"""Prompt templates for RAG query methods."""

from app.core.rag_constants import MULTI_QUERY_COUNT


def hyde_prompt(query: str) -> str:
    return (
        "Write a short hypothetical knowledge-base passage that would answer the question below. "
        "Write only the passage text, without preamble or labels.\n\n"
        f"Question: {query}"
    )


def multi_query_prompt(query: str, *, count: int = MULTI_QUERY_COUNT) -> str:
    return (
        f"Generate exactly {count} different search queries to retrieve relevant airport knowledge "
        "base documents for the user question. "
        "Return a JSON array of strings only, no markdown.\n\n"
        f"Question: {query}"
    )


def query_rewriting_prompt(query: str, history_text: str) -> str:
    history_block = history_text.strip() or "(no prior messages)"

    return (
        "Rewrite the latest user question into a standalone search query for an airport knowledge base. "
        "Use the conversation only when it is needed to resolve references like «this» or «what next». "
        "Return only the rewritten query text.\n\n"
        f"Conversation:\n{history_block}\n\n"
        f"Latest question: {query}"
    )


def rerank_prompt(query: str, documents: str, *, top_n: int) -> str:
    return (
        f"Rank the numbered documents by relevance to the search query. "
        f"Return JSON only: {{\"indices\": [<up to {top_n} document numbers, most relevant first>]}}.\n\n"
        f"Query: {query}\n\n"
        f"Documents:\n{documents}"
    )
