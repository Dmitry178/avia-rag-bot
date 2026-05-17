"""RAG pipeline unit tests."""

from app.rag.methods.registry import resolve_query_transform_method, resolve_rerank_method
from app.rag.retrieval import reciprocal_rank_fusion
from app.schemas.rag import RagConfig


class _DummyLlm:
    pass


def test_reciprocal_rank_fusion_merges_ranked_lists() -> None:
    """
    Shared chunks should receive higher fused scores.
    """

    fused = reciprocal_rank_fusion(
        [
            [(1, 0.9), (2, 0.8)],
            [(2, 0.95), (3, 0.7)],
        ],
    )

    assert [row_id for row_id, _score in fused] == [2, 1, 3]


def test_resolve_exclusive_query_method_prefers_first_enabled_flag() -> None:
    """
    Only one query transform method should be active at a time.
    """

    method = resolve_query_transform_method(
        RagConfig(use_hyde=True, use_multi_query=True, use_query_rewriting=True),
        _DummyLlm(),  # type: ignore[arg-type]
    )

    assert method is not None
    assert method.name == "hyde"


def test_resolve_rerank_method_when_enabled() -> None:
    """
    Rerank method should be available independently from query transforms.
    """

    method = resolve_rerank_method(RagConfig(use_rerank=True), _DummyLlm())  # type: ignore[arg-type]

    assert method is not None
    assert method.name == "rerank"
