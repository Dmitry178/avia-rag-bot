"""ETL domain types."""

from dataclasses import dataclass


@dataclass
class ChunkDraft:
    """
    In-memory chunk before persistence and embedding.
    """

    content: str
    content_type: str
    section: str
    title: str
    node_id: str
    parent_chunk_index: int | None = None
    token_count: int = 0
    source_path: str = ""
    content_hash: str = ""
