"""ETL parser and chunker unit tests."""

import pytest

from etl.chunker import chunk_document
from etl.parser import parse_markdown
from etl.profile import get_document_profile
from etl.static_sections import extract_static_prompt_sections
from etl.types import ContentType

from tests.paths import RAG_DOCUMENT, RAG_DOCUMENT_EN, RAG_DOCUMENT_RU


@pytest.fixture
def ru_profile():
    """
    Russian KB document profile.
    """

    return get_document_profile("ru")


@pytest.fixture
def en_profile():
    """
    English KB document profile.
    """

    return get_document_profile("en")


def test_parse_markdown_finds_all_main_sections(ru_profile) -> None:
    """
    Parser should extract intro, FAQ, and glossary sections from the RAG document.
    """

    text = RAG_DOCUMENT.read_text(encoding="utf-8")
    nodes = parse_markdown(text, profile=ru_profile, source_path=str(RAG_DOCUMENT))
    sections = {node.section for node in nodes if node.level == 1 or node.level == 2}

    assert any("00." in section for section in sections)
    assert any("14." in section or "FAQ" in section for section in sections)
    assert any("15." in section or "Глоссарий" in section for section in sections)


def test_chunk_document_produces_expected_types(ru_profile) -> None:
    """
    Chunker should emit indexed content types and skip meta, out-of-scope, and glossary.
    """

    text = RAG_DOCUMENT.read_text(encoding="utf-8")
    chunks = chunk_document(text, profile=ru_profile, source_path=str(RAG_DOCUMENT))
    types = {chunk.content_type for chunk in chunks}

    assert ContentType.SOP in types
    assert ContentType.FAQ in types
    assert ContentType.DECISION_TREE in types
    assert ContentType.SCENARIO in types
    assert ContentType.GLOSSARY not in types
    assert ContentType.META not in types
    assert ContentType.OUT_OF_SCOPE not in types
    assert len(chunks) >= 200


def test_chunks_have_retrieval_prefix(ru_profile) -> None:
    """
    Every chunk should include section and content-type retrieval prefixes.
    """

    text = RAG_DOCUMENT.read_text(encoding="utf-8")
    chunks = chunk_document(text, profile=ru_profile, source_path=str(RAG_DOCUMENT))

    assert all("[Раздел:" in chunk.content for chunk in chunks)
    assert all("[Тип:" in chunk.content for chunk in chunks)


def test_faq_chunks_include_source_section_metadata(ru_profile) -> None:
    """
    FAQ pairs extracted from SOP chapters should carry the source chapter in metadata.
    """

    text = RAG_DOCUMENT.read_text(encoding="utf-8")
    chunks = chunk_document(text, profile=ru_profile, source_path=str(RAG_DOCUMENT))
    chapter_faq = [
        chunk
        for chunk in chunks
        if chunk.content_type == ContentType.FAQ and "01." in chunk.section
    ]

    assert chapter_faq
    assert all("[Источник: 01." in chunk.content for chunk in chapter_faq)
    assert all("**Вопрос:**" in chunk.content for chunk in chapter_faq)


def test_sop_chunks_do_not_embed_trailing_faq_blocks(ru_profile) -> None:
    """
    Trailing FAQ blocks must be extracted from SOP chunks, not left inline.
    """

    text = RAG_DOCUMENT.read_text(encoding="utf-8")
    chunks = chunk_document(text, profile=ru_profile, source_path=str(RAG_DOCUMENT))
    sop_with_inline_faq = [
        chunk
        for chunk in chunks
        if chunk.content_type == ContentType.SOP and "**Вопрос:**" in chunk.content
    ]

    assert not sop_with_inline_faq


def test_static_prompt_sections_extract_chapters_00_and_13(ru_profile) -> None:
    """
    Chapters 00 and 13 should be available for the RAG system prompt.
    """

    text = RAG_DOCUMENT.read_text(encoding="utf-8")
    sections = extract_static_prompt_sections(text, ru_profile)

    assert "00" in sections
    assert "13" in sections
    assert "Назначение" in sections["00"]
    assert "Что бот не отвечает" in sections["13"]


def test_en_chunk_count_matches_ru(en_profile, ru_profile) -> None:
    """
    English and Russian documents share structure and should produce similar chunk counts.
    """

    ru_chunks = chunk_document(
        RAG_DOCUMENT_RU.read_text(encoding="utf-8"),
        profile=ru_profile,
        source_path=str(RAG_DOCUMENT_RU),
    )
    en_chunks = chunk_document(
        RAG_DOCUMENT_EN.read_text(encoding="utf-8"),
        profile=en_profile,
        source_path=str(RAG_DOCUMENT_EN),
    )

    assert abs(len(en_chunks) - len(ru_chunks)) <= 2
    assert len(en_chunks) >= 700
    assert len(ru_chunks) >= 700


def test_en_chunks_use_english_prefix_labels(en_profile) -> None:
    """
    English profile should emit English retrieval-prefix labels.
    """

    chunks = chunk_document(
        RAG_DOCUMENT_EN.read_text(encoding="utf-8"),
        profile=en_profile,
        source_path=str(RAG_DOCUMENT_EN),
    )

    assert chunks
    assert all("[Section:" in chunk.content for chunk in chunks)
    assert all("[Type:" in chunk.content for chunk in chunks)
    assert any("**Question:**" in chunk.content for chunk in chunks if chunk.content_type == ContentType.FAQ)
