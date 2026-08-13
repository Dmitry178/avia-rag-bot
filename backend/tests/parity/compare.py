"""Helpers to compare embed and MCP ``RagPipelineResult`` payloads."""

from app.rag.types import RagPipelineResult, RetrievedChunk


def chunk_ids(chunks: list[RetrievedChunk]) -> list[int]:
    """
    Return retrieved chunk database ids in stable order.
    """

    return [item.chunk.id for item in chunks if item.chunk.id is not None]


def chunk_similarities(chunks: list[RetrievedChunk]) -> list[float]:
    """
    Return similarity scores aligned with ``chunk_ids`` order.
    """

    values: list[float] = []

    for item in chunks:
        if item.chunk.id is None:
            continue

        score = item.vector_similarity if item.vector_similarity is not None else item.score
        values.append(float(score))

    return values


def trace_step_names(result: RagPipelineResult) -> list[str]:
    """
    Return ordered trace step names.
    """

    return [step.step for step in result.trace]


def normalize_context(context: str) -> str:
    """
    Normalize whitespace for context string comparison.
    """

    return "\n".join(line.rstrip() for line in context.strip().splitlines())


def assert_retrieve_parity(
    embed_result: RagPipelineResult,
    mcp_result: RagPipelineResult,
    *,
    similarity_tolerance: float = 0.0001,
) -> None:
    """
    Assert embed and MCP retrieval outputs match parity contract (§8).
    """

    embed_ids = chunk_ids(embed_result.chunks)
    mcp_ids = chunk_ids(mcp_result.chunks)
    assert embed_ids == mcp_ids, f"chunk ids differ: embed={embed_ids} mcp={mcp_ids}"

    embed_scores = chunk_similarities(embed_result.chunks)
    mcp_scores = chunk_similarities(mcp_result.chunks)
    assert len(embed_scores) == len(mcp_scores)

    for index, (left, right) in enumerate(zip(embed_scores, mcp_scores, strict=True)):
        assert abs(left - right) <= similarity_tolerance, (
            f"similarity mismatch at index {index}: embed={left} mcp={right}"
        )

    assert normalize_context(embed_result.context) == normalize_context(mcp_result.context), (
        "assembled context strings differ"
    )

    assert trace_step_names(embed_result) == trace_step_names(mcp_result), (
        f"trace steps differ: embed={trace_step_names(embed_result)} mcp={trace_step_names(mcp_result)}"
    )
