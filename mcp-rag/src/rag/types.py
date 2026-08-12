"""Shared RAG pipeline data types."""

from dataclasses import dataclass, field
from typing import Any

from src.models.chunk_meta import ChunkMeta
from src.rag.retrieval_lanes import RetrievalLane
from src.schemas.rag import RagConfig


@dataclass
class RagQueryContext:
    """
    Inputs for query transformation and retrieval.
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

    chunk: ChunkMeta
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
