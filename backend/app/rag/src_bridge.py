"""Lazy imports into the canonical ``mcp-rag`` (``src``) package."""

from typing import Any

from app.exceptions.service import ServiceError
from app.llm.chat import ChatCompletionClient
from app.rag.types import RetrievalRuntime, RetrievedChunk


def _import_error(exc: ImportError) -> None:
    raise ServiceError(
        detail="In-process RAG (embed) is not installed in this backend image.",
        error_code="rag_embed_not_installed",
        status_code=503,
    ) from exc


def get_retrieval_runtime(language_code: str) -> RetrievalRuntime:
    """
    Return lane metadata for a KB language.
    """

    try:
        from src.rag.retrieval_lanes import get_retrieval_runtime as _get
    except ImportError:
        return RetrievalRuntime(lanes=(), lane_by_id={})

    return _get(language_code)  # type: ignore[return-value]


async def generate_lane_verification_guidance(
    client: ChatCompletionClient,
    *,
    query: str,
    hit: RetrievedChunk,
    lane: Any,
    reply_language: str,
) -> Any:
    """
    Run lane verification LLM step using the shared decision-tree helper.
    """

    try:
        from src.rag.decision_tree import generate_lane_verification_guidance as _generate
    except ImportError as exc:
        _import_error(exc)

    return await _generate(
        client,
        query=query,
        hit=hit,
        lane=lane,
        reply_language=reply_language,
    )


def build_generation_prompt(
    *,
    context: str,
    language_code: str,
    reply_language: str,
) -> str:
    """
    Build the RAG system prompt from retrieved context.
    """

    try:
        from src.rag.pipeline import RagPipeline
    except ImportError as exc:
        _import_error(exc)

    return RagPipeline.build_generation_prompt(
        context=context,
        language_code=language_code,
        reply_language=reply_language,
    )


def verification_metadata_key(presentation: Any) -> str | None:
    """
    Return metadata key for a lane verification block.
    """

    try:
        from src.rag.decision_tree import verification_metadata_key as _key
    except ImportError as exc:
        _import_error(exc)

    return _key(presentation)


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    """
    Format retrieved chunks for the generation prompt.
    """

    try:
        from src.rag.generation import build_context_block as _build
    except ImportError as exc:
        _import_error(exc)

    return _build(chunks)


def exclude_lane_categories(chunks: list[RetrievedChunk], *, category_ids: set[str]) -> list[RetrievedChunk]:
    """
    Remove chunks that belong to excluded lane categories.
    """

    try:
        from src.rag.lane_post_processing import exclude_lane_categories as _exclude
    except ImportError as exc:
        _import_error(exc)

    return _exclude(chunks, category_ids=category_ids)
