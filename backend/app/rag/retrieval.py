"""Vector retrieval and result fusion."""

import asyncio

from collections import defaultdict
from pathlib import Path

from app.core.faiss_manager import faiss_manager
from app.core.rag_constants import RERANK_TOP_N, RETRIEVAL_TOP_K, RRF_K
from app.llm.embeddings import EmbeddingClient
from app.models.chunk_meta import ChunkMeta
from app.rag.retrieval_lanes import (
    LANE_SEARCH_MIN_FETCH,
    LANE_SEARCH_OVERSAMPLE,
    RETRIEVAL_LANES,
    RetrievalLane,
)
from app.rag.types import RetrievedChunk


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[int, float]]],
    *,
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    """
    Merge multiple ranked row-id lists with reciprocal rank fusion.
    """

    scores: dict[int, float] = defaultdict(float)

    for ranked in ranked_lists:
        for rank, (row_id, _score) in enumerate(ranked):
            scores[row_id] += 1.0 / (k + rank + 1)

    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def dedupe_retrieved_chunks(items: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """
    Keep the highest-scoring item per chunk id.
    """

    best: dict[int, RetrievedChunk] = {}

    for item in items:
        chunk_id = item.chunk.id
        if chunk_id is None:
            continue

        existing = best.get(chunk_id)
        if existing is None or item.score > existing.score:
            best[chunk_id] = item

    return sorted(best.values(), key=lambda item: item.score, reverse=True)


class VectorRetriever:
    """
    Embed queries and search the persisted FAISS index.
    """

    def __init__(
        self,
        *,
        index_path: Path,
        embedder: EmbeddingClient,
        chunks_by_id: dict[int, ChunkMeta],
    ) -> None:
        self._index_path = index_path
        self._embedder = embedder
        self._chunks_by_id = chunks_by_id

    def _fetch_k_for_lane(self, top_k: int) -> int:
        return min(
            len(self._chunks_by_id),
            max(top_k * LANE_SEARCH_OVERSAMPLE, LANE_SEARCH_MIN_FETCH),
        )

    async def _search_query_filtered(
        self,
        query: str,
        *,
        content_types: frozenset[str],
        top_k: int,
        lane: str,
        fetch_k: int | None = None,
    ) -> list[RetrievedChunk]:
        vectors = await self._embedder.embed_texts([query])
        if not vectors:
            return []

        resolved_fetch_k = fetch_k if fetch_k is not None else self._fetch_k_for_lane(top_k)
        row_ids, scores = await faiss_manager.search_async(
            self._index_path,
            vectors[0],
            resolved_fetch_k,
        )
        results: list[RetrievedChunk] = []

        for row_id, score in zip(row_ids, scores, strict=True):
            chunk = self._chunks_by_id.get(row_id)
            if chunk is None or chunk.content_type not in content_types:
                continue

            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=score,
                    source_query=query,
                    vector_similarity=score,
                    retrieval_lane=lane,
                ),
            )
            if len(results) >= top_k:
                break

        return results

    async def search_query(self, query: str, *, top_k: int = RETRIEVAL_TOP_K) -> list[RetrievedChunk]:
        vectors = await self._embedder.embed_texts([query])
        if not vectors:
            return []

        row_ids, scores = await faiss_manager.search_async(self._index_path, vectors[0], top_k)
        results: list[RetrievedChunk] = []

        for row_id, score in zip(row_ids, scores, strict=True):
            chunk = self._chunks_by_id.get(row_id)
            if chunk is None:
                continue
            results.append(RetrievedChunk(chunk=chunk, score=score, source_query=query))

        return results

    async def search_lane(
        self,
        queries: list[str],
        *,
        lane: RetrievalLane,
    ) -> list[RetrievedChunk]:
        """
        Search one retrieval lane, applying RRF when multiple queries are provided.
        """

        if not queries:
            return []

        if len(queries) == 1:
            return await self._search_query_filtered(
                queries[0],
                content_types=lane.content_types,
                top_k=lane.top_k,
                lane=lane.id,
            )

        ranked_lists: list[list[tuple[int, float]]] = []
        chunk_lookup: dict[int, RetrievedChunk] = {}
        max_similarity: dict[int, float] = {}

        for query in queries:
            items = await self._search_query_filtered(
                query,
                content_types=lane.content_types,
                top_k=lane.top_k,
                lane=lane.id,
            )
            ranked_lists.append(
                [(item.chunk.id or 0, item.score) for item in items if item.chunk.id is not None],
            )

            for item in items:
                chunk_id = item.chunk.id
                if chunk_id is None:
                    continue

                chunk_lookup[chunk_id] = item
                max_similarity[chunk_id] = max(max_similarity.get(chunk_id, float("-inf")), item.score)

        fused = reciprocal_rank_fusion(ranked_lists)
        merged: list[RetrievedChunk] = []

        for row_id, fused_score in fused:
            item = chunk_lookup.get(row_id)
            if item is None:
                continue

            merged.append(
                RetrievedChunk(
                    chunk=item.chunk,
                    score=fused_score,
                    source_query=item.source_query,
                    vector_similarity=max_similarity.get(row_id),
                    retrieval_lane=lane.id,
                ),
            )

            if len(merged) >= lane.top_k:
                break

        return merged

    async def search_lanes(self, queries: list[str]) -> dict[str, list[RetrievedChunk]]:
        """
        Run all configured retrieval lanes in parallel.
        """

        async def run_lane(lane: RetrievalLane) -> tuple[str, list[RetrievedChunk]]:
            hits = await self.search_lane(queries, lane=lane)
            return lane.id, hits

        results = await asyncio.gather(*(run_lane(lane) for lane in RETRIEVAL_LANES))

        return dict(results)

    async def search_many(self, queries: list[str], *, top_k: int = RETRIEVAL_TOP_K) -> list[RetrievedChunk]:
        if not queries:
            return []

        if len(queries) == 1:
            return await self.search_query(queries[0], top_k=top_k)

        ranked_lists: list[list[tuple[int, float]]] = []
        chunk_lookup: dict[int, RetrievedChunk] = {}
        max_similarity: dict[int, float] = {}

        for query in queries:
            items = await self.search_query(query, top_k=top_k)
            ranked_lists.append(
                [(item.chunk.id or 0, item.score) for item in items if item.chunk.id is not None],
            )
            for item in items:
                chunk_id = item.chunk.id
                if chunk_id is None:
                    continue

                chunk_lookup[chunk_id] = item
                max_similarity[chunk_id] = max(max_similarity.get(chunk_id, float("-inf")), item.score)

        fused = reciprocal_rank_fusion(ranked_lists)
        merged: list[RetrievedChunk] = []

        for row_id, fused_score in fused:
            item = chunk_lookup.get(row_id)
            if item is None:
                continue

            merged.append(
                RetrievedChunk(
                    chunk=item.chunk,
                    score=fused_score,
                    source_query=item.source_query,
                    vector_similarity=max_similarity.get(row_id),
                ),
            )
            if len(merged) >= top_k:
                break

        return merged

    @staticmethod
    def trim_candidates(candidates: list[RetrievedChunk], *, top_n: int = RERANK_TOP_N) -> list[RetrievedChunk]:
        if len(candidates) <= top_n:
            return candidates

        return candidates[:top_n]
