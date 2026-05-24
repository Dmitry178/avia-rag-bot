"""Document ingestion and indexing."""

import hashlib
import json

from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings, settings
from app.core.db_manager import DBManager
from app.core.faiss_manager import faiss_manager
from app.core.logs import logger
from app.exceptions import handle_basic_db_errors
from app.exceptions.service import ServiceError
from app.llm.embeddings import EMBED_BATCH_SIZE, EmbeddingClient
from app.models.chunk_meta import ChunkMeta
from app.models.index_manifest import IndexManifest
from app.schemas.etl import ChunkStatsResponse, IngestResponse, ManifestResponse
from app.services.etl_checkpoint import IngestCheckpoint, IngestCheckpointStore
from app.services.etl_plan import plan_ingest
from app.services.etl_progress import IngestProgress, IngestProgressCallback
from etl.chunker import chunk_document
from etl.hashing import CHUNKER_VERSION
from etl.types import ChunkDraft


class ETLService:
    """
    Orchestrates the ingest use case: parse → embed → SQLite + FAISS + manifest.

    Pure parse/chunk logic lives in the `etl/` package; this service wires I/O and persistence.
    Supports resume from checkpoint and incremental sync when the document changes.
    """

    def __init__(self, db: DBManager, app_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = app_settings or settings

    def _resolve_source_path(self, source_path: str | None) -> Path:
        """
        API/CLI override or default from ETL__DOCUMENT_PATH (relative to backend root).
        """

        if source_path:
            path = Path(source_path)
            if not path.is_absolute():
                path = self.settings.backend_root / path
            return path

        return self.settings.etl.resolve_document_path(self.settings.backend_root)

    def _faiss_index_path(self) -> Path:
        return self.settings.faiss.index_path(self.settings.backend_root)

    def _manifest_json_path(self) -> Path:
        # Duplicate of index_manifest row for tooling / Docker bootstrap without DB access.
        return self.settings.resolve_data_dir() / "manifest.json"

    def _checkpoint_store(self) -> IngestCheckpointStore:
        return IngestCheckpointStore(self.settings.resolve_data_dir() / "ingest_checkpoint.json")

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
    ) -> bool:
        if rebuild or latest_manifest is None:
            return False

        return (
            latest_manifest.embedding_model == self.settings.llm.embedding_model
            and latest_manifest.chunker_version == CHUNKER_VERSION
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

        def on_batch_complete(done: int, batch_total: int) -> None:
            current_embedded = embedded_count + done
            overall = 5 + int(85 * current_embedded / max(total_chunks, 1))
            section, item_title, section_current, section_total = self._chunk_progress_context(
                drafts,
                pending_indices,
                done,
            )
            self._report_progress(
                on_progress,
                phase="embedding",
                current=current_embedded,
                total=total_chunks,
                overall_percent=overall,
                section=section,
                item_title=item_title,
                section_current=section_current,
                section_total=section_total,
            )

        new_vectors = await embedder.embed_texts(texts, on_batch_complete=on_batch_complete)

        if len(new_vectors) != len(pending_indices):
            raise ServiceError(
                detail="Embedding count does not match chunk count",
                error_code="etl_embedding_mismatch",
                status_code=502,
            )

        checkpoint_total = len(pending_indices)

        for item_index, (draft_index, vector) in enumerate(
            zip(pending_indices, new_vectors, strict=True),
            start=1,
        ):
            vectors_by_index[draft_index] = vector
            checkpoint.vectors_by_hash[drafts[draft_index].content_hash] = vector

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

            if item_index % EMBED_BATCH_SIZE == 0 or item_index == checkpoint_total:
                checkpoint_store.save(checkpoint)

        return [vectors_by_index[i] for i in range(total_chunks)]  # type: ignore[misc]

    @handle_basic_db_errors
    async def ingest(
        self,
        *,
        rebuild: bool = False,
        source_path: str | None = None,
        on_progress: IngestProgressCallback | None = None,
    ) -> IngestResponse:
        """
        Parse document, embed chunks, and persist index artifacts.

        Incremental by default: reuses unchanged chunk vectors, embeds new/changed only.
        Writes a checkpoint during embedding so a failed run can resume.
        """

        checkpoint_store = self._checkpoint_store()

        if rebuild:
            checkpoint_store.clear()

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

        total_chunks = len(drafts)
        self._report_progress(
            on_progress,
            phase="chunking",
            current=total_chunks,
            total=total_chunks,
            overall_percent=5,
        )

        embedding_model = self.settings.llm.embedding_model
        latest_manifest = await self.db.etl.index_manifest.get_latest()
        can_reuse_existing = self._can_reuse_existing_vectors(latest_manifest, source=source, rebuild=rebuild)

        existing_chunks = await self.db.etl.chunks.list_all_ordered()
        existing_vectors: list[list[float]] = []

        if can_reuse_existing and self._faiss_index_path().is_file():
            existing_vectors = await faiss_manager.reconstruct_vectors_async(self._faiss_index_path())

        loaded_checkpoint = checkpoint_store.load()
        checkpoint_vectors: dict[str, list[float]] = {}

        if loaded_checkpoint is not None and checkpoint_store.is_compatible(
            loaded_checkpoint,
            source_path=source,
            doc_hash=doc_hash,
            embedding_model=embedding_model,
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
            source_path=source,
            doc_hash=doc_hash,
            embedding_model=embedding_model,
            rebuild=rebuild,
            total_chunks=total_chunks,
            vectors_by_hash=dict(checkpoint_vectors),
        )

        for index, vector in plan.reused_vectors.items():
            checkpoint.vectors_by_hash[drafts[index].content_hash] = vector

        checkpoint_store.save(checkpoint)

        # --- Phase 2: embeddings (external LLM API, with checkpoint) ---
        vectors = await self._embed_missing(
            drafts,
            plan.embed_indices,
            plan.reused_vectors,
            checkpoint_store,
            checkpoint,
            on_progress,
        )

        # --- Phase 3: SQLite (chunk_meta + index_manifest) ---
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
                    id=index,
                    content=draft.content,
                    content_type=draft.content_type.value,
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

        await self.db.etl.chunks.replace_all(chunk_models)
        await self.db.etl.index_manifest.delete_all()

        manifest = IndexManifest(
            source_path=source,
            doc_hash=doc_hash,
            embedding_model=embedding_model,
            chunker_version=CHUNKER_VERSION,
            chunk_count=len(chunk_models),
            built_at=built_at,
        )
        saved_manifest = await self.db.etl.index_manifest.insert(manifest)
        await self.db.commit()

        # --- Phase 4: FAISS + manifest.json (after DB commit) ---
        self._report_progress(
            on_progress,
            phase="faiss",
            current=0,
            total=total_chunks,
            overall_percent=95,
            section="FAISS",
            item_title="vector index",
        )

        data_dir = self.settings.resolve_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.faiss.ensure_exists(self.settings.backend_root)
        await faiss_manager.save_async(vectors, self._faiss_index_path())

        manifest_payload = {
            "source_path": source,
            "doc_hash": doc_hash,
            "embedding_model": embedding_model,
            "chunker_version": CHUNKER_VERSION,
            "chunk_count": len(chunk_models),
            "built_at": built_at.isoformat(),
        }
        self._manifest_json_path().write_text(
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
            chunker_version=latest.chunker_version,
            chunk_count=latest.chunk_count,
            built_at=latest.built_at,
        )
