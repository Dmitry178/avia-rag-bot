"""Document ingestion and indexing."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings, settings
from app.core.db_manager import DBManager
from app.core.logs import logger
from app.exceptions import handle_basic_db_errors
from app.exceptions.service import ServiceError
from app.infrastructure.faiss.store import save_index_async
from app.infrastructure.llm.embeddings import EmbeddingClient
from app.models.chunk_meta import ChunkMeta
from app.models.index_manifest import IndexManifest
from app.schemas.etl import ChunkStatsResponse, IngestResponse, ManifestResponse
from etl.chunker import chunk_document


class ETLService:
    """
    Orchestrates the ingest use case: parse → embed → SQLite + FAISS + manifest.

    Pure parse/chunk logic lives in the `etl/` package; this service wires I/O and persistence.
    """

    def __init__(self, db: DBManager, app_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = app_settings or settings

    def _resolve_source_path(self, source_path: str | None) -> Path:
        """
        API/CLI override or default from ETL__DOCUMENT_PATH (relative to repo root).
        """
        
        if source_path:
            path = Path(source_path)
            if not path.is_absolute():
                path = self.settings.repo_root / path
            return path

        return self.settings.etl.resolve_document_path(self.settings.repo_root)

    def _faiss_index_path(self) -> Path:
        return Path(self.settings.data.dir) / "faiss.index"

    def _manifest_json_path(self) -> Path:
        # Duplicate of index_manifest row for tooling / Docker bootstrap without DB access.
        return Path(self.settings.data.dir) / "manifest.json"

    @handle_basic_db_errors
    async def ingest(self, *, rebuild: bool = True, source_path: str | None = None) -> IngestResponse:
        """
        Parse document, embed chunks, and persist index artifacts.

        Pipeline: read markdown → chunk → embed → SQLite → commit → FAISS → manifest.json.
        """

        if not rebuild:
            raise ServiceError(
                detail="Only full rebuild ingest is supported",
                error_code="etl_rebuild_required",
                status_code=400,
            )

        # --- Phase 1: read and chunk (no DB) ---
        path = self._resolve_source_path(source_path)
        if not path.is_file():
            raise ServiceError(
                detail=f"Source document not found: {path}",
                error_code="etl_source_not_found",
                status_code=404,
            )

        raw_text = path.read_text(encoding="utf-8")
        doc_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        source = str(path)
        drafts = chunk_document(raw_text, source_path=source)

        if not drafts:
            raise ServiceError(
                detail="No chunks produced from source document",
                error_code="etl_empty_document",
                status_code=400,
            )

        # --- Phase 2: embeddings (external LLM API) ---
        embedder = EmbeddingClient(self.settings.llm)
        vectors = await embedder.embed_texts([draft.content for draft in drafts])

        if len(vectors) != len(drafts):
            raise ServiceError(
                detail="Embedding count does not match chunk count",
                error_code="etl_embedding_mismatch",
                status_code=502,
            )

        # --- Phase 3: SQLite (chunk_meta + index_manifest) ---
        built_at = datetime.now(UTC)
        chunk_models: list[ChunkMeta] = []

        for index, draft in enumerate(drafts):
            parent_id = draft.parent_chunk_index if draft.parent_chunk_index is not None else None
            chunk_models.append(
                ChunkMeta(
                    # Explicit id = FAISS row index; order must match vectors list.
                    id=index,
                    content=draft.content,
                    content_type=draft.content_type.value,
                    section=draft.section,
                    title=draft.title,
                    node_id=draft.node_id,
                    parent_id=parent_id,
                    token_count=draft.token_count,
                    source_path=draft.source_path or source,
                    created_at=built_at,
                )
            )

        if rebuild:
            await self.db.etl.chunks.delete_all()
            await self.db.etl.index_manifest.delete_all()

        await self.db.etl.chunks.insert_many(chunk_models)

        manifest = IndexManifest(
            source_path=source,
            doc_hash=doc_hash,
            embedding_model=self.settings.llm.embedding_model,
            chunk_count=len(chunk_models),
            built_at=built_at,
        )
        saved_manifest = await self.db.etl.index_manifest.insert(manifest)
        await self.db.commit()

        # --- Phase 4: FAISS + manifest.json (after DB commit) ---
        # Index is rebuilt on disk only after SQLite succeeds so retrieval metadata stays consistent.
        data_dir = Path(self.settings.data.dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        await save_index_async(vectors, self._faiss_index_path())

        manifest_payload = {
            "source_path": source,
            "doc_hash": doc_hash,
            "embedding_model": self.settings.llm.embedding_model,
            "chunk_count": len(chunk_models),
            "built_at": built_at.isoformat(),
        }
        self._manifest_json_path().write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(
            "etl_ingest_completed",
            chunk_count=len(chunk_models),
            source_path=source,
            doc_hash=doc_hash,
        )

        return IngestResponse(
            chunk_count=len(chunk_models),
            doc_hash=doc_hash,
            embedding_model=self.settings.llm.embedding_model,
            source_path=source,
            built_at=saved_manifest.built_at,
        )

    @handle_basic_db_errors
    async def stats(self) -> ChunkStatsResponse:
        """
        Return chunk counts grouped by content type.
        """

        by_type = await self.db.etl.chunks.count_by_content_type()
        total = await self.db.etl.chunks.total_count()

        return ChunkStatsResponse(total=total, by_content_type=by_type)

    @handle_basic_db_errors
    async def manifest(self) -> ManifestResponse:
        """
        Return metadata for the latest index build.
        """

        latest = await self.db.etl.index_manifest.get_latest()
        
        # Business rule: no manifest row means ingest has never completed successfully.
        if latest is None:
            raise ServiceError(
                detail="Index has not been built yet",
                error_code="etl_not_indexed",
                status_code=404,
            )

        return ManifestResponse(
            source_path=latest.source_path,
            doc_hash=latest.doc_hash,
            embedding_model=latest.embedding_model,
            chunk_count=latest.chunk_count,
            built_at=latest.built_at,
        )
