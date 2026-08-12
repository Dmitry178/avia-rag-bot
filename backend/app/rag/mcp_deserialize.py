"""Deserialize MCP retrieve tool payloads into backend RAG types."""

import json

from datetime import UTC, datetime

from app.exceptions.service import ServiceError
from app.rag.src_bridge import get_retrieval_runtime
from app.rag.types import (
    ChunkRecord,
    LaneVerificationCandidate,
    RagPipelineResult,
    RagTraceStep,
    RetrievedChunk,
)


def _chunk_from_payload(payload: dict, *, language_code: str) -> ChunkRecord:
    """
    Build a minimal chunk row from an MCP chunk dictionary.
    """

    preview = str(payload.get("content_preview", ""))
    return ChunkRecord(
        language_code=language_code,
        id=int(payload["id"]),
        content=preview,
        content_type=str(payload.get("content_type", "")),
        section=str(payload.get("section", "")),
        title=str(payload.get("title", "")),
        node_id="",
        content_hash="",
        token_count=max(len(preview) // 4, 0),
        source_path="",
        created_at=datetime.now(UTC),
    )


def _hydrate_chunks(payloads: list[dict], *, language_code: str) -> dict[int, ChunkRecord]:
    """
    Build chunk rows from MCP payload fields (backend has no KB tables).
    """

    hydrated: dict[int, ChunkRecord] = {}

    for payload in payloads:
        chunk_id = int(payload["id"])
        hydrated[chunk_id] = _chunk_from_payload(payload, language_code=language_code)

    return hydrated


def _build_retrieved_chunk(
    payload: dict,
    *,
    chunks_by_id: dict[int, ChunkRecord],
    language_code: str,
) -> RetrievedChunk | None:
    chunk_id = payload.get("id")
    if chunk_id is None:
        return None

    chunk = chunks_by_id.get(int(chunk_id))
    if chunk is None:
        chunk = _chunk_from_payload(payload, language_code=language_code)

    score = float(payload.get("score", payload.get("similarity", 0.0)))
    similarity = payload.get("similarity")
    vector_similarity = float(similarity) if similarity is not None else score

    return RetrievedChunk(
        chunk=chunk,
        score=score,
        vector_similarity=vector_similarity,
        retrieval_lane=str(payload.get("retrieval_lane") or chunk.content_type),
    )


async def deserialize_mcp_retrieve_result(
    payload: dict,
    *,
    language_code: str,
) -> RagPipelineResult:
    """
    Convert the MCP ``retrieve`` JSON contract into ``RagPipelineResult``.
    """

    if payload.get("error_code"):
        raise ServiceError(
            detail=str(payload.get("detail", "MCP retrieve failed")),
            error_code=str(payload["error_code"]),
            status_code=int(payload.get("status_code", 500)),
        )

    runtime = get_retrieval_runtime(language_code)
    chunk_payloads = list(payload.get("chunks", []))
    chunks_by_id = _hydrate_chunks(chunk_payloads, language_code=language_code)

    chunks: list[RetrievedChunk] = []

    for chunk_payload in chunk_payloads:
        item = _build_retrieved_chunk(
            chunk_payload,
            chunks_by_id=chunks_by_id,
            language_code=language_code,
        )
        if item is not None:
            chunks.append(item)

    trace = [
        RagTraceStep(
            step=str(step["step"]),
            duration_ms=int(step.get("duration_ms", 0)),
            data=dict(step.get("data", {})),
        )
        for step in payload.get("trace", [])
    ]

    verification_candidates: list[LaneVerificationCandidate] = []

    for candidate in payload.get("verification_candidates", []):
        lane_id = str(candidate.get("lane_id", ""))
        chunk_id = candidate.get("chunk_id")
        lane = runtime.lane_by_id.get(lane_id)

        if lane is None or chunk_id is None:
            continue

        hit_payload = {"id": chunk_id, "score": 0.0, "retrieval_lane": lane_id}
        hit = _build_retrieved_chunk(
            hit_payload,
            chunks_by_id=chunks_by_id,
            language_code=language_code,
        )

        if hit is not None:
            verification_candidates.append(LaneVerificationCandidate(lane=lane, hit=hit))

    applicable_decision_trees: list[RetrievedChunk] = []
    for tree in payload.get("applicable_decision_trees", []):
        chunk_id = tree.get("chunk_id")
        if chunk_id is None:
            continue

        item = _build_retrieved_chunk(
            {"id": chunk_id, "score": 0.0, "retrieval_lane": "decision_tree"},
            chunks_by_id=chunks_by_id,
            language_code=language_code,
        )

        if item is not None:
            applicable_decision_trees.append(item)

    return RagPipelineResult(
        context=str(payload.get("context", "")),
        chunks=chunks,
        trace=trace,
        search_queries=[str(item) for item in payload.get("search_queries", [])],
        verification_candidates=verification_candidates,
        applicable_decision_trees=applicable_decision_trees,
    )


def parse_mcp_tool_payload(result: object) -> dict:
    """
    Extract a JSON object from an MCP ``call_tool`` response.
    """

    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured

    is_error = bool(getattr(result, "isError", False))
    content = getattr(result, "content", None) or []

    texts: list[str] = []

    for block in content:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)

    if not texts:
        if is_error:
            raise ServiceError(
                detail="MCP tool returned an error without a payload",
                error_code="mcp_tool_error",
                status_code=502,
            )
        raise ServiceError(
            detail="MCP tool returned empty content",
            error_code="mcp_empty_response",
            status_code=502,
        )

    combined = "\n".join(texts).strip()

    try:
        payload = json.loads(combined)
    except json.JSONDecodeError as exc:
        raise ServiceError(
            detail=f"MCP tool returned non-JSON content: {combined[:200]}",
            error_code="mcp_invalid_json",
            status_code=502,
        ) from exc

    if not isinstance(payload, dict):
        raise ServiceError(
            detail="MCP tool JSON payload must be an object",
            error_code="mcp_invalid_json",
            status_code=502,
        )

    if is_error:
        raise ServiceError(
            detail=str(payload.get("detail", combined)),
            error_code=str(payload.get("error_code", "mcp_tool_error")),
            status_code=int(payload.get("status_code", 502)),
        )

    return payload
