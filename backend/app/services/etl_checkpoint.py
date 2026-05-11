"""Persisted ingest checkpoint for resume after interruption."""

import json

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from etl.hashing import CHUNKER_VERSION


class CheckpointDraft(BaseModel):
    """
    Serializable chunk draft stored in the ingest checkpoint.
    """

    node_id: str
    content_hash: str
    content: str
    content_type: str
    section: str
    title: str
    parent_chunk_index: int | None = None
    token_count: int = 0
    source_path: str = ""


class IngestCheckpoint(BaseModel):
    """
    On-disk state for resuming an interrupted ingest run.
    """

    source_path: str
    doc_hash: str
    embedding_model: str
    chunker_version: str = CHUNKER_VERSION
    rebuild: bool = False
    total_chunks: int
    vectors_by_hash: dict[str, list[float]] = Field(default_factory=dict)


class IngestCheckpointStore:
    """
    Read/write ingest checkpoint JSON next to other data artifacts.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> IngestCheckpoint | None:
        """
        Load checkpoint if present and valid JSON.
        """

        if not self._path.is_file():
            return None

        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return IngestCheckpoint.model_validate(payload)

    def save(self, checkpoint: IngestCheckpoint) -> None:
        """
        Atomically persist checkpoint to disk.
        """

        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(checkpoint.model_dump(), ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.replace(self._path)

    def clear(self) -> None:
        """
        Remove checkpoint file if it exists.
        """

        if self._path.is_file():
            self._path.unlink()

    @staticmethod
    def is_compatible(
        checkpoint: IngestCheckpoint,
        *,
        source_path: str,
        doc_hash: str,
        embedding_model: str,
        rebuild: bool,
    ) -> bool:
        """
        Return True when checkpoint matches the current ingest context.
        """

        return (
            checkpoint.source_path == source_path
            and checkpoint.doc_hash == doc_hash
            and checkpoint.embedding_model == embedding_model
            and checkpoint.chunker_version == CHUNKER_VERSION
            and checkpoint.rebuild == rebuild
        )

    @staticmethod
    def draft_to_payload(draft: Any) -> CheckpointDraft:
        """
        Convert a ChunkDraft into a checkpoint-serializable record.
        """

        return CheckpointDraft(
            node_id=draft.node_id,
            content_hash=draft.content_hash,
            content=draft.content,
            content_type=draft.content_type.value
            if hasattr(draft.content_type, "value")
            else str(draft.content_type),
            section=draft.section,
            title=draft.title,
            parent_chunk_index=draft.parent_chunk_index,
            token_count=draft.token_count,
            source_path=draft.source_path,
        )
