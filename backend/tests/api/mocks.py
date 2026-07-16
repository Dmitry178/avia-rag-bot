"""Shared mock payloads for API-layer tests."""

from datetime import UTC, datetime

from app.schemas.etl import ChunkStatsResponse, IngestResponse, ManifestResponse

MOCK_INGEST_RESPONSE = IngestResponse(
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

MOCK_CHUNK_STATS = ChunkStatsResponse(
    total=42,
    by_content_type={"sop": 20, "faq": 12, "glossary": 10},
)

MOCK_MANIFEST_RESPONSE = ManifestResponse(
    source_path="/tmp/rag-document.md",
    doc_hash="deadbeef",
    embedding_model="text-embedding-test",
    chunker_version="1.0.0",
    chunk_count=42,
    built_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
)
