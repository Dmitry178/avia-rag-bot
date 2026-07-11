"""Tests for graceful ETL ingest interruption."""

import asyncio
import pytest

from unittest.mock import MagicMock, patch

from app.exceptions.ingest import IngestInterruptedError
from app.services.etl import ETLService
from app.services.etl_checkpoint import IngestCheckpoint, IngestCheckpointStore
from etl.types import ChunkDraft, ContentType


def _draft(node_id: str, content: str, content_hash: str) -> ChunkDraft:
    return ChunkDraft(
        content=content,
        content_type=ContentType.SOP,
        section="01. Test",
        title="Section",
        node_id=node_id,
        content_hash=content_hash,
        source_path="doc.md",
    )


@pytest.mark.asyncio
async def test_embed_missing_saves_checkpoint_and_raises_on_cancel(tmp_path) -> None:
    """
    Cancelling embedding should persist the checkpoint and raise IngestInterruptedError.
    """

    drafts = [
        _draft("a", "chunk-a", "hash-a"),
        _draft("b", "chunk-b", "hash-b"),
    ]
    checkpoint_store = IngestCheckpointStore(tmp_path / "checkpoint.json")
    checkpoint = IngestCheckpoint(
        source_path="doc.md",
        doc_hash="doc-hash",
        embedding_model="embed-model",
        rebuild=False,
        total_chunks=2,
        vectors_by_hash={},
    )

    async def cancelled_batches(_texts: list[str]):
        yield [[0.1, 0.2]]
        raise asyncio.CancelledError

    service = ETLService(MagicMock())
    mock_embedder = MagicMock()
    mock_embedder.iter_embed_batches = cancelled_batches

    with patch("app.services.etl.EmbeddingClient", return_value=mock_embedder):
        with pytest.raises(IngestInterruptedError) as exc_info:
            await service._embed_missing(
                drafts,
                embed_indices=[0, 1],
                reused_vectors={},
                checkpoint_store=checkpoint_store,
                checkpoint=checkpoint,
                on_progress=None,
            )

    assert exc_info.value.embedded == 1
    assert exc_info.value.total == 2
    loaded = checkpoint_store.load()
    assert loaded is not None
    assert loaded.vectors_by_hash["hash-a"] == [0.1, 0.2]
