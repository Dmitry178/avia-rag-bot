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


_RAG_GROUNDING_RULES = (
    "The excerpts below were retrieved automatically; they may or may not answer the user's question. "
    "Your job is to judge semantic fit: use an excerpt only if it substantively addresses what was asked. "
    "Treat excerpts as irrelevant when they discuss a different topic, provide meta-information "
    "instead of an answer, or relate to the query only loosely rather than answering it. "
    "When no excerpt adequately answers the question, reply briefly that nothing matching was found "
    "in the knowledge base and ask the user to clarify or rephrase. "
    "Do not invent facts, do not repeat the user's message as the answer, and keep the refusal short. "
    "Russian: «В базе знаний не найдено информации по вашему вопросу. "
    "Пожалуйста, уточните или переформулируйте вопрос.» "
    "English: \"No information matching your question was found in the knowledge base. "
    "Please clarify or rephrase your question.\" "
    "Match the user's language (Cyrillic → Russian, otherwise English). "
    "Reference an excerpt by its number only when that excerpt directly supports a claim in your answer."
)


def build_rag_system_prompt(
    *,
    context: str,
    reply_language: str | None = None,
    kb_static_context: str = "",
) -> str:
    """
    System prompt for grounded RAG answers.
    """

    base = build_system_prompt(reply_language=reply_language)
    static_block = f"\n\n{kb_static_context.strip()}" if kb_static_context.strip() else ""

    return (
        f"{base}{static_block}\n\n"
        f"{_RAG_GROUNDING_RULES}\n\n"
        f"Knowledge-base excerpts:\n{context}"
    )
