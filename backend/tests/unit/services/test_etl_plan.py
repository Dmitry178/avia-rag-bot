"""Unit tests for incremental ingest planning."""

from app.models.chunk_meta import ChunkMeta
from app.services.etl_plan import plan_ingest
from etl.types import ChunkDraft, ContentType


def _draft(node_id: str, content: str, content_hash: str) -> ChunkDraft:
    return ChunkDraft(
        content=content,
        content_type=ContentType.SOP,
        section="01. Test",
        title="Test",
        node_id=node_id,
        content_hash=content_hash,
    )


def _chunk(node_id: str, content_hash: str, chunk_id: int = 0) -> ChunkMeta:
    return ChunkMeta(
        id=chunk_id,
        content="body",
        content_type="sop",
        section="01. Test",
        title="Test",
        node_id=node_id,
        content_hash=content_hash,
    )


def test_plan_reuses_unchanged_chunks_from_faiss() -> None:
    drafts = [_draft("01.a", "same", "hash-a")]
    existing = [_chunk("01.a", "hash-a", chunk_id=0)]
    vectors = [[0.1, 0.2]]

    plan = plan_ingest(
        drafts,
        existing,
        vectors,
        {},
        rebuild=False,
        can_reuse_existing=True,
    )

    assert plan.embed_indices == []
    assert plan.reused_vectors == {0: [0.1, 0.2]}
    assert plan.stats.unchanged == 1
    assert plan.stats.added == 0
    assert plan.stats.updated == 0
    assert plan.stats.removed == 0


def test_plan_embeds_changed_and_new_chunks() -> None:
    drafts = [
        _draft("01.a", "changed", "hash-a2"),
        _draft("01.b", "new", "hash-b"),
    ]
    existing = [_chunk("01.a", "hash-a", chunk_id=0)]
    vectors = [[0.1, 0.2]]

    plan = plan_ingest(
        drafts,
        existing,
        vectors,
        {},
        rebuild=False,
        can_reuse_existing=True,
    )

    assert plan.embed_indices == [0, 1]
    assert plan.reused_vectors == {}
    assert plan.stats.updated == 1
    assert plan.stats.added == 1
    assert plan.stats.removed == 0


def test_plan_marks_removed_chunks() -> None:
    drafts = [_draft("01.b", "new", "hash-b")]
    existing = [
        _chunk("01.a", "hash-a", chunk_id=0),
        _chunk("01.b", "hash-b", chunk_id=1),
    ]
    vectors = [[0.1], [0.2]]

    plan = plan_ingest(
        drafts,
        existing,
        vectors,
        {},
        rebuild=False,
        can_reuse_existing=True,
    )

    assert plan.embed_indices == []
    assert plan.reused_vectors == {0: [0.2]}
    assert plan.stats.removed == 1
    assert plan.stats.unchanged == 1


def test_plan_uses_checkpoint_vectors_before_existing() -> None:
    drafts = [_draft("01.a", "same", "hash-a")]
    existing = [_chunk("01.a", "hash-a", chunk_id=0)]
    vectors = [[0.1, 0.2]]

    plan = plan_ingest(
        drafts,
        existing,
        vectors,
        {"hash-a": [0.9, 0.8]},
        rebuild=False,
        can_reuse_existing=True,
    )

    assert plan.embed_indices == []
    assert plan.reused_vectors == {0: [0.9, 0.8]}


def test_plan_rebuild_embeds_everything() -> None:
    drafts = [_draft("01.a", "same", "hash-a")]
    existing = [_chunk("01.a", "hash-a", chunk_id=0)]
    vectors = [[0.1, 0.2]]

    plan = plan_ingest(
        drafts,
        existing,
        vectors,
        {"hash-a": [0.9, 0.8]},
        rebuild=True,
        can_reuse_existing=False,
    )

    assert plan.embed_indices == []
    assert plan.reused_vectors == {0: [0.9, 0.8]}
