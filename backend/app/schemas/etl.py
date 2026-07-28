"""ETL API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """
    Request body for document ingestion.
    """

    rebuild: bool = Field(
        default=False,
        description="Force full re-embed; when false, reuse unchanged chunks and resume from checkpoint",
    )
    language_code: str | None = Field(
        default=None,
        description="Target KB language code (e.g. ru, en); required unless source_path implies a language",
    )
    source_path: str | None = Field(
        default=None,
        description="Override path to markdown source; defaults to the language document in app/core/config.py",
    )


class IngestAllRequest(BaseModel):
    """
    Request body for ingesting all active knowledge-base languages.
    """

    rebuild: bool = Field(
        default=False,
        description="Force full re-embed for every language",
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
    Result of ingesting all active languages.
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
