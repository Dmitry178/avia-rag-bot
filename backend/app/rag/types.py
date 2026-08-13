"""Shared RAG pipeline data types (no mcp-rag / ``src`` imports)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.schemas.rag import RagConfig


@dataclass
class ChunkRecord:
    """
    Knowledge-base chunk row used for retrieval metadata and trace enrichment.
    """

    language_code: str
    id: int | None
    content: str
    content_type: str
    section: str
    title: str
    node_id: str = ""
    content_hash: str = ""
    parent_id: int | None = None
    token_count: int = 0
    source_path: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class LanePresentation:
    """
    Runtime presentation and verification settings for one retrieval lane.
    """

    ui_priority: int = 0
    ui_variant: str | None = None
    exclude_from_generation_context: bool = False
    verification_strategy: str = "none"
    verification_no_match_token: str | None = None
    max_verification_candidates: int = 1


@dataclass(frozen=True)
class RetrievalLane:
    """
    One retrieval corpus with its own top-k quota and similarity threshold.
    """

    id: str
    content_types: frozenset[str]
    top_k: int
    label: str
    description: str = ""
    oversample: int = 10
    min_fetch: int = 80
    min_similarity: float = 0.4
    presentation: LanePresentation = LanePresentation()


@dataclass(frozen=True)
class RetrievalRuntime:
    """
    Per-language retrieval runtime (lane metadata for serialization and verification).
    """

    lanes: tuple[RetrievalLane, ...]
    lane_by_id: dict[str, RetrievalLane]


@dataclass
class RagQueryContext:
    """
    Inputs for query transformation and retrieval (backend ``RagConfig`` includes runtime fields).
    """

    query: str
    history: list[dict[str, str]]
    rag_config: RagConfig
    reply_language: str
    language_code: str


@dataclass
class RetrievedChunk:
    """
    A knowledge-base chunk with retrieval score.
    """

    chunk: ChunkRecord
    score: float
    source_query: str | None = None
    vector_similarity: float | None = None
    retrieval_lane: str | None = None


def chunk_similarity(item: RetrievedChunk) -> float:
    """
    Return the best available similarity score for a retrieved chunk.
    """

    if item.vector_similarity is not None:
        return item.vector_similarity

    return item.score


@dataclass(frozen=True)
class LaneVerificationCandidate:
    """
    One lane hit selected for optional dedicated LLM verification.
    """

    lane: RetrievalLane
    hit: RetrievedChunk


@dataclass
class RagTraceStep:
    """
    Single trace step for UI / message metadata.
    """

    step: str
    duration_ms: int
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RagPipelineResult:
    """
    Output of the retrieval stage before LLM generation.
    """

    context: str
    chunks: list[RetrievedChunk]
    trace: list[RagTraceStep]
    search_queries: list[str] = field(default_factory=list)
    verification_candidates: list[LaneVerificationCandidate] = field(default_factory=list)
    applicable_decision_trees: list[RetrievedChunk] = field(default_factory=list)


__all__ = [
    "ChunkRecord",
    "LanePresentation",
    "LaneVerificationCandidate",
    "RagPipelineResult",
    "RagQueryContext",
    "RagTraceStep",
    "RetrievalLane",
    "RetrievalRuntime",
    "RetrievedChunk",
    "chunk_similarity",
]
