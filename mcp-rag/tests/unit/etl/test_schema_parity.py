"""Schema-driven baseline parity checks for RU/EN KB documents."""

import pytest

from pathlib import Path

from src.etl.chunking_schema import load_runtime_schema_for_language
from src.etl.universal_chunker import UniversalChunker

from tests.paths import KB_ROOT, RAG_DOCUMENT_EN, RAG_DOCUMENT_RU


def _chunk_hashes(path: Path, *, language_code: str) -> list[str]:
    schema = load_runtime_schema_for_language(language_code, str(KB_ROOT)).schema
    chunker = UniversalChunker(schema)
    text = path.read_text(encoding="utf-8")
    return [chunk.content_hash for chunk in chunker.chunk_document(text, source_path=str(path))]


@pytest.mark.parametrize(
    ("language_code", "document_path", "expected_count"),
    [
        ("ru", RAG_DOCUMENT_RU, 719),
        ("en", RAG_DOCUMENT_EN, 720),
    ],
)
def test_schema_baseline_chunk_count_and_hash_stability(
    language_code: str,
    document_path: Path,
    expected_count: int,
) -> None:
    """
    Schema-driven chunker should keep baseline chunking stable for shipped KB documents.
    """

    schema_hashes = _chunk_hashes(document_path, language_code=language_code)

    assert len(schema_hashes) == expected_count
    assert len(set(schema_hashes)) == expected_count
