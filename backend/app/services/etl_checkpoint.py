"""Persisted ingest checkpoint for resume after interruption."""

import json

from collections.abc import Iterable
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

    language_code: str
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
        Remove checkpoint file and any leftover atomic-write temp sibling.
        """

        if self._path.is_file():
            self._path.unlink()

        temp_path = self._path.with_suffix(".tmp")
        if temp_path.is_file():
            temp_path.unlink()

    @property
    def path(self) -> Path:
        """
        Return the on-disk checkpoint JSON path.
        """

        return self._path

    @staticmethod
    def is_compatible(
        checkpoint: IngestCheckpoint,
        *,
        language_code: str,
        source_path: str,
        doc_hash: str,
        embedding_model: str,
        rebuild: bool,
    ) -> bool:
        """
        Return True when checkpoint matches the current ingest context.
        """

        return (
            checkpoint.language_code == language_code
            and checkpoint.source_path == source_path
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


def checkpoint_artifact_paths(data_dir: Path, language_code: str) -> tuple[Path, Path]:
    """
    Return checkpoint JSON and temp paths for a knowledge-base language.
    """

    json_path = data_dir / f"ingest_checkpoint_{language_code}.json"
    return json_path, json_path.with_suffix(".tmp")


def cleanup_ingest_temp_files(
    data_dir: Path,
    *,
    language_codes: Iterable[str],
) -> list[Path]:
    """
    Remove ingest checkpoint artifacts after a successful ingest run.

    Safe to call when ingest completed: leftover files are resume-only state.
    """

    removed: list[Path] = []

    for language_code in language_codes:
        store = IngestCheckpointStore(checkpoint_artifact_paths(data_dir, language_code)[0])
        if store.path.is_file() or store.path.with_suffix(".tmp").is_file():
            store.clear()
            removed.append(store.path)

    return removed
