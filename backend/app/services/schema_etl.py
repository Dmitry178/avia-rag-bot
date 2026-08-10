"""Schema-driven ETL ingestion without touching application DB state."""

import hashlib
import json

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.core.faiss_manager import faiss_manager
from app.core.logs import logger
from app.exceptions.service import ServiceError
from app.llm.embeddings import EmbeddingClient
from etl.chunking_schema import load_runtime_schema, resolve_schema_output_root, resolve_schema_source_path
from etl.document_warnings import emit_duplicate_section_number_warnings
from etl.universal_chunker import UniversalChunker


@dataclass(frozen=True, slots=True)
class SchemaIngestResult:
    """
    Result payload for one schema-driven ingestion run.
    """

    schema_path: str
    language_code: str
    source_path: str
    output_root: str
    chunk_count: int
    doc_hash: str
    chunker_version: str
    manifest_path: str
    chunks_export_path: str
    faiss_index_path: str | None
    embedded: int


class SchemaETLService:
    """
    Run chunking from schema and store artifacts in isolated output root.
    """

    @staticmethod
    async def ingest(
        *,
        schema_path: str,
        source_path: str | None = None,
        output_root: str | None = None,
        run_id: str | None = None,
        no_embed: bool = False,
        allow_overwrite: bool = False,
    ) -> SchemaIngestResult:
        """
        Run schema-driven ETL and write chunks/manifest/optional FAISS.
        """

        backend_root = settings.backend_root
        repo_root = settings.repo_root
        context = load_runtime_schema(Path(schema_path), backend_root, repo_root)
        schema = context.schema
        chunker = UniversalChunker(schema)
        resolved_source = resolve_schema_source_path(
            schema,
            schema_dir=context.schema_dir,
            backend_root=backend_root,
            repo_root=repo_root,
            source_override=source_path,
        )
        resolved_output_root = resolve_schema_output_root(
            schema,
            schema_dir=context.schema_dir,
            backend_root=backend_root,
            repo_root=repo_root,
            output_root_override=output_root,
        )

        if run_id:
            normalized = run_id.strip()
            if not normalized:
                raise ServiceError(
                    detail="run_id cannot be empty",
                    error_code="etl_schema_invalid_run_id",
                    status_code=400,
                )

            resolved_output_root = (resolved_output_root / normalized).resolve()

        if not resolved_source.is_file():
            raise ServiceError(
                detail=f"Source document not found: {resolved_source}",
                error_code="etl_source_not_found",
                status_code=404,
            )

        resolved_output_root.mkdir(parents=True, exist_ok=True)
        chunks_path = (resolved_output_root / schema.io.chunks_export_path).resolve()
        manifest_path = (resolved_output_root / schema.io.manifest_path).resolve()
        faiss_path = (resolved_output_root / schema.io.faiss_index_path).resolve()

        protected_targets = schema.io.protected_production_targets
        if protected_targets is not None and protected_targets.require_explicit_override and not allow_overwrite:
            forbidden: list[Path] = []
            target_values = [
                protected_targets.chunk_meta_db_path,
                protected_targets.faiss_index_path,
                protected_targets.manifest_path,
            ]

            for target_value in target_values:
                if not target_value:
                    continue
                target_path = Path(target_value)
                if not target_path.is_absolute():
                    target_path = (repo_root / target_path).resolve()
                if target_path in {chunks_path, manifest_path, faiss_path}:
                    forbidden.append(target_path)

            if forbidden:
                rendered = ", ".join(str(path) for path in forbidden)
                raise ServiceError(
                    detail=(
                        "Target path matches a protected production artifact and requires explicit override. "
                        f"Conflicts: {rendered}"
                    ),
                    error_code="etl_schema_production_path_forbidden",
                    status_code=409,
                )

        if schema.io.overwrite_policy == "forbid" and not allow_overwrite:
            existing_paths = [path for path in (chunks_path, manifest_path, faiss_path) if path.exists()]
            if existing_paths:
                rendered = ", ".join(str(path) for path in existing_paths)
                raise ServiceError(
                    detail=(
                        "Output artifacts already exist and overwrite is forbidden by schema. "
                        f"Existing: {rendered}"
                    ),
                    error_code="etl_schema_overwrite_forbidden",
                    status_code=409,
                )

        raw_text = resolved_source.read_text(encoding="utf-8")
        doc_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        emit_duplicate_section_number_warnings(
            chunker,
            raw_text,
            source_path=str(resolved_source),
            logger=logger,
        )
        drafts = chunker.chunk_document(raw_text, source_path=str(resolved_source))

        if not drafts:
            raise ServiceError(
                detail="No chunks produced from source document",
                error_code="etl_empty_document",
                status_code=400,
            )

        chunks_path.parent.mkdir(parents=True, exist_ok=True)
        with chunks_path.open("w", encoding="utf-8") as file:
            for index, draft in enumerate(drafts):
                payload = {
                    "id": index,
                    "language_code": schema.document.language_code,
                    "content": draft.content,
                    "content_type": str(getattr(draft.content_type, "value", draft.content_type)),
                    "section": draft.section,
                    "title": draft.title,
                    "node_id": draft.node_id,
                    "content_hash": draft.content_hash,
                    "parent_id": draft.parent_chunk_index,
                    "token_count": draft.token_count,
                    "source_path": draft.source_path,
                }
                file.write(json.dumps(payload, ensure_ascii=False) + "\n")

        embedded = 0
        resolved_faiss: Path | None = None

        if not no_embed:
            if not settings.llm.embedding_model:
                raise ServiceError(
                    detail="Embedding model is not configured; cannot build FAISS index",
                    error_code="etl_embedding_model_missing",
                    status_code=400,
                )

            embedder = EmbeddingClient(settings.llm)
            vectors: list[list[float]] = []
            texts = [draft.content for draft in drafts]

            async for batch in embedder.iter_embed_batches(texts):
                vectors.extend(batch)

            embedded = len(vectors)

            if embedded != len(drafts):
                raise ServiceError(
                    detail="Embedding count does not match chunk count",
                    error_code="etl_embedding_mismatch",
                    status_code=502,
                )

            faiss_path.parent.mkdir(parents=True, exist_ok=True)
            await faiss_manager.save_async(vectors, faiss_path)
            resolved_faiss = faiss_path

        built_at = datetime.now(UTC)
        manifest_payload = {
            "schema_path": str(Path(schema_path).resolve()),
            "language_code": schema.document.language_code,
            "source_path": str(resolved_source),
            "output_root": str(resolved_output_root),
            "doc_hash": doc_hash,
            "chunk_count": len(drafts),
            "chunker_version": schema.format,
            "embedding_model": settings.llm.embedding_model if not no_embed else "",
            "embedded": embedded,
            "built_at": built_at.isoformat(),
        }

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info(
            "schema_ingest_completed",
            schema_path=str(Path(schema_path).resolve()),
            language_code=schema.document.language_code,
            source_path=str(resolved_source),
            output_root=str(resolved_output_root),
            chunk_count=len(drafts),
            embedded=embedded,
        )

        return SchemaIngestResult(
            schema_path=str(Path(schema_path).resolve()),
            language_code=schema.document.language_code,
            source_path=str(resolved_source),
            output_root=str(resolved_output_root),
            chunk_count=len(drafts),
            doc_hash=doc_hash,
            chunker_version=schema.format,
            manifest_path=str(manifest_path),
            chunks_export_path=str(chunks_path),
            faiss_index_path=str(resolved_faiss) if resolved_faiss is not None else None,
            embedded=embedded,
        )
