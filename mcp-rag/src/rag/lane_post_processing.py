"""Schema-driven post-retrieval lane filtering and verification candidate selection."""

from src.rag.retrieval_lanes import RetrievalRuntime
from src.rag.types import (
    LaneVerificationCandidate,
    RetrievedChunk,
    chunk_similarity,
)


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
