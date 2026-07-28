"""Shared mock payloads for API-layer tests."""

from datetime import UTC, datetime

from app.schemas.etl import ChunkStatsResponse, IngestAllResponse, IngestResponse, ManifestResponse

MOCK_INGEST_RESPONSE = IngestResponse(
    language_code="ru",
    chunk_count=42,
    doc_hash="deadbeef",
    embedding_model="text-embedding-test",
    source_path="/tmp/rag-document.md",
    built_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
    added=10,
    updated=2,
    unchanged=30,
    removed=0,
    embedded=12,
)

MOCK_INGEST_ALL_RESPONSE = IngestAllResponse(results=[MOCK_INGEST_RESPONSE])

MOCK_CHUNK_STATS = ChunkStatsResponse(
    language_code=None,
    total=42,
    by_content_type={"sop": 20, "faq": 12, "glossary": 10},
)

MOCK_CHUNK_STATS_RU = ChunkStatsResponse(
    language_code="ru",
    total=10,
    by_content_type={"sop": 10},
)

MOCK_MANIFEST_RESPONSE = ManifestResponse(
    language_code="ru",
    source_path="/tmp/rag-document.md",
    doc_hash="deadbeef",
    embedding_model="text-embedding-test",
    chunker_version="1.0.0",
    chunk_count=42,
    built_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
)

MOCK_MANIFEST_RESPONSE_EN = ManifestResponse(
    language_code="en",
    source_path="/tmp/rag-document-en.md",
    doc_hash="cafebabe",
    embedding_model="text-embedding-test",
    chunker_version="1.0.0",
    chunk_count=21,
    built_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
)
