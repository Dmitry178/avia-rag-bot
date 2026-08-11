"""Document ingestion and indexing."""

import asyncio
import hashlib
import json

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import DBSettings, Settings, get_kb_language, settings
from app.core.db_manager import DBManager
from app.core.faiss_manager import faiss_manager
from app.core.logs import logger
from app.db.init_db import init_db
from app.db.session import SessionLocal, dispose_engine
from app.exceptions import handle_basic_db_errors
from app.exceptions.ingest import IngestInterruptedError
from app.exceptions.service import ServiceError
from app.llm.embeddings import EmbeddingClient
from app.models.chunk_meta import ChunkMeta
from app.models.index_manifest import IndexManifest
from app.schemas.etl import ChunkStatsResponse, IngestAllResponse, IngestResponse, ManifestResponse
from app.services.etl_checkpoint import IngestCheckpoint, IngestCheckpointStore
from app.services.etl_plan import plan_ingest
from app.services.etl_progress import IngestProgress, IngestProgressCallback
from etl.chunking_schema import (
    discover_chunking_schemas,
    load_runtime_schema,
    resolve_schema_chunk_meta_db_path,
    resolve_schema_output_root,
    resolve_schema_source_path,
)
from etl.document_warnings import emit_duplicate_section_number_warnings
from etl.universal_chunker import UniversalChunker
from etl.types import ChunkDraft


async def _with_schema_db[T](
    db_file: Path,
    handler: Callable[[DBManager], Awaitable[T]],
    app_settings: Settings,
) -> T:
    """
    Point the app database at a schema-declared SQLite file and run handler.
    """

    db_file.parent.mkdir(parents=True, exist_ok=True)
    await dispose_engine()
    app_settings.db = DBSettings(url=f"sqlite:///{db_file.resolve().as_posix()}")
    app_settings.data.ensure_exists(app_settings.backend_root)
    await init_db()

    try:
        async with DBManager(SessionLocal) as db:
            return await handler(db)
    finally:
        await dispose_engine()


async def ingest_chunking_schema_at_path(
    schema_path: Path,
    *,
    rebuild: bool = False,
    source_path: str | None = None,
    on_progress: IngestProgressCallback | None = None,
    db: DBManager | None = None,
    app_settings: Settings | None = None,
) -> IngestResponse:
    """
    Ingest one schema file, using the SQLite path declared in the schema when present.
    """

    resolved_settings = app_settings or settings
    context = load_runtime_schema(
        schema_path,
        resolved_settings.backend_root,
        resolved_settings.repo_root,
    )
    db_path = resolve_schema_chunk_meta_db_path(context.schema, schema_dir=context.schema_dir)

    async def _run(active_db: DBManager) -> IngestResponse:
        return await ETLService(active_db, resolved_settings).ingest_schema(
            schema_path=schema_path,
            rebuild=rebuild,
            source_path=source_path,
            on_progress=on_progress,
        )

    if db_path is not None:
        return await _with_schema_db(db_path, _run, resolved_settings)

    if db is None:
        raise ServiceError(
            detail="Database session is required when schema does not declare chunk_meta.db_path",
            error_code="etl_db_required",
            status_code=500,
        )

    return await _run(db)


