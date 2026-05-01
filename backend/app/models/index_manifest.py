"""Index build manifest stored in SQLite."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class IndexManifest(SQLModel, table=True):
    """
    Metadata about a single vector index build (one row per ingest run).
    """

    __tablename__ = "index_manifest"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="Surrogate primary key for the manifest row.",
    )
    source_path: str = Field(
        description="Resolved path to the markdown file that was ingested.",
    )
    doc_hash: str = Field(
        description="SHA-256 hex digest of the source file at ingest time; used to detect document changes.",
    )
    embedding_model: str = Field(
        description="LLM embedding model name (LLM__EMBEDDING_MODEL) used to build the index.",
    )
    chunk_count: int = Field(
        description="Number of chunks written to chunk_meta and FAISS in this build.",
    )
    built_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the index build completed.",
    )
