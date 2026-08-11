"""Unit tests for schema-driven lane verification and decision-tree guidance."""

import pytest

from unittest.mock import AsyncMock, MagicMock

from app.models.chunk_meta import ChunkMeta
from app.rag.decision_tree import (
    generate_decision_tree_guidance,
    generate_lane_verification_guidance,
    is_decision_tree_no_match,
    is_verification_no_match,
    verification_metadata_key,
)
from app.rag.retrieval_lanes import LanePresentation, RetrievalLane
from app.rag.types import RetrievedChunk


def _chunk(
    *,
    chunk_id: int,
    content_type: str = "decision_tree",
    title: str = "Title",
) -> ChunkMeta:
    """
    Build a minimal chunk row for retrieval and verification tests.
    """

    return ChunkMeta(
        language_code="ru",
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
    content_type: str = "decision_tree",
    title: str = "Title",
    lane: str | None = None,
) -> RetrievedChunk:
    """
    Wrap a chunk row as a scored retrieval hit with optional lane label.
    """

    return RetrievedChunk(
        chunk=_chunk(chunk_id=chunk_id, content_type=content_type, title=title),
        score=score,
        vector_similarity=score,
        retrieval_lane=lane,
    )


def _decision_tree_lane() -> RetrievalLane:
    """
    Return a decision-tree lane with dedicated LLM verification enabled.
    """

    return RetrievalLane(
        id="decision_tree",
        content_types=frozenset({"decision_tree"}),
        top_k=3,
        label="Decision trees",
        description="Chapter 16: step-by-step decision trees",
        min_similarity=0.30,
        presentation=LanePresentation(
            ui_priority=100,
            ui_variant="decision_tree",
            exclude_from_generation_context=True,
            verification_strategy="dedicated_llm",
            verification_no_match_token="NO_DECISION_TREE_MATCH",
            max_verification_candidates=1,
        ),
    )


@pytest.mark.asyncio
async def test_generate_decision_tree_guidance_returns_structured_result() -> None:
    """
    Decision-tree verification should return structured guidance for a matching tree.
    """

    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=(
            "1. Alert security.\n2. Isolate the area.",
            {"model": "test"},
        ),
    )
    tree = _retrieved(
        chunk_id=42,
        score=0.45,
        title="Fire alarm",
        lane="decision_tree",
    )

    guidance = await generate_decision_tree_guidance(
        llm,
        query="What should I do about a fire alarm?",
        tree=tree,
        reply_language="en",
    )

    assert guidance is not None
    assert guidance.chunk_id == 42
    assert guidance.title == "Fire alarm"
    assert "Alert security" in guidance.guidance


def test_is_decision_tree_no_match_recognizes_token() -> None:
    """
    Decision-tree no-match detection should accept the canonical token case-insensitively.
    """

    assert is_decision_tree_no_match("NO_DECISION_TREE_MATCH") is True
    assert is_decision_tree_no_match("  no_decision_tree_match  ") is True
    assert is_decision_tree_no_match("1. Сообщить в пожарную службу.") is False


def test_is_verification_no_match_uses_schema_token() -> None:
    """
    Generic verification no-match checks should honor the lane-specific token from schema.
    """

    assert is_verification_no_match("CUSTOM_NO", no_match_token="CUSTOM_NO") is True
    assert is_verification_no_match("NO_DECISION_TREE_MATCH", no_match_token="CUSTOM_NO") is False


@pytest.mark.asyncio
async def test_generate_decision_tree_guidance_returns_none_on_no_match_token() -> None:
    """
    Decision-tree verification should return None when the LLM emits the no-match token.
    """

    llm = MagicMock()
    llm.complete = AsyncMock(return_value=("NO_DECISION_TREE_MATCH", {"model": "test"}))
    tree = _retrieved(chunk_id=1, score=0.45, lane="decision_tree")

    guidance = await generate_decision_tree_guidance(
        llm,
        query="baggage question",
        tree=tree,
        reply_language="ru",
    )

    assert guidance is None


@pytest.mark.asyncio
async def test_generate_lane_verification_guidance_dispatches_by_ui_variant() -> None:
    """
    Lane verification entrypoint should dispatch decision-tree hits to the tree handler.
    """

    llm = MagicMock()
    llm.complete = AsyncMock(return_value=("1. Step one.", {"model": "test"}))
    hit = _retrieved(chunk_id=7, score=0.5, lane="decision_tree")

    guidance = await generate_lane_verification_guidance(
        llm,
        query="fire",
        hit=hit,
        lane=_decision_tree_lane(),
        reply_language="en",
    )

    assert guidance is not None
    assert guidance.chunk_id == 7


def test_verification_metadata_key_maps_decision_tree_variant() -> None:
    """
    Decision-tree presentation should map to the legacy API metadata key.
    """

    presentation = LanePresentation(ui_variant="decision_tree")
    assert verification_metadata_key(presentation) == "decision_tree_guidance"
