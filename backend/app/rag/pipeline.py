"""RAG retrieval orchestration."""

import time

from pathlib import Path

from app.core.config import Settings
from app.core.db_manager import DBManager
from app.exceptions.service import ServiceError
from app.llm.chat import ChatCompletionClient
from app.llm.embeddings import EmbeddingClient
from app.llm.kb_static_context import load_kb_static_context
from app.models.chunk_meta import ChunkMeta
from app.rag.generation import build_context_block, build_rag_system_prompt
from app.rag.methods.registry import resolve_query_transform_method, resolve_rerank_method
from app.rag.retrieval import VectorRetriever, dedupe_retrieved_chunks
from app.rag.retrieval_lanes import LANE_BY_ID, RETRIEVAL_LANES
from app.rag.types import RagPipelineResult, RagQueryContext, RagTraceStep, RetrievedChunk
from app.schemas.rag import RagConfig


class RagPipeline:
    """
    Run query transformation, vector retrieval, optional rerank, and context assembly.
    """

    def __init__(self, db: DBManager, app_settings: Settings) -> None:
        self._db = db
        self._settings = app_settings
        self._llm = ChatCompletionClient(app_settings.llm)
        self._embedder = EmbeddingClient(app_settings.llm)

    def _index_path(self) -> Path:
        return self._settings.faiss.index_path(self._settings.backend_root)

    async def _load_chunks(self) -> dict[int, ChunkMeta]:
        chunks = await self._db.etl.chunks.list_all_ordered()
        return {chunk.id: chunk for chunk in chunks if chunk.id is not None}

    @staticmethod
    def _chunk_similarity(item: RetrievedChunk) -> float:
        if item.vector_similarity is not None:
            return item.vector_similarity

        return item.score

    @staticmethod
    def _serialize_trace_hit(item: RetrievedChunk) -> dict:
        chunk_id = item.chunk.id
        if chunk_id is None:
            return {}

        lane = item.retrieval_lane or item.chunk.content_type
        lane_meta = LANE_BY_ID.get(lane)

        return {
            "id": chunk_id,
            "title": item.chunk.title or "",
            "section": item.chunk.section or "",
            "content_type": item.chunk.content_type,
            "lane": lane,
            "lane_source": lane_meta.source_label if lane_meta is not None else "",
            "similarity": round(RagPipeline._chunk_similarity(item), 4),
            "content_preview": item.chunk.content[:600],
        }

    @classmethod
    def _serialize_trace_hits(cls, items: list[RetrievedChunk]) -> list[dict]:
        return [hit for item in items if (hit := cls._serialize_trace_hit(item))]

    @staticmethod
    def _serialize_lane_results(lane_results: dict[str, list[RetrievedChunk]]) -> list[dict]:
        lanes: list[dict] = []

        for lane in RETRIEVAL_LANES:
            hits = lane_results.get(lane.id, [])
            lanes.append(
                {
                    "lane": lane.id,
                    "source_label": lane.source_label,
                    "top_k": lane.top_k,
                    "hit_count": len(hits),
                    "hits": RagPipeline._serialize_trace_hits(hits),
                },
            )

        return lanes

    @staticmethod
    def _serialize_rag_config(rag_config: RagConfig) -> dict:
        return {
            "use_hyde": bool(rag_config.use_hyde),
            "use_multi_query": bool(rag_config.use_multi_query),
            "use_query_rewriting": bool(rag_config.use_query_rewriting),
            "use_rerank": bool(rag_config.use_rerank),
            "top_chunks": rag_config.top_chunks,
        }

    @staticmethod
    def _normalized_config(rag_config: RagConfig | None) -> RagConfig:
        if rag_config is None:
            return RagConfig()

        return RagConfig(
            use_hyde=bool(rag_config.use_hyde),
            use_multi_query=bool(rag_config.use_multi_query),
            use_query_rewriting=bool(rag_config.use_query_rewriting),
            use_rerank=bool(rag_config.use_rerank),
            top_chunks=rag_config.top_chunks,
        )

    async def run(self, ctx: RagQueryContext) -> RagPipelineResult:
        """
        Execute the configured RAG retrieval pipeline.
        """

        trace: list[RagTraceStep] = []
        rag_config = self._normalized_config(ctx.rag_config)
        top_chunks = rag_config.top_chunks
        index_path = self._index_path()

        trace.append(
            RagTraceStep(
                step="rag_config",
                duration_ms=0,
                data=RagPipeline._serialize_rag_config(rag_config),
            ),
        )

        if not index_path.is_file():
            raise ServiceError(
                detail="Knowledge base index has not been built yet",
                error_code="rag_index_missing",
                status_code=503,
            )

        chunks_by_id = await self._load_chunks()
        if not chunks_by_id:
            raise ServiceError(
                detail=(
                    "Knowledge base chunks are missing in the database. "
                    "Run `make etl-ingest` to rebuild SQLite metadata and FAISS index."
                ),
                error_code="rag_chunks_missing",
                status_code=503,
            )

        retriever = VectorRetriever(
            index_path=index_path,
            embedder=self._embedder,
            chunks_by_id=chunks_by_id,
        )

        transform = resolve_query_transform_method(rag_config, self._llm)

        started = time.perf_counter()

        if transform is None:
            search_queries = [ctx.query]
        else:
            search_queries = await transform.build_search_queries(ctx)
            trace.append(
                RagTraceStep(
                    step=transform.name,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    data={"queries": search_queries},
                ),
            )

        retrieval_started = time.perf_counter()
        lane_results = await retriever.search_lanes(search_queries)
        lane_hits = [hit for hits in lane_results.values() for hit in hits]
        candidates = dedupe_retrieved_chunks(lane_hits)

        trace.append(
            RagTraceStep(
                step="retrieval",
                duration_ms=int((time.perf_counter() - retrieval_started) * 1000),
                data={
                    "query_count": len(search_queries),
                    "candidate_count": len(candidates),
                    "lanes": RagPipeline._serialize_lane_results(lane_results),
                    "hits": RagPipeline._serialize_trace_hits(candidates),
                },
            ),
        )

        reranker = resolve_rerank_method(rag_config, self._llm)

        if reranker is not None and candidates:
            rerank_started = time.perf_counter()
            final_chunks = await reranker.rerank(ctx.query, candidates, top_n=top_chunks)
            trace.append(
                RagTraceStep(
                    step="rerank",
                    duration_ms=int((time.perf_counter() - rerank_started) * 1000),
                    data={
                        "hits": RagPipeline._serialize_trace_hits(final_chunks),
                    },
                ),
            )
        else:
            final_chunks = VectorRetriever.trim_candidates(candidates, top_n=top_chunks)

        context = build_context_block(final_chunks)

        return RagPipelineResult(
            context=context,
            chunks=final_chunks,
            trace=trace,
            search_queries=search_queries,
        )

    def build_generation_prompt(self, *, context: str, reply_language: str | None) -> str:
        """
        Build the grounded system prompt for the final LLM call.
        """

        document_path = self._settings.etl.resolve_document_path(self._settings.backend_root)
        kb_static_context = load_kb_static_context(str(document_path))

        return build_rag_system_prompt(
            context=context,
            reply_language=reply_language,
            kb_static_context=kb_static_context,
        )
