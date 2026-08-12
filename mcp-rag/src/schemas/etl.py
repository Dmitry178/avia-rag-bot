"""ETL API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """
    Request body for ingesting one chunking schema file.
    """

    schema_path: str = Field(
        ...,
        description="Path to chunking schema JSON (relative to backend root or absolute)",
    )
    rebuild: bool = Field(
        default=False,
        description="Force full re-embed; when false, reuse unchanged chunks and resume from checkpoint",
    )
    source_path: str | None = Field(
        default=None,
        description="Optional markdown source path override (relative to schema directory or absolute)",
    )


class IngestAllRequest(BaseModel):
    """
    Request body for ingesting all schemas in the default data directory.
    """

    rebuild: bool = Field(
        default=False,
        description="Force full re-embed for every schema",
    )


class IngestResponse(BaseModel):
    """
    Result of a successful ingest run.
    """

    language_code: str
    chunk_count: int
    doc_hash: str
    embedding_model: str
    source_path: str
    built_at: datetime
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    embedded: int = 0


class IngestAllResponse(BaseModel):
    """
    Result of ingesting every schema in a directory.
    """

    results: list[IngestResponse]


class ChunkStatsResponse(BaseModel):
    """
    Chunk distribution by content type.
    """

    language_code: str | None = None
    total: int
    by_content_type: dict[str, int]


class ManifestResponse(BaseModel):
    """
    Latest index manifest snapshot.
    """

    language_code: str
    source_path: str
    doc_hash: str
    embedding_model: str
    chunker_version: str = ""
    chunk_count: int
    built_at: datetime
