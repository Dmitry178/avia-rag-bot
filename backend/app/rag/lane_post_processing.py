"""Schema-driven post-retrieval lane filtering and verification candidate selection."""

from dataclasses import dataclass

from app.rag.decision_tree import chunk_similarity
from app.rag.retrieval_lanes import RetrievalLane, RetrievalRuntime
from app.rag.types import RetrievedChunk


@dataclass(frozen=True)
class LaneVerificationCandidate:
    """
    One lane hit selected for optional dedicated LLM verification.
    """

    lane: RetrievalLane
    hit: RetrievedChunk


def apply_lane_similarity_filters(
    lane_results: dict[str, list[RetrievedChunk]],
    *,
    runtime: RetrievalRuntime,
) -> dict[str, list[RetrievedChunk]]:
    """
    Drop lane hits below the schema-defined min_similarity threshold.
    """

    filtered: dict[str, list[RetrievedChunk]] = {}

    for lane in runtime.lanes:
        hits = lane_results.get(lane.id, [])
        filtered[lane.id] = [hit for hit in hits if chunk_similarity(hit) >= lane.min_similarity]

    return filtered


def select_verification_candidates(
    lane_results: dict[str, list[RetrievedChunk]],
    *,
    runtime: RetrievalRuntime,
) -> list[LaneVerificationCandidate]:
    """
    Pick lane hits that require dedicated LLM verification, ordered by ui_priority.
    """

    candidates: list[LaneVerificationCandidate] = []

    for lane in runtime.lanes:
        if lane.presentation.verification_strategy != "dedicated_llm":
            continue

        hits = lane_results.get(lane.id, [])
        for hit in hits[: lane.presentation.max_verification_candidates]:
            candidates.append(LaneVerificationCandidate(lane=lane, hit=hit))

    return sorted(candidates, key=lambda item: item.lane.presentation.ui_priority, reverse=True)


def exclude_lane_categories(
    chunks: list[RetrievedChunk],
    *,
    category_ids: frozenset[str],
) -> list[RetrievedChunk]:
    """
    Remove chunks that belong to the given category ids from a context list.
    """

    return [item for item in chunks if item.chunk.content_type not in category_ids]
