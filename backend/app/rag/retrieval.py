"""Vector retrieval and result fusion."""

from collections import defaultdict
from pathlib import Path

from app.core.faiss_manager import faiss_manager
from app.core.rag_constants import RERANK_TOP_N, RETRIEVAL_TOP_K, RRF_K
from app.llm.embeddings import EmbeddingClient
from app.models.chunk_meta import ChunkMeta
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
