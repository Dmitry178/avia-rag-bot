"""ETL API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """
    Request body for document ingestion.
    """

    rebuild: bool = Field(default=True, description="Replace existing index and chunks")
    source_path: str | None = Field(
        default=None,
        description="Override path to markdown source; defaults to ETL__DOCUMENT_PATH",
    )


class IngestResponse(BaseModel):
    """
    Result of a successful ingest run.
    """

    chunk_count: int
    doc_hash: str
    embedding_model: str
    source_path: str
    built_at: datetime


class ChunkStatsResponse(BaseModel):
    """
    Chunk distribution by content type.
    """

    total: int
    by_content_type: dict[str, int]


class ManifestResponse(BaseModel):
    """
    Latest index manifest snapshot.
    """

    source_path: str
    doc_hash: str
    embedding_model: str
    chunk_count: int
    built_at: datetime
