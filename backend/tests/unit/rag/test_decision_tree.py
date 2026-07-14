"""Decision-tree RAG unit tests."""

import pytest

from unittest.mock import AsyncMock, MagicMock

from etl.types import ContentType
from app.models.chunk_meta import ChunkMeta
from app.rag.decision_tree import (
    exclude_decision_tree_chunks,
    generate_decision_tree_guidance,
    is_decision_tree_no_match,
    select_applicable_decision_trees,
)
from app.rag.types import RetrievedChunk


def _chunk(
    *,
    chunk_id: int,
    content_type: str = ContentType.SOP.value,
    title: str = "Title",
) -> ChunkMeta:
    return ChunkMeta(
        id=chunk_id,
        content=f"content-{chunk_id}",
        content_type=content_type,
        section="01. Section",
        title=title,
        node_id=f"node-{chunk_id}",
    )


def _retrieved(
    *,
    chunk_id: int,
    score: float,
    content_type: str = ContentType.SOP.value,
    title: str = "Title",
    lane: str | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=_chunk(chunk_id=chunk_id, content_type=content_type, title=title),
        score=score,
        vector_similarity=score,
        retrieval_lane=lane,
    )


def test_select_applicable_decision_trees_filters_by_similarity() -> None:
    """
    Only decision-tree lane hits above the threshold should be selected.
    """

    lane_results = {
        "decision_tree": [
            _retrieved(chunk_id=1, score=0.45, content_type=ContentType.DECISION_TREE.value, lane="decision_tree"),
            _retrieved(chunk_id=2, score=0.20, content_type=ContentType.DECISION_TREE.value, lane="decision_tree"),
        ],
    }

    selected = select_applicable_decision_trees(lane_results, min_similarity=0.30)

    assert [item.chunk.id for item in selected] == [1]


def test_select_applicable_decision_trees_limits_count() -> None:
    """
    At most one decision tree should be processed per query.
    """

    lane_results = {
        "decision_tree": [
            _retrieved(chunk_id=1, score=0.50, content_type=ContentType.DECISION_TREE.value, lane="decision_tree"),
            _retrieved(chunk_id=2, score=0.40, content_type=ContentType.DECISION_TREE.value, lane="decision_tree"),
        ],
    }

    selected = select_applicable_decision_trees(lane_results, min_similarity=0.30, max_trees=1)

    assert len(selected) == 1
    assert selected[0].chunk.id == 1


def test_exclude_decision_tree_chunks_removes_only_decision_trees() -> None:
    """
    General RAG context should keep SOP/FAQ chunks but drop decision trees.
    """

    chunks = [
        _retrieved(chunk_id=1, score=0.9, content_type=ContentType.SOP.value),
        _retrieved(chunk_id=2, score=0.8, content_type=ContentType.DECISION_TREE.value),
        _retrieved(chunk_id=3, score=0.7, content_type=ContentType.FAQ.value),
    ]

    filtered = exclude_decision_tree_chunks(chunks)

    assert [item.chunk.id for item in filtered] == [1, 3]


@pytest.mark.asyncio
async def test_generate_decision_tree_guidance_returns_structured_result() -> None:
    """
    Dedicated decision-tree generation should return metadata-ready guidance.
    """

    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=(
            "1. Сообщить в пожарную службу.\n2. Начать эвакуацию.",
            {"latency_ms": 10},
        ),
    )

    tree = _retrieved(
        chunk_id=708,
        score=0.4462,
        content_type=ContentType.DECISION_TREE.value,
        title="Обнаружение пожара",
        lane="decision_tree",
    )
    tree.chunk.section = "16. Decision Trees"
    tree.chunk.content = "Сработала пожарная сигнализация..."

    guidance = await generate_decision_tree_guidance(
        llm,
        query="пожар",
        tree=tree,
        reply_language="ru",
    )

    assert guidance is not None
    assert guidance.chunk_id == 708
    assert guidance.title == "Обнаружение пожара"
    assert "пожарную службу" in guidance.guidance
    assert guidance.to_metadata()["similarity"] == 0.4462


