"""Vector retrieval unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.chunk_meta import ChunkMeta
from app.rag.retrieval import VectorRetriever, dedupe_retrieved_chunks
from app.rag.retrieval_lanes import FAQ_LANE, SOP_LANE
from app.rag.types import RetrievedChunk


def _chunk(
    chunk_id: int,
    *,
    content_type: str,
    section: str = "01. Test",
) -> ChunkMeta:
    return ChunkMeta(
        id=chunk_id,
        content="body",
        content_type=content_type,
        section=section,
        title=f"Title {chunk_id}",
        node_id=f"node-{chunk_id}",
    )


@pytest.mark.asyncio
async def test_search_lane_filters_by_content_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Lane search should return only chunks of the requested content type.
    """

    chunks_by_id = {
        1: _chunk(1, content_type="sop"),
        2: _chunk(2, content_type="faq", section="14. FAQ"),
        3: _chunk(3, content_type="sop"),
    }
    embedder = MagicMock()
    embedder.embed_texts = AsyncMock(return_value=[[0.1, 0.2]])

    async def fake_search(_path, _vector, _top_k):
        return [3, 2, 1], [0.9, 0.8, 0.7]

    monkeypatch.setattr(
        "app.rag.retrieval.faiss_manager.search_async",
        AsyncMock(side_effect=fake_search),
    )

    retriever = VectorRetriever(
        index_path=MagicMock(),
        embedder=embedder,
        chunks_by_id=chunks_by_id,
    )

    hits = await retriever.search_lane(["baggage rules"], lane=SOP_LANE)

    assert len(hits) == 2
    assert all(hit.chunk.content_type == "sop" for hit in hits)
    assert all(hit.retrieval_lane == "sop" for hit in hits)


@pytest.mark.asyncio
async def test_search_lane_faq_includes_per_chapter_faq(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    FAQ lane should surface FAQ chunks from chapter 14 and SOP chapters.
    """

    chunks_by_id = {
        10: _chunk(10, content_type="faq", section="01. Общие правила"),
        11: _chunk(11, content_type="faq", section="14. FAQ"),
        12: _chunk(12, content_type="sop"),
    }
    embedder = MagicMock()
    embedder.embed_texts = AsyncMock(return_value=[[0.1, 0.2]])

    async def fake_search(_path, _vector, _top_k):
        return [12, 11, 10], [0.9, 0.85, 0.8]

    monkeypatch.setattr(
        "app.rag.retrieval.faiss_manager.search_async",
        AsyncMock(side_effect=fake_search),
    )

    retriever = VectorRetriever(
        index_path=MagicMock(),
        embedder=embedder,
        chunks_by_id=chunks_by_id,
    )

    hits = await retriever.search_lane(["personal devices"], lane=FAQ_LANE)

    assert [hit.chunk.id for hit in hits] == [11, 10]
    assert hits[0].chunk.section.startswith("14.")


def test_dedupe_retrieved_chunks_keeps_best_score() -> None:
    """
    Duplicate chunk ids across lanes should keep the highest score.
    """

    chunk = _chunk(5, content_type="sop")
    deduped = dedupe_retrieved_chunks(
        [
            RetrievedChunk(chunk=chunk, score=0.5, retrieval_lane="sop"),
            RetrievedChunk(chunk=chunk, score=0.9, retrieval_lane="faq"),
        ],
    )

    assert len(deduped) == 1
    assert deduped[0].score == 0.9
