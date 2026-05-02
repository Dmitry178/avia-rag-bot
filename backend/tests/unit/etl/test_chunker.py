"""ETL parser and chunker unit tests."""

from etl.chunker import chunk_document
from etl.parser import parse_markdown
from etl.types import ContentType

from tests.paths import RAG_DOCUMENT


def test_parse_markdown_finds_all_main_sections() -> None:
    """
    Parser should extract intro, FAQ, and glossary sections from the RAG document.
    """

    text = RAG_DOCUMENT.read_text(encoding="utf-8")
    nodes = parse_markdown(text, source_path=str(RAG_DOCUMENT))
    sections = {node.section for node in nodes if node.level == 1 or node.level == 2}

    assert any("00." in section for section in sections)
    assert any("14." in section or "FAQ" in section for section in sections)
    assert any("15." in section or "Глоссарий" in section for section in sections)


def test_chunk_document_produces_expected_types() -> None:
    """
    Chunker should emit all major content types with a reasonable chunk count.
    """

    text = RAG_DOCUMENT.read_text(encoding="utf-8")
    chunks = chunk_document(text, source_path=str(RAG_DOCUMENT))
    types = {chunk.content_type for chunk in chunks}

    assert ContentType.SOP in types
    assert ContentType.FAQ in types
    assert ContentType.GLOSSARY in types
    assert ContentType.DECISION_TREE in types
    assert ContentType.SCENARIO in types
    assert len(chunks) >= 200


def test_chunks_have_retrieval_prefix() -> None:
    """
    Every chunk should include section and content-type retrieval prefixes.
    """

    text = RAG_DOCUMENT.read_text(encoding="utf-8")
    chunks = chunk_document(text, source_path=str(RAG_DOCUMENT))

    assert all("[Раздел:" in chunk.content for chunk in chunks)
    assert all("[Тип:" in chunk.content for chunk in chunks)
