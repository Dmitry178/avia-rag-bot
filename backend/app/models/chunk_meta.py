"""Chunk metadata stored in SQLite."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class ChunkMeta(SQLModel, table=True):
    """
    Text chunk with metadata; primary key matches FAISS row index.
    """

    __tablename__ = "chunk_meta"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="Chunk row id; equals the vector position in FAISS index (0..N-1).",
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
    parent_id: int | None = Field(
        default=None,
        foreign_key="chunk_meta.id",
        description="Parent chunk id when an SOP section was split by ### subheadings; null otherwise.",
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
