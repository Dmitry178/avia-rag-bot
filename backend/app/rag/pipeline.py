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
from app.rag.lane_post_processing import (
    apply_lane_similarity_filters,
    select_verification_candidates,
)
from app.rag.methods.registry import resolve_query_transform_method, resolve_rerank_method
from app.rag.retrieval import VectorRetriever, dedupe_retrieved_chunks
from app.rag.retrieval_lanes import get_retrieval_runtime
from app.rag.types import RagPipelineResult, RagQueryContext, RagTraceStep, RetrievedChunk
from app.schemas.rag import RagConfig
from etl.chunking_schema import load_runtime_schema_for_language, resolve_schema_output_root


class RagPipeline:
    """
    Run query transformation, vector retrieval, optional rerank, and context assembly.
    """

    def __init__(self, db: DBManager, app_settings: Settings) -> None:
        self._db = db
        self._settings = app_settings
        self._llm = ChatCompletionClient(app_settings.llm)
        self._embedder = EmbeddingClient(app_settings.llm)

    def _index_path(self, language_code: str) -> Path:
        context = load_runtime_schema_for_language(language_code, str(self._settings.backend_root))
        output_root = resolve_schema_output_root(
            context.schema,
            schema_dir=context.schema_dir,
            backend_root=self._settings.backend_root,
            repo_root=self._settings.repo_root,
            output_root_override=None,
        )
        return (output_root / context.schema.io.faiss_index_path).resolve()

    async def _load_chunks(self, language_code: str) -> dict[int, ChunkMeta]:
        chunks = await self._db.etl.chunks.list_all_ordered(language_code)
        return {chunk.id: chunk for chunk in chunks if chunk.id is not None}

    @staticmethod
    def _chunk_similarity(item: RetrievedChunk) -> float:
        if item.vector_similarity is not None:
            return item.vector_similarity

        return item.score

    @staticmethod
    def _serialize_trace_hit(item: RetrievedChunk, lane_by_id: dict[str, object]) -> dict:
        chunk_id = item.chunk.id
        if chunk_id is None:
            return {}

        lane = item.retrieval_lane or item.chunk.content_type
        lane_meta = lane_by_id.get(lane)
        lane_label = getattr(lane_meta, "label", "") if lane_meta is not None else ""
        lane_description = getattr(lane_meta, "description", "") if lane_meta is not None else ""

        return {
            "id": chunk_id,
            "title": item.chunk.title or "",
            "section": item.chunk.section or "",
            "content_type": item.chunk.content_type,
            "lane": lane,
            "lane_label": lane_label,
            "lane_description": lane_description,
            "lane_source": lane_description,
            "similarity": round(RagPipeline._chunk_similarity(item), 4),
            "content_preview": item.chunk.content[:600],
        }

    @classmethod
    def _serialize_trace_hits(cls, items: list[RetrievedChunk], lane_by_id: dict[str, object]) -> list[dict]:
        return [hit for item in items if (hit := cls._serialize_trace_hit(item, lane_by_id))]

    @staticmethod
    def _serialize_lane_results(
        lane_results: dict[str, list[RetrievedChunk]],
        *,
        lanes: tuple[object, ...],
        lane_by_id: dict[str, object],
    ) -> list[dict]:
        serialized: list[dict] = []

        for lane in lanes:
            hits = lane_results.get(getattr(lane, "id"), [])
            serialized.append(
                {
                    "lane": getattr(lane, "id"),
                    "label": getattr(lane, "label", ""),
                    "description": getattr(lane, "description", ""),
                    "source_label": getattr(lane, "label", ""),
                    "top_k": getattr(lane, "top_k"),
                    "hit_count": len(hits),
                    "hits": RagPipeline._serialize_trace_hits(hits, lane_by_id),
                },
            )

        return serialized

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
        language_code = ctx.language_code
        index_path = self._index_path(language_code)
        retrieval_runtime = get_retrieval_runtime(language_code)

        trace.append(
            RagTraceStep(
                step="rag_config",
                duration_ms=0,
                data=RagPipeline._serialize_rag_config(rag_config),
            ),
        )

        if not index_path.is_file():
            raise ServiceError(
                detail=f"Knowledge base index has not been built yet for language: {language_code}",
                error_code="rag_index_missing",
                status_code=503,
            )

        chunks_by_id = await self._load_chunks(language_code)
        if not chunks_by_id:
            raise ServiceError(
                detail=(
                    f"Knowledge base chunks are missing for language {language_code}. "
                    "Run `make etl-ingest` to rebuild SQLite metadata and FAISS indexes."
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
        raw_lane_results = await retriever.search_lanes(search_queries, lanes=retrieval_runtime.lanes)
        lane_results = apply_lane_similarity_filters(raw_lane_results, runtime=retrieval_runtime)
        verification_candidates = select_verification_candidates(lane_results, runtime=retrieval_runtime)
        applicable_decision_trees = [
            candidate.hit
            for candidate in verification_candidates
            if candidate.lane.presentation.ui_variant == "decision_tree"
        ]
        lane_hits = [hit for hits in lane_results.values() for hit in hits]
        candidates = dedupe_retrieved_chunks(lane_hits)

        trace.append(
            RagTraceStep(
                step="retrieval",
                duration_ms=int((time.perf_counter() - retrieval_started) * 1000),
                data={
                    "query_count": len(search_queries),
                    "candidate_count": len(candidates),
                    "lanes": RagPipeline._serialize_lane_results(
                        lane_results,
                        lanes=retrieval_runtime.lanes,
                        lane_by_id=retrieval_runtime.lane_by_id,
                    ),
                    "hits": RagPipeline._serialize_trace_hits(candidates, retrieval_runtime.lane_by_id),
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
                        "hits": RagPipeline._serialize_trace_hits(final_chunks, retrieval_runtime.lane_by_id),
                    },
                ),
            )
        else:
            final_chunks = VectorRetriever.trim_candidates(candidates, top_n=top_chunks)

        context = build_context_block(final_chunks)

        if verification_candidates:
            trace.append(
                RagTraceStep(
                    step="lane_verification",
                    duration_ms=0,
                    data={
                        "candidate_count": len(verification_candidates),
                        "lanes": [
                            {
                                "lane": candidate.lane.id,
                                "ui_variant": candidate.lane.presentation.ui_variant,
                                "hits": RagPipeline._serialize_trace_hits(
                                    [candidate.hit],
                                    retrieval_runtime.lane_by_id,
                                ),
                            }
                            for candidate in verification_candidates
                        ],
                    },
                ),
            )

        if applicable_decision_trees:
            trace.append(
                RagTraceStep(
                    step="decision_tree",
                    duration_ms=0,
                    data={
                        "applicable_count": len(applicable_decision_trees),
                        "hits": RagPipeline._serialize_trace_hits(
                            applicable_decision_trees,
                            retrieval_runtime.lane_by_id,
                        ),
                    },
                ),
            )

        return RagPipelineResult(
            context=context,
            chunks=final_chunks,
            trace=trace,
            search_queries=search_queries,
            verification_candidates=verification_candidates,
            applicable_decision_trees=applicable_decision_trees,
        )

    @staticmethod
    def build_generation_prompt(
        *,
        context: str,
        reply_language: str | None,
        language_code: str,
    ) -> str:
        """
        Build the grounded system prompt for the final LLM call.
        """

        kb_static_context = load_kb_static_context("", language_code=language_code)

        return build_rag_system_prompt(
            context=context,
            reply_language=reply_language,
            kb_static_context=kb_static_context,
        )
