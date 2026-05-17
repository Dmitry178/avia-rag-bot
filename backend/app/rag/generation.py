"""RAG context formatting and generation prompts."""

from app.llm.prompts import build_system_prompt
from app.rag.types import RetrievedChunk


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    """
    Format retrieved chunks for the LLM system prompt.
    """

    if not chunks:
        return "No relevant knowledge-base excerpts were found."

    parts: list[str] = []

    for index, item in enumerate(chunks, start=1):
        chunk = item.chunk
        parts.append(
            f"[{index}] {chunk.section} / {chunk.title}\n{chunk.content}",
        )

    return "\n\n".join(parts)


def build_rag_system_prompt(*, context: str, reply_language: str | None = None) -> str:
    """
    System prompt for grounded RAG answers.
    """

    base = build_system_prompt(reply_language=reply_language)

    return (
        f"{base}\n\n"
        "Answer using the knowledge-base excerpts below when they are relevant. "
        "If the excerpts do not contain enough information, say so clearly instead of inventing facts. "
        "Cite excerpt numbers like [1] when helpful.\n\n"
        f"Knowledge-base excerpts:\n{context}"
    )