def test_is_decision_tree_no_match_recognizes_token() -> None:
    """
    The no-match token should suppress operational card rendering.
    """

    assert is_decision_tree_no_match("NO_DECISION_TREE_MATCH") is True
    assert is_decision_tree_no_match("  no_decision_tree_match  ") is True
    assert is_decision_tree_no_match("NO_DECISION_TREE_MATCH\n") is True
    assert is_decision_tree_no_match("NO_DECISION_TREE_MATCH.") is True
    assert is_decision_tree_no_match("`NO_DECISION_TREE_MATCH`") is True
    assert is_decision_tree_no_match("**NO_DECISION_TREE_MATCH**") is True
    assert is_decision_tree_no_match("") is True
    assert (
        is_decision_tree_no_match(
            "The decision tree is about a suspicious object, but your question does not fit.\n\n"
            "NO_DECISION_TREE_MATCH",
        )
        is True
    )
    assert is_decision_tree_no_match("1. Сообщить в пожарную службу.") is False


@pytest.mark.asyncio
async def test_generate_decision_tree_guidance_returns_none_on_no_match_token() -> None:
    """
    Backend must discard the codeword and not expose a guidance card.
    """

    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=(
            "NO_DECISION_TREE_MATCH",
            {"latency_ms": 5},
        ),
    )

    tree = _retrieved(
        chunk_id=2,
        score=0.45,
        content_type=ContentType.DECISION_TREE.value,
        title="Реагирование на подозрительный предмет",
        lane="decision_tree",
    )
    tree.chunk.content = "Обнаружен неопознанный предмет..."

    guidance = await generate_decision_tree_guidance(
        llm,
        query="что делать, если при погрузке негабаритного груза он высыпался на ВПП?",
        tree=tree,
        reply_language="ru",
    )

    assert guidance is None


@pytest.mark.asyncio
async def test_generate_decision_tree_guidance_returns_none_on_formatted_no_match_token() -> None:
    """
    Markdown-wrapped no-match tokens must not be persisted as guidance.
    """

    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=(
            "**NO_DECISION_TREE_MATCH**",
            {"latency_ms": 5},
        ),
    )

    tree = _retrieved(
        chunk_id=2,
        score=0.45,
        content_type=ContentType.DECISION_TREE.value,
        title="Реагирование на подозрительный предмет",
        lane="decision_tree",
    )

    guidance = await generate_decision_tree_guidance(
        llm,
        query="подозрительная сумка",
        tree=tree,
        reply_language="ru",
    )

    assert guidance is None


@pytest.mark.asyncio
async def test_generate_decision_tree_guidance_returns_none_when_token_follows_explanation() -> None:
    """
    Explanatory text plus the no-match token must still be discarded.
    """

    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=(
            "The decision tree provided is about responding to a suspicious object, "
            'but your question "what can i do" does not match.\n\n'
            "NO_DECISION_TREE_MATCH",
            {"latency_ms": 5},
        ),
    )

    tree = _retrieved(
        chunk_id=2,
        score=0.45,
        content_type=ContentType.DECISION_TREE.value,
        title="Реагирование на подозрительный предмет",
        lane="decision_tree",
    )

    guidance = await generate_decision_tree_guidance(
        llm,
        query="what can i do",
        tree=tree,
        reply_language="en",
    )

    assert guidance is None


@pytest.mark.asyncio
async def test_generate_decision_tree_guidance_uses_dedicated_prompt_without_hardening() -> None:
    """
    Decision-tree calls should bypass the general aviation system prompt.
    """

    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=(
            "NO_DECISION_TREE_MATCH",
            {"latency_ms": 5},
        ),
    )

    tree = _retrieved(
        chunk_id=2,
        score=0.45,
        content_type=ContentType.DECISION_TREE.value,
        title="Реагирование на подозрительный предмет",
        lane="decision_tree",
    )

    await generate_decision_tree_guidance(
        llm,
        query="подозрительная сумка",
        tree=tree,
        reply_language="ru",
    )

    _messages, kwargs = llm.complete.call_args
    system_prompt = kwargs["system_prompt"]
    assert "NO_DECISION_TREE_MATCH" in system_prompt
    assert "Я могу отвечать только" not in system_prompt
    assert kwargs["harden_user_messages"] is False
