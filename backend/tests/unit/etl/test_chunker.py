"""Universal schema-driven chunker unit tests."""

from app.llm.kb_static_context import load_kb_static_context
from etl.chunking_schema import load_runtime_schema_for_language
from etl.universal_chunker import UniversalChunker

from tests.paths import BACKEND_ROOT, RAG_DOCUMENT_EN, RAG_DOCUMENT_RU


def _chunk_document(language_code: str, document_path: str):
    context = load_runtime_schema_for_language(language_code, str(BACKEND_ROOT))
    chunker = UniversalChunker(context.schema)
    text = RAG_DOCUMENT_RU.read_text(encoding="utf-8") if language_code == "ru" else RAG_DOCUMENT_EN.read_text(encoding="utf-8")
    return chunker.chunk_document(text, source_path=document_path)


def test_chunk_document_produces_expected_categories_ru() -> None:
    """
    Schema-driven chunker should emit expected categories for RU KB.
    """

    chunks = _chunk_document("ru", str(RAG_DOCUMENT_RU))
    types = {chunk.content_type for chunk in chunks}

    assert "sop" in types
    assert "faq" in types
    assert "decision_tree" in types
    assert "scenario" in types
    assert "glossary" not in types
    assert "meta" not in types
    assert "out_of_scope" not in types
    assert len(chunks) >= 200


def test_chunks_have_retrieval_prefix_ru() -> None:
    """
    Every RU chunk should include section and category prefixes.
    """

    chunks = _chunk_document("ru", str(RAG_DOCUMENT_RU))

    assert all("[Раздел:" in chunk.content for chunk in chunks)
    assert all("[Тип:" in chunk.content for chunk in chunks)


def test_faq_chunks_include_source_section_metadata_ru() -> None:
    """
    FAQ chunks should include source-section marker for extracted pairs.
    """

    chunks = _chunk_document("ru", str(RAG_DOCUMENT_RU))
    chapter_faq = [chunk for chunk in chunks if chunk.content_type == "faq" and "01." in chunk.section]

    assert chapter_faq
    assert all("[Источник: 01." in chunk.content for chunk in chapter_faq)
    assert all("**Вопрос:**" in chunk.content for chunk in chapter_faq)


def test_sop_chunks_do_not_embed_trailing_faq_blocks_ru() -> None:
    """
    Embedded FAQ blocks should be split out of SOP chunks.
    """

    chunks = _chunk_document("ru", str(RAG_DOCUMENT_RU))
    sop_with_inline_faq = [chunk for chunk in chunks if chunk.content_type == "sop" and "**Вопрос:**" in chunk.content]

    assert not sop_with_inline_faq


def test_en_chunk_count_matches_ru() -> None:
    """
    RU and EN KB documents should remain structurally close by chunk count.
    """

    ru_chunks = _chunk_document("ru", str(RAG_DOCUMENT_RU))
    en_chunks = _chunk_document("en", str(RAG_DOCUMENT_EN))

    assert abs(len(en_chunks) - len(ru_chunks)) <= 2
    assert len(en_chunks) >= 700
    assert len(ru_chunks) >= 700


def test_en_chunks_use_english_prefix_labels() -> None:
    """
    EN schema should emit English retrieval-prefix labels.
    """

    chunks = _chunk_document("en", str(RAG_DOCUMENT_EN))

    assert chunks
    assert all("[Section:" in chunk.content for chunk in chunks)
    assert all("[Type:" in chunk.content for chunk in chunks)
    assert any("**Question:**" in chunk.content for chunk in chunks if chunk.content_type == "faq")


def test_static_prompt_context_assembled_from_schema_sources() -> None:
    """
    Static prompt context should be built from schema block selectors.
    """

    context = load_kb_static_context(str(RAG_DOCUMENT_RU), language_code="ru")

    assert "Knowledge-base static policies" in context
    assert "Назначение" in context
    assert "Что бот не отвечает" in context
