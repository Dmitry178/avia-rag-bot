"""Serialize RAG pipeline results for MCP tool responses."""

from src.rag.retrieval_lanes import get_retrieval_runtime
from src.rag.types import RagPipelineResult, RagTraceStep, chunk_similarity


def serialize_trace(trace: list[RagTraceStep]) -> list[dict]:
    """
    Convert pipeline trace steps to the JSON shape expected by ChatService / UI.
    """

    return [
        {
            "step": step.step,
            "duration_ms": step.duration_ms,
            "data": step.data,
        }
        for step in trace
    ]


def serialize_rag_pipeline_result(result: RagPipelineResult, *, language_code: str) -> dict:
    """
    Convert ``RagPipelineResult`` to the MCP ``retrieve`` output contract.
    """

    lane_by_id = get_retrieval_runtime(language_code).lane_by_id
    chunks: list[dict] = []

    for item in result.chunks:
        chunk = item.chunk
        if chunk.id is None:
            continue

        similarity = round(chunk_similarity(item), 4)
        lane_id = item.retrieval_lane or chunk.content_type
        lane_meta = lane_by_id.get(lane_id)
        lane_label = lane_meta.label if lane_meta is not None else lane_id

        chunks.append(
            {
                "id": chunk.id,
                "section": chunk.section,
                "title": chunk.title,
                "content_type": chunk.content_type,
                "retrieval_lane": lane_id,
                "retrieval_lane_label": lane_label,
                "similarity": similarity,
                "score": similarity,
                "content_preview": chunk.content[:600],
            },
        )

    verification_candidates = [
        {
            "lane_id": candidate.lane.id,
            "chunk_id": candidate.hit.chunk.id,
        }
        for candidate in result.verification_candidates
        if candidate.hit.chunk.id is not None
    ]

    applicable_decision_trees = [
        {"chunk_id": item.chunk.id}
        for item in result.applicable_decision_trees
        if item.chunk.id is not None
    ]

    return {
        "context": result.context,
        "search_queries": result.search_queries,
        "chunks": chunks,
        "trace": serialize_trace(result.trace),
        "verification_candidates": verification_candidates,
        "applicable_decision_trees": applicable_decision_trees,
    }
