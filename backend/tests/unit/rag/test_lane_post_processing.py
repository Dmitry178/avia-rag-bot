"""Schema-driven lane post-processing unit tests."""

from app.rag.lane_post_processing import (
    apply_lane_similarity_filters,
    exclude_lane_categories,
    select_verification_candidates,
)
from app.rag.retrieval_lanes import LanePresentation, RetrievalLane, RetrievalRuntime
from app.rag.types import RetrievedChunk


def _lane(
    lane_id: str,
    *,
    min_similarity: float = 0.0,
    presentation: LanePresentation | None = None,
) -> RetrievalLane:
    return RetrievalLane(
        id=lane_id,
        content_types=frozenset({lane_id}),
        top_k=3,
        label=lane_id,
        min_similarity=min_similarity,
        presentation=presentation or LanePresentation(),
    )


def _hit(chunk_id: int, score: float, *, content_type: str, lane: str) -> RetrievedChunk:
    from app.models.chunk_meta import ChunkMeta

    return RetrievedChunk(
        chunk=ChunkMeta(
            language_code="ru",
            id=chunk_id,
            content="body",
            content_type=content_type,
            section="01. Test",
            title="Title",
            node_id=f"node-{chunk_id}",
        ),
        score=score,
        vector_similarity=score,
        retrieval_lane=lane,
    )


def test_apply_lane_similarity_filters_uses_schema_thresholds() -> None:
    runtime = RetrievalRuntime(
        lanes=(
            _lane("sop", min_similarity=0.0),
            _lane("decision_tree", min_similarity=0.30),
        ),
        lane_by_id={},
    )
    runtime = RetrievalRuntime(lanes=runtime.lanes, lane_by_id={lane.id: lane for lane in runtime.lanes})

    lane_results = {
        "sop": [_hit(1, 0.10, content_type="sop", lane="sop")],
        "decision_tree": [
            _hit(2, 0.45, content_type="decision_tree", lane="decision_tree"),
            _hit(3, 0.20, content_type="decision_tree", lane="decision_tree"),
        ],
    }

    filtered = apply_lane_similarity_filters(lane_results, runtime=runtime)

    assert [item.chunk.id for item in filtered["sop"]] == [1]
    assert [item.chunk.id for item in filtered["decision_tree"]] == [2]


def test_select_verification_candidates_respects_presentation_config() -> None:
    runtime = RetrievalRuntime(
        lanes=(
            _lane(
                "decision_tree",
                min_similarity=0.30,
                presentation=LanePresentation(
                    ui_priority=100,
                    ui_variant="decision_tree",
                    verification_strategy="dedicated_llm",
                    max_verification_candidates=1,
                ),
            ),
        ),
        lane_by_id={},
    )
    runtime = RetrievalRuntime(lanes=runtime.lanes, lane_by_id={lane.id: lane for lane in runtime.lanes})

    lane_results = {
        "decision_tree": [
            _hit(2, 0.45, content_type="decision_tree", lane="decision_tree"),
            _hit(3, 0.40, content_type="decision_tree", lane="decision_tree"),
        ],
    }

    candidates = select_verification_candidates(lane_results, runtime=runtime)

    assert len(candidates) == 1
    assert candidates[0].hit.chunk.id == 2
    assert candidates[0].lane.presentation.ui_variant == "decision_tree"


def test_exclude_lane_categories_removes_only_configured_types() -> None:
    chunks = [
        _hit(1, 0.9, content_type="sop", lane="sop"),
        _hit(2, 0.8, content_type="decision_tree", lane="decision_tree"),
        _hit(3, 0.7, content_type="faq", lane="faq"),
    ]

    filtered = exclude_lane_categories(chunks, category_ids=frozenset({"decision_tree"}))

    assert [item.chunk.id for item in filtered] == [1, 3]
