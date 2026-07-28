"""Chunk metadata stored in SQLite."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class ChunkMeta(SQLModel, table=True):
    """
    Text chunk with metadata; primary key (language_code, id) matches FAISS row index per language.
    """

    __tablename__ = "chunk_meta"

    language_code: str = Field(
        primary_key=True,
        max_length=16,
        description="Knowledge-base language this chunk belongs to (ru or en).",
    )
    id: int = Field(
        primary_key=True,
        description="Chunk row id within the language; equals the vector position in that language's FAISS index.",
    )
    content: str = Field(
        description="Full chunk text with retrieval prefix ([Раздел:], [Тип:]) for embedding and LLM context.",
    )
    content_type: str = Field(
        description="Chunk category: sop, faq, glossary, decision_tree, scenario, meta, or out_of_scope.",
    )
    section: str = Field(
        description="Top-level document section (H1 title), e.g. '04. Багаж'.",
    )
    title: str = Field(
        description="Chunk heading: SOP subsection, FAQ question, glossary term, scenario name, etc.",
    )
    node_id: str = Field(
        default="",
        description="Stable id of the source node in the parsed document tree.",
    )
    content_hash: str = Field(
        default="",
        description="SHA-256 hex digest of content; used for incremental re-indexing.",
    )
    parent_id: int | None = Field(
        default=None,
        description="Parent chunk id (same language_code) when an SOP section was split by ### subheadings.",
    )
    token_count: int = Field(
        default=0,
        description="Approximate token count (len(content) // 4) at ingest time.",
    )
    source_path: str = Field(
        default="",
        description="Absolute or resolved path to the markdown file this chunk was ingested from.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the chunk was written during ingest.",
    )
