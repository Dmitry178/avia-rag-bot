"""ETL domain types."""

from dataclasses import dataclass, field
from enum import StrEnum


class ContentType(StrEnum):
    """
    Chunk content classification.
    """

    SOP = "sop"
    FAQ = "faq"
    GLOSSARY = "glossary"
    DECISION_TREE = "decision_tree"
    SCENARIO = "scenario"
    META = "meta"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass
class DocumentNode:
    """
    A node in the parsed document tree.
    """

    id: str
    section: str
    title: str
    level: int
    content_type: ContentType
    text: str
    parent_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ChunkDraft:
    """
    In-memory chunk before persistence and embedding.
    """

    content: str
    content_type: ContentType
    section: str
    title: str
    node_id: str
    parent_chunk_index: int | None = None
    token_count: int = 0
    source_path: str = ""
    content_hash: str = ""