class ETLService:
    """
    Orchestrates the ingest use case: parse → embed → SQLite + FAISS + manifest.

    Pure parse/chunk logic lives in the `etl/` package; this service wires I/O and persistence.
    Supports resume from checkpoint and incremental sync when the document changes.
    Each knowledge-base language has its own chunk set, FAISS index, and manifest.
    """

    def __init__(self, db: DBManager, app_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = app_settings or settings

    @staticmethod
    def _content_type_value(value: object) -> str:
        resolved = getattr(value, "value", value)
        return str(resolved)

    @staticmethod
    def _checkpoint_store(output_root: Path, language_code: str) -> IngestCheckpointStore:
        return IngestCheckpointStore(
            output_root / f"ingest_checkpoint_{language_code}.json",
        )

    @staticmethod
    def _report_progress(
        callback: IngestProgressCallback | None,
        *,
        phase: str,
        current: int,
        total: int,
        overall_percent: int,
        section: str | None = None,
        item_title: str | None = None,
        section_current: int | None = None,
        section_total: int | None = None,
    ) -> None:
        if callback is None:
            return

        callback(
            IngestProgress(
                phase=phase,
                current=current,
                total=total,
                overall_percent=overall_percent,
                section=section,
                item_title=item_title,
                section_current=section_current,
                section_total=section_total,
            )
        )

    @staticmethod
    def _chunk_progress_context(
        drafts: list[ChunkDraft],
        ordered_indices: list[int],
        completed_count: int,
    ) -> tuple[str | None, str | None, int | None, int | None]:
        """
        Return section, item title, and per-section progress for the last completed chunk.
        """

        if completed_count <= 0 or not ordered_indices:
            return None, None, None, None

        draft_index = ordered_indices[completed_count - 1]
        draft = drafts[draft_index]
        section = draft.section
        section_total = sum(1 for index in ordered_indices if drafts[index].section == section)
        section_current = sum(
            1 for index in ordered_indices[:completed_count] if drafts[index].section == section
        )

        return section, draft.title, section_current, section_total

    def _can_reuse_existing_vectors(
        self,
        latest_manifest: IndexManifest | None,
        *,
        source: str,
        rebuild: bool,
        chunker_version: str,
    ) -> bool:
        if rebuild or latest_manifest is None:
            return False

        return (
            latest_manifest.embedding_model == self.settings.llm.embedding_model
            and latest_manifest.chunker_version == chunker_version
            and latest_manifest.source_path == source
        )

    async def _embed_missing(
        self,
        drafts: list[ChunkDraft],
        embed_indices: list[int],
        reused_vectors: dict[int, list[float]],
        checkpoint_store: IngestCheckpointStore,
        checkpoint: IngestCheckpoint,
        on_progress: IngestProgressCallback | None,
    ) -> list[list[float]]:
        """
        Embed drafts that still lack vectors; persist checkpoint in batches.
        """

        total_chunks = len(drafts)
        vectors_by_index: list[list[float] | None] = [None] * total_chunks

        for index, vector in reused_vectors.items():
            vectors_by_index[index] = vector

        pending_indices = [index for index in embed_indices if vectors_by_index[index] is None]
        if not pending_indices:
            return [vectors_by_index[i] for i in range(total_chunks)]  # type: ignore[misc]

        texts = [drafts[index].content for index in pending_indices]
        embedder = EmbeddingClient(self.settings.llm)
        embedded_count = total_chunks - len(pending_indices)
        completed_in_run = 0

        try:
            async for batch_vectors in embedder.iter_embed_batches(texts):
                for vector in batch_vectors:
                    draft_index = pending_indices[completed_in_run]
                    vectors_by_index[draft_index] = vector
                    checkpoint.vectors_by_hash[drafts[draft_index].content_hash] = vector
                    completed_in_run += 1

                    section, item_title, section_current, section_total = self._chunk_progress_context(
                        drafts,
                        pending_indices,
                        completed_in_run,
                    )
                    current_embedded = embedded_count + completed_in_run
                    self._report_progress(
                        on_progress,
                        phase="embedding",
                        current=current_embedded,
                        total=total_chunks,
                        overall_percent=5 + int(85 * current_embedded / max(total_chunks, 1)),
                        section=section,
                        item_title=item_title,
                        section_current=section_current,
                        section_total=section_total,
                    )

                checkpoint_store.save(checkpoint)
        except asyncio.CancelledError as exc:
            checkpoint_store.save(checkpoint)
            raise IngestInterruptedError(
                embedded=embedded_count + completed_in_run,
                total=total_chunks,
            ) from None

        if completed_in_run != len(pending_indices):
            raise ServiceError(
                detail="Embedding count does not match chunk count",
                error_code="etl_embedding_mismatch",
                status_code=502,
            )

        checkpoint_total = len(pending_indices)

        for item_index in range(1, checkpoint_total + 1):
            section, item_title, section_current, section_total = self._chunk_progress_context(
                drafts,
                pending_indices,
                item_index,
            )
            self._report_progress(
                on_progress,
                phase="checkpoint",
                current=item_index,
                total=checkpoint_total,
                overall_percent=90 + int(2 * item_index / max(checkpoint_total, 1)),
                section=section,
                item_title=item_title,
                section_current=section_current,
                section_total=section_total,
            )

        return [vectors_by_index[i] for i in range(total_chunks)]  # type: ignore[misc]

    @handle_basic_db_errors
    async def ingest_schema(
        self,
        *,
        schema_path: Path,
        rebuild: bool = False,
        source_path: str | None = None,
        on_progress: IngestProgressCallback | None = None,
    ) -> IngestResponse:
        """
        Parse document, embed chunks, and persist index artifacts for one schema file.

        Paths in the schema are resolved relative to the schema file directory.
        """

        runtime_schema = load_runtime_schema(
            schema_path,
            self.settings.backend_root,
            self.settings.repo_root,
        )
        schema = runtime_schema.schema
        language_code = schema.document.language_code
        chunker = UniversalChunker(schema)
        output_root = resolve_schema_output_root(
            schema,
            schema_dir=runtime_schema.schema_dir,
            backend_root=self.settings.backend_root,
            repo_root=self.settings.repo_root,
            output_root_override=None,
        )
        output_root.mkdir(parents=True, exist_ok=True)
        checkpoint_store = self._checkpoint_store(output_root, language_code)

        if rebuild:
            checkpoint_store.clear()

        path = resolve_schema_source_path(
            schema,
            schema_dir=runtime_schema.schema_dir,
            backend_root=self.settings.backend_root,
            repo_root=self.settings.repo_root,
            source_override=source_path,
        )

        if not path.is_file():
            raise ServiceError(
                detail=f"Source document not found: {path}",
                error_code="etl_source_not_found",
                status_code=404,
            )

        raw_text = path.read_text(encoding="utf-8")
        doc_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        source = str(path)
        emit_duplicate_section_number_warnings(
            chunker,
            raw_text,
            source_path=source,
            logger=logger,
        )
        drafts = chunker.chunk_document(raw_text, source_path=source)

        if not drafts:
            raise ServiceError(
                detail="No chunks produced from source document",
                error_code="etl_empty_document",
                status_code=400,
            )

        total_chunks = len(drafts)
        self._report_progress(
            on_progress,
            phase="chunking",
            current=total_chunks,
            total=total_chunks,
            overall_percent=5,
        )

        embedding_model = self.settings.llm.embedding_model
        chunker_version = schema.format
        latest_manifest = await self.db.etl.index_manifest.get_latest(language_code)
        can_reuse_existing = self._can_reuse_existing_vectors(
            latest_manifest,
            source=source,
            rebuild=rebuild,
            chunker_version=chunker_version,
        )
        existing_chunks = await self.db.etl.chunks.list_all_ordered(language_code)
        existing_vectors: list[list[float]] = []
        faiss_path = (output_root / schema.io.faiss_index_path).resolve()

        if can_reuse_existing and faiss_path.is_file():
            existing_vectors = await faiss_manager.reconstruct_vectors_async(faiss_path)

        loaded_checkpoint = checkpoint_store.load()
        checkpoint_vectors: dict[str, list[float]] = {}

        if loaded_checkpoint is not None and checkpoint_store.is_compatible(
            loaded_checkpoint,
            language_code=language_code,
            source_path=source,
            doc_hash=doc_hash,
            embedding_model=embedding_model,
            chunker_version=chunker_version,
            rebuild=rebuild,
        ):
            checkpoint_vectors = dict(loaded_checkpoint.vectors_by_hash)
        elif loaded_checkpoint is not None:
            checkpoint_store.clear()

        plan = plan_ingest(
            drafts,
            existing_chunks,
            existing_vectors,
            checkpoint_vectors,
            rebuild=rebuild,
            can_reuse_existing=can_reuse_existing,
        )

        checkpoint = IngestCheckpoint(
            language_code=language_code,
            source_path=source,
            doc_hash=doc_hash,
            embedding_model=embedding_model,
            chunker_version=chunker_version,
            rebuild=rebuild,
            total_chunks=total_chunks,
            vectors_by_hash=dict(checkpoint_vectors),
        )

        for index, vector in plan.reused_vectors.items():
            checkpoint.vectors_by_hash[drafts[index].content_hash] = vector

        checkpoint_store.save(checkpoint)

        vectors = await self._embed_missing(
            drafts,
            plan.embed_indices,
            plan.reused_vectors,
            checkpoint_store,
            checkpoint,
            on_progress,
        )

        self._report_progress(
            on_progress,
            phase="persisting",
            current=0,
            total=total_chunks,
            overall_percent=92,
            section="SQLite",
            item_title="chunk metadata",
        )

        built_at = datetime.now(UTC)
        chunk_models: list[ChunkMeta] = []

        for index, draft in enumerate(drafts):
            parent_id = draft.parent_chunk_index if draft.parent_chunk_index is not None else None
            chunk_models.append(
                ChunkMeta(
                    language_code=language_code,
                    id=index,
                    content=draft.content,
                    content_type=self._content_type_value(draft.content_type),
                    section=draft.section,
                    title=draft.title,
                    node_id=draft.node_id,
                    content_hash=draft.content_hash,
                    parent_id=parent_id,
                    token_count=draft.token_count,
                    source_path=draft.source_path or source,
                    created_at=built_at,
                )
            )

        await self.db.etl.chunks.replace_for_language(language_code, chunk_models)
        await self.db.etl.index_manifest.delete_for_language(language_code)

        manifest = IndexManifest(
            language_code=language_code,
            source_path=source,
            doc_hash=doc_hash,
            embedding_model=embedding_model,
            chunker_version=chunker_version,
            chunk_count=len(chunk_models),
            built_at=built_at,
        )
        saved_manifest = await self.db.etl.index_manifest.insert(manifest)
        await self.db.commit()

        self._report_progress(
            on_progress,
            phase="faiss",
            current=0,
            total=total_chunks,
            overall_percent=95,
            section="FAISS",
            item_title="vector index",
        )

        output_root.mkdir(parents=True, exist_ok=True)
        await faiss_manager.save_async(vectors, faiss_path)

        manifest_payload = {
            "language_code": language_code,
            "source_path": source,
            "doc_hash": doc_hash,
            "embedding_model": embedding_model,
            "chunker_version": chunker_version,
            "chunk_count": len(chunk_models),
            "built_at": built_at.isoformat(),
        }
        manifest_path = (output_root / schema.io.manifest_path).resolve()
        manifest_path.write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        checkpoint_store.clear()

        self._report_progress(
            on_progress,
            phase="done",
            current=total_chunks,
            total=total_chunks,
            overall_percent=100,
        )

        embedded_count = len(plan.embed_indices)

        logger.info(
            "etl_ingest_completed",
            language_code=language_code,
            schema_path=str(runtime_schema.schema_path),
            chunk_count=len(chunk_models),
            source_path=source,
            doc_hash=doc_hash,
            added=plan.stats.added,
            updated=plan.stats.updated,
            unchanged=plan.stats.unchanged,
            removed=plan.stats.removed,
            embedded=embedded_count,
        )

        return IngestResponse(
            language_code=language_code,
            chunk_count=len(chunk_models),
            doc_hash=doc_hash,
            embedding_model=embedding_model,
            source_path=source,
            built_at=saved_manifest.built_at,
            added=plan.stats.added,
            updated=plan.stats.updated,
            unchanged=plan.stats.unchanged,
            removed=plan.stats.removed,
            embedded=embedded_count,
        )

    @handle_basic_db_errors
    async def ingest_directory(
        self,
        *,
        schemas_dir: Path,
        rebuild: bool = False,
        on_progress: IngestProgressCallback | None = None,
    ) -> IngestAllResponse:
        """
        Discover and ingest every supported chunking schema JSON in a directory.
        """

        schema_paths = discover_chunking_schemas(schemas_dir)
        results: list[IngestResponse] = []

        for schema_path in schema_paths:
            results.append(
                await self.ingest_schema(
                    schema_path=schema_path,
                    rebuild=rebuild,
                    on_progress=on_progress,
                ),
            )

        return IngestAllResponse(results=results)

    @handle_basic_db_errors
    async def ingest_all(
        self,
        *,
        rebuild: bool = False,
        on_progress: IngestProgressCallback | None = None,
    ) -> IngestAllResponse:
        """
        Ingest every supported schema JSON in the default backend data directory.
        """

        return await self.ingest_directory(
            schemas_dir=self.settings.backend_root / "data",
            rebuild=rebuild,
            on_progress=on_progress,
        )

    @handle_basic_db_errors
    async def stats(self, language_code: str | None = None) -> ChunkStatsResponse:
        """
        Return chunk counts grouped by content type, optionally for one language.
        """

        if language_code is not None:
            get_kb_language(language_code)

        by_type = await self.db.etl.chunks.count_by_content_type(language_code)
        total = await self.db.etl.chunks.total_count(language_code)

        return ChunkStatsResponse(language_code=language_code, total=total, by_content_type=by_type)

    @handle_basic_db_errors
    async def manifest(self, language_code: str) -> ManifestResponse:
        """
        Return metadata for the latest index build of a language.
        """

        get_kb_language(language_code)
        latest = await self.db.etl.index_manifest.get_latest(language_code)

        if latest is None:
            raise ServiceError(
                detail=f"Index has not been built yet for language: {language_code}",
                error_code="etl_not_indexed",
                status_code=404,
            )

        return ManifestResponse(
            language_code=latest.language_code,
            source_path=latest.source_path,
            doc_hash=latest.doc_hash,
            embedding_model=latest.embedding_model,
            chunker_version=latest.chunker_version,
            chunk_count=latest.chunk_count,
            built_at=latest.built_at,
        )
