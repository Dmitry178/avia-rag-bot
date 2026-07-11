"""Tests for static knowledge-base context in RAG prompts."""

from app.llm.kb_static_context import load_kb_static_context

from tests.paths import RAG_DOCUMENT


def test_load_kb_static_context_includes_chapters_00_and_13() -> None:
    """
    Static RAG context should include guidance and full text for chapters 00 and 13.
    """

    load_kb_static_context.cache_clear()
    context = load_kb_static_context(str(RAG_DOCUMENT))

    assert "Chapter 00" in context
    assert "Chapter 13" in context
    assert "Назначение" in context
    assert "Что бот не отвечает" in context
