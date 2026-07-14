"""Chat use cases: CRUD, messaging, and RAG/LLM replies."""

import time

from datetime import UTC, datetime

from app.core.chat_constants import is_default_chat_title
from app.core.config import Settings, settings
from app.core.db_manager import DBManager
from app.core.logs import logger
from app.core.rag_constants import DEFAULT_TOP_CHUNKS
from app.core.sse_manager import sse_manager
from app.exceptions import handle_basic_db_errors
from app.exceptions.service import ServiceError
from app.llm.chat import ChatCompletionClient
from app.llm.prompts import build_system_prompt
from app.llm.prompt_guard import (
    BlockReason,
    blocked_refusal,
    evaluate_user_message,
    reply_language_for_user_text,
)
from app.models.chat import ChatType
from app.models.chat_message import MessageRole
from app.models.chunk_meta import ChunkMeta
from app.schemas.chat import (
    ChatDetailResponse,
    ChatMessageResponse,
    ChatSummaryResponse,
    CreateChatRequest,
    EditMessageRequest,
    SendMessageRequest,
    SendMessageResponse,
    SetRatingRequest,
    UpdateChatRequest,
)
from app.schemas.llm import LlmConfig
from app.schemas.rag import RagConfig
from app.rag.decision_tree import exclude_decision_tree_chunks, generate_decision_tree_guidance
from app.rag.generation import build_context_block
from app.rag.pipeline import RagPipeline
from app.rag.types import RagQueryContext, RagTraceStep
from app.services.chat_title import schedule_chat_title_generation


class ChatService:
    """
    Orchestrates chat list, history, RAG retrieval, and synchronous LLM replies.
    """

    def __init__(self, db: DBManager, app_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = app_settings or settings

    @staticmethod
    def _parse_rag_config(data: dict | None) -> RagConfig | None:
        if not data:
            return None

        return RagConfig.model_validate(data)

    @staticmethod
    def _parse_llm_config(data: dict | None) -> LlmConfig | None:
        if not data:
            return None

        return LlmConfig.model_validate(data)

    @staticmethod
    def _resolve_use_history(body: SendMessageRequest, chat) -> bool:
        if "use_history" in body.model_fields_set:
            value = body.use_history
        else:
            value = chat.use_history

        return True if value is None else value

    @staticmethod
    def _settings_message_metadata(
        rag_config: RagConfig | None,
        llm_config: LlmConfig | None,
        use_history: bool,
    ) -> dict:
        metadata: dict = {"use_history": use_history}

        if rag_config is not None:
            metadata["rag_config"] = rag_config.model_dump()

        if llm_config is not None:
            metadata["llm_config"] = llm_config.model_dump()

        return metadata

    @staticmethod
    def _build_llm_messages(history, current_content: str, use_history: bool) -> list[dict[str, str]]:
        if use_history:
            return [
                {"role": message.role, "content": message.content}
                for message in history
                if message.role in {MessageRole.USER.value, MessageRole.ASSISTANT.value}
            ]

        return [{"role": MessageRole.USER.value, "content": current_content}]

    @staticmethod
    def _rag_history_messages(history, *, use_history: bool) -> list[dict[str, str]]:
        if not use_history or len(history) <= 1:
            return []

        return [
            {"role": message.role, "content": message.content}
            for message in history[:-1]
            if message.role in {MessageRole.USER.value, MessageRole.ASSISTANT.value}
        ]

    @staticmethod
    def _serialize_rag_trace(trace: list[RagTraceStep]) -> list[dict]:
        requested_at = datetime.now(UTC).isoformat()

        return [
            {
                "step": step.step,
                "timestamp": requested_at,
                "duration_ms": step.duration_ms,
                "data": step.data,
            }
            for step in trace
        ]

    @staticmethod
    async def _publish_rag_trace(client_id: str | None, trace: list[RagTraceStep]) -> None:
        if not client_id:
            return

        for step in trace:
            await sse_manager.publish(
                client_id,
                "trace",
                {
                    "step": step.step,
                    "duration_ms": step.duration_ms,
                    "data": step.data,
                },
            )

    @staticmethod
    def _chunk_similarity(item) -> float:
        vector_similarity = getattr(item, "vector_similarity", None)

        if vector_similarity is not None:
            return vector_similarity

        return item.score

    @staticmethod
    def _serialize_retrieved_chunks(chunks) -> list[dict]:
        serialized: list[dict] = []

        for citation_index, item in enumerate(chunks, start=1):
            chunk = item.chunk
            if chunk.id is None:
                continue

            similarity = round(ChatService._chunk_similarity(item), 4)

            serialized.append(
                {
                    "citation_index": citation_index,
                    "id": chunk.id,
                    "section": chunk.section,
                    "title": chunk.title,
                    "content_type": chunk.content_type,
                    "retrieval_lane": item.retrieval_lane or chunk.content_type,
                    "score": similarity,
                    "similarity": similarity,
                    "source_query": item.source_query,
                    "token_count": chunk.token_count,
                    "node_id": chunk.node_id,
                    "content_preview": chunk.content[:600],
                },
            )

        return serialized

    @staticmethod
    def _serialize_chunk_meta(
        chunk: ChunkMeta,
        *,
        citation_index: int,
        score: float | None = None,
        similarity: float | None = None,
    ) -> dict:
        resolved_similarity = similarity if similarity is not None else score

        return {
            "citation_index": citation_index,
            "id": chunk.id,
            "section": chunk.section,
            "title": chunk.title,
            "content_type": chunk.content_type,
            "retrieval_lane": chunk.content_type,
            "score": round(resolved_similarity, 4) if resolved_similarity is not None else None,
            "similarity": round(resolved_similarity, 4) if resolved_similarity is not None else None,
            "source_query": None,
            "token_count": chunk.token_count,
            "node_id": chunk.node_id,
            "content_preview": chunk.content[:600],
        }

    @staticmethod
    def _similarity_scores_from_trace(metadata: dict) -> dict[int, float]:
        scores: dict[int, float] = {}

        for step in metadata.get("rag_trace") or []:
            if not isinstance(step, dict):
                continue

            if step.get("step") not in {"retrieval", "rerank"}:
                continue

            data = step.get("data")
            if not isinstance(data, dict):
                continue

            for hit in data.get("hits") or []:
                if not isinstance(hit, dict):
                    continue

                chunk_id = hit.get("id")
                similarity = hit.get("similarity")
                if isinstance(chunk_id, int) and isinstance(similarity, (int, float)):
                    scores[chunk_id] = float(similarity)

            for lane in data.get("lanes") or []:
                if not isinstance(lane, dict):
                    continue

                for hit in lane.get("hits") or []:
                    if not isinstance(hit, dict):
                        continue

                    chunk_id = hit.get("id")
                    similarity = hit.get("similarity")
                    if isinstance(chunk_id, int) and isinstance(similarity, (int, float)):
                        scores[chunk_id] = float(similarity)

        return scores

    @staticmethod
    def _chunk_ids_from_metadata(metadata: dict) -> set[int]:
        chunk_ids: set[int] = set()

        for chunk_id in metadata.get("retrieved_chunk_ids") or []:
            if isinstance(chunk_id, int):
                chunk_ids.add(chunk_id)

        for chunk in metadata.get("retrieved_chunks") or []:
            if isinstance(chunk, dict) and isinstance(chunk.get("id"), int):
                chunk_ids.add(chunk["id"])

        for step in metadata.get("rag_trace") or []:
            if not isinstance(step, dict):
                continue

            data = step.get("data")
            if not isinstance(data, dict):
                continue

            for hit in data.get("hits") or []:
                if isinstance(hit, dict) and isinstance(hit.get("id"), int):
                    chunk_ids.add(hit["id"])

            for lane in data.get("lanes") or []:
                if not isinstance(lane, dict):
                    continue

                for hit in lane.get("hits") or []:
                    if isinstance(hit, dict) and isinstance(hit.get("id"), int):
                        chunk_ids.add(hit["id"])

        return chunk_ids

    async def _load_chunk_map_for_metadata(self, metadata_list: list[dict]) -> dict[int, ChunkMeta]:
        chunk_ids: set[int] = set()

        for metadata in metadata_list:
            chunk_ids.update(self._chunk_ids_from_metadata(metadata))

        if not chunk_ids:
            return {}

        chunks = await self.db.etl.chunks.list_by_ids(list(chunk_ids))
        return {chunk.id: chunk for chunk in chunks if chunk.id is not None}

    @staticmethod
    def _enrich_trace_hit(hit: dict, chunk_map: dict[int, ChunkMeta]) -> dict:
        enriched = dict(hit)
        chunk_id = enriched.get("id")

        if not isinstance(chunk_id, int):
            return enriched

        chunk_meta = chunk_map.get(chunk_id)
        if chunk_meta is None:
            return enriched

        if not enriched.get("title"):
            enriched["title"] = chunk_meta.title

        if not enriched.get("section"):
            enriched["section"] = chunk_meta.section

        if not enriched.get("content_type"):
            enriched["content_type"] = chunk_meta.content_type

        if not enriched.get("retrieval_lane"):
            enriched["retrieval_lane"] = enriched.get("lane") or chunk_meta.content_type

        if not enriched.get("content_preview"):
            enriched["content_preview"] = chunk_meta.content[:600]

        return enriched

    @staticmethod
    def _enrich_rag_trace_steps(trace: list, chunk_map: dict[int, ChunkMeta]) -> list:
        enriched_steps: list = []

        for step in trace:
            if not isinstance(step, dict):
                continue

            step_dict = dict(step)
            data = step_dict.get("data")
            if not isinstance(data, dict):
                enriched_steps.append(step_dict)
                continue

            data_dict = dict(data)
            hits = data_dict.get("hits")

            if isinstance(hits, list):
                data_dict["hits"] = [
                    ChatService._enrich_trace_hit(hit, chunk_map) if isinstance(hit, dict) else hit
                    for hit in hits
                ]

            lanes = data_dict.get("lanes")
            if isinstance(lanes, list):
                enriched_lanes: list[dict] = []

                for lane in lanes:
                    if not isinstance(lane, dict):
                        continue

                    lane_dict = dict(lane)
                    lane_hits = lane_dict.get("hits")

                    if isinstance(lane_hits, list):
                        lane_dict["hits"] = [
                            ChatService._enrich_trace_hit(hit, chunk_map) if isinstance(hit, dict) else hit
                            for hit in lane_hits
                        ]

                    enriched_lanes.append(lane_dict)

                data_dict["lanes"] = enriched_lanes

            step_dict["data"] = data_dict
            enriched_steps.append(step_dict)

        return enriched_steps

    @staticmethod
    def _enrich_rag_metadata(metadata: dict, chunk_map: dict[int, ChunkMeta]) -> dict:
        enriched = dict(metadata)
        similarity_by_id = ChatService._similarity_scores_from_trace(enriched)

        existing = enriched.get("retrieved_chunks")
        if existing:
            merged: list[dict] = []

            for chunk in existing:
                if not isinstance(chunk, dict):
                    continue

                chunk_dict = dict(chunk)
                chunk_id = chunk_dict.get("id")
                similarity = chunk_dict.get("similarity")

                if similarity is None:
                    similarity = chunk_dict.get("score")

                if similarity is None and isinstance(chunk_id, int):
                    similarity = similarity_by_id.get(chunk_id)

                if similarity is not None:
                    chunk_dict["similarity"] = similarity
                    chunk_dict["score"] = similarity

                if isinstance(chunk_id, int):
                    chunk_meta = chunk_map.get(chunk_id)
                    if chunk_meta is not None:
                        if not chunk_dict.get("title"):
                            chunk_dict["title"] = chunk_meta.title
                        if not chunk_dict.get("section"):
                            chunk_dict["section"] = chunk_meta.section
                        if not chunk_dict.get("node_id"):
                            chunk_dict["node_id"] = chunk_meta.node_id
                        if not chunk_dict.get("content_type"):
                            chunk_dict["content_type"] = chunk_meta.content_type
                        if not chunk_dict.get("retrieval_lane"):
                            chunk_dict["retrieval_lane"] = chunk_meta.content_type
                        if not chunk_dict.get("token_count"):
                            chunk_dict["token_count"] = chunk_meta.token_count
                        if not chunk_dict.get("content_preview"):
                            chunk_dict["content_preview"] = chunk_meta.content[:600]

                merged.append(chunk_dict)

            enriched["retrieved_chunks"] = merged

        elif metadata.get("retrieved_chunk_ids"):
            serialized: list[dict] = []

            for citation_index, chunk_id in enumerate(metadata["retrieved_chunk_ids"], start=1):
                if not isinstance(chunk_id, int):
                    continue

                chunk = chunk_map.get(chunk_id)
                if chunk is None:
                    continue

                serialized.append(
                    ChatService._serialize_chunk_meta(
                        chunk,
                        citation_index=citation_index,
                        similarity=similarity_by_id.get(chunk_id),
                    ),
                )

            enriched["retrieved_chunks"] = serialized

        rag_trace = enriched.get("rag_trace")

        if isinstance(rag_trace, list) and rag_trace:
            enriched["rag_trace"] = ChatService._enrich_rag_trace_steps(rag_trace, chunk_map)

        return enriched

    @staticmethod
    def _rag_retrieval_metadata(rag_result) -> dict:
        return {
            "search_queries": rag_result.search_queries,
            "retrieved_chunk_ids": [
                item.chunk.id for item in rag_result.chunks if item.chunk.id is not None
            ],
            "retrieved_chunks": ChatService._serialize_retrieved_chunks(rag_result.chunks),
            "rag_trace": ChatService._serialize_rag_trace(rag_result.trace),
        }

    @staticmethod
    def _is_llm_free_mode(llm_config: LlmConfig | None) -> bool:
        return llm_config is not None and llm_config.use_custom_prompt is True

    @staticmethod
    def _resolve_custom_system_prompt(llm_config: LlmConfig | None) -> str | None:
        if llm_config is None or not llm_config.use_custom_prompt:
            return None

        custom_prompt = (llm_config.custom_prompt or "").strip()

        return custom_prompt or None

    @staticmethod
    def _chat_to_summary(chat) -> ChatSummaryResponse:
        return ChatSummaryResponse(
            id=chat.id,
            title=chat.title,
            chat_type=ChatType(chat.chat_type),
            is_closed=chat.is_closed,
            message_count=chat.message_count,
            rag_config=ChatService._parse_rag_config(chat.rag_config),
            llm_config=ChatService._parse_llm_config(chat.llm_config),
            use_history=chat.use_history,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            closed_at=chat.closed_at,
        )

    def _message_to_response(self, message, *, chunk_map: dict[int, ChunkMeta] | None = None) -> ChatMessageResponse:
        metadata = message.message_metadata

        if chunk_map is not None:
            metadata = self._enrich_rag_metadata(metadata, chunk_map)

        return ChatMessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            role=MessageRole(message.role),
            content=message.content,
            rating=message.rating,
            rating_comment=message.rating_comment,
            metadata=metadata,
            created_at=message.created_at,
            updated_at=message.updated_at,
        )

    @staticmethod
    async def _publish_error(client_id: str | None, chat_id: int, exc: Exception) -> None:
        if not client_id:
            return

        error_code = getattr(exc, "error_code", "chat_error")
        detail = getattr(exc, "detail", str(exc))

        await sse_manager.publish(
            client_id,
            "error",
            {"message": detail, "chat_id": chat_id, "error_code": error_code},
        )

    async def _get_open_chat(self, chat_id: int):
        chat = await self.db.chat.chats.get_by_id(chat_id)
        if chat is None:
            raise ServiceError(
                detail="Chat not found",
                error_code="chat_not_found",
                status_code=404,
            )

        if chat.is_closed:
            raise ServiceError(
                detail="Chat is closed",
                error_code="chat_closed",
                status_code=409,
            )
        return chat

    @handle_basic_db_errors
    async def list_chats(self, chat_type: ChatType | None = None) -> list[ChatSummaryResponse]:
        """
        Return active (non-deleted) chats for the sidebar.
        """

        chats = await self.db.chat.chats.list_active(chat_type=chat_type)
        return [self._chat_to_summary(chat) for chat in chats]

    @handle_basic_db_errors
    async def create_chat(self, body: CreateChatRequest) -> ChatSummaryResponse:
        """
        Create a new chat thread.
        """

        use_history = body.use_history
        llm_config = body.llm_config.model_dump() if body.llm_config else None
        rag_config = body.rag_config.model_dump() if body.rag_config else None

        if body.chat_type == ChatType.LLM:
            if use_history is None:
                use_history = True

            if llm_config is None:
                llm_config = {
                    "use_custom_prompt": False,
                    "custom_prompt": None,
                }

        if body.chat_type == ChatType.RAG:
            if use_history is None:
                use_history = True

            if rag_config is None:
                rag_config = {
                    "use_hyde": False,
                    "use_multi_query": False,
                    "use_query_rewriting": False,
                    "use_rerank": False,
                    "top_chunks": DEFAULT_TOP_CHUNKS,
                }

        chat = await self.db.chat.chats.create(
            title=body.title,
            chat_type=body.chat_type,
            rag_config=rag_config,
            llm_config=llm_config,
            use_history=use_history,
        )
        await self.db.commit()

        return self._chat_to_summary(chat)

    @handle_basic_db_errors
    async def get_chat(self, chat_id: int) -> ChatDetailResponse:
        """
        Return chat metadata and message history.
        """

        chat = await self.db.chat.chats.get_by_id(chat_id)
        if chat is None:
            raise ServiceError(
                detail="Chat not found",
                error_code="chat_not_found",
                status_code=404,
            )

        messages = await self.db.chat.messages.list_by_chat(chat_id)
        chunk_map = await self._load_chunk_map_for_metadata(
            [message.message_metadata for message in messages],
        )

        return ChatDetailResponse(
            id=chat.id,
            title=chat.title,
            chat_type=ChatType(chat.chat_type),
            is_closed=chat.is_closed,
            message_count=chat.message_count,
            rag_config=self._parse_rag_config(chat.rag_config),
            llm_config=self._parse_llm_config(chat.llm_config),
            use_history=chat.use_history,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            closed_at=chat.closed_at,
            messages=[self._message_to_response(message, chunk_map=chunk_map) for message in messages],
        )

    @handle_basic_db_errors
    async def update_chat(self, chat_id: int, body: UpdateChatRequest) -> ChatSummaryResponse:
        """
        Update chat-level RAG/LLM settings (toggles, use_history).
        """

        fields_set = body.model_fields_set
        chat = await self.db.chat.chats.update_settings(
            chat_id,
            rag_config=body.rag_config.model_dump() if body.rag_config else None,
            llm_config=body.llm_config.model_dump() if body.llm_config else None,
            use_history=body.use_history,
            update_rag_config="rag_config" in fields_set,
            update_llm_config="llm_config" in fields_set,
            update_use_history="use_history" in fields_set,
        )

        if chat is None:
            raise ServiceError(
                detail="Chat not found",
                error_code="chat_not_found",
                status_code=404,
            )

        await self.db.commit()

        return self._chat_to_summary(chat)

    @handle_basic_db_errors
    async def delete_chat(self, chat_id: int) -> None:
        """
        Soft-delete a chat.
        """

        chat = await self.db.chat.chats.soft_delete(chat_id)
        if chat is None:
            raise ServiceError(
                detail="Chat not found",
                error_code="chat_not_found",
                status_code=404,
            )
        await self.db.commit()

    @handle_basic_db_errors
    async def close_chat(self, chat_id: int) -> ChatSummaryResponse:
        """
        Close chat (no further messages).
        """

        chat = await self.db.chat.chats.close(chat_id)
        if chat is None:
            raise ServiceError(
                detail="Chat not found",
                error_code="chat_not_found",
                status_code=404,
            )
        await self.db.commit()

        return self._chat_to_summary(chat)

    @handle_basic_db_errors
    async def send_message(self, chat_id: int, body: SendMessageRequest) -> SendMessageResponse:
        """
        Persist user message, call LLM synchronously, persist assistant reply.

        Errors can be mirrored to SSE when client_id is provided.
        """

        await self._get_open_chat(chat_id)
        chat = await self.db.chat.chats.get_by_id(chat_id)
        assert chat is not None

        should_generate_title = chat.message_count == 0 and is_default_chat_title(chat.title)

        chat_type = ChatType(chat.chat_type)
        use_history_value = self._resolve_use_history(body, chat)

        rag_snapshot: RagConfig | None = None
        llm_snapshot: LlmConfig | None = None

        update_rag_config = False
        update_llm_config = False
        update_use_history = "use_history" in body.model_fields_set

        if chat_type == ChatType.RAG:
            rag_snapshot = body.rag_config or self._parse_rag_config(chat.rag_config)
            update_rag_config = body.rag_config is not None

        if chat_type == ChatType.LLM:
            llm_snapshot = body.llm_config or self._parse_llm_config(chat.llm_config)
            update_llm_config = body.llm_config is not None

        if update_rag_config or update_llm_config or update_use_history:
            await self.db.chat.chats.update_settings(
                chat_id,
                rag_config=rag_snapshot.model_dump() if rag_snapshot else None,
                llm_config=llm_snapshot.model_dump() if llm_snapshot else None,
                use_history=use_history_value,
                update_rag_config=update_rag_config,
                update_llm_config=update_llm_config,
                update_use_history=update_use_history,
            )

        settings_metadata = self._settings_message_metadata(
            rag_snapshot,
            llm_snapshot,
            use_history_value,
        )

        user_message = await self.db.chat.messages.create(
            chat_id=chat_id,
            role=MessageRole.USER,
            content=body.content,
            message_metadata=settings_metadata,
        )

        history = await self.db.chat.messages.list_by_chat(chat_id)
        llm_messages = self._build_llm_messages(history, body.content, use_history_value)

        client = ChatCompletionClient(self.settings.llm)
        requested_at = datetime.now(UTC).isoformat()
        free_mode = chat_type == ChatType.LLM and self._is_llm_free_mode(llm_snapshot)
        block_reason = None if free_mode else evaluate_user_message(body.content)

        if block_reason is not None:
            assistant_text = blocked_refusal(body.content)
            llm_metadata: dict = {
                "model": self.settings.llm.model,
                "latency_ms": 0,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "blocked_reason": block_reason.value,
            }
            assistant_metadata = {**llm_metadata, "requested_at": requested_at, **settings_metadata}
            assistant_message = await self.db.chat.messages.create(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=assistant_text,
                message_metadata=assistant_metadata,
            )

            if block_reason is BlockReason.INJECTION:
                await self.db.chat.chats.close(chat_id)
            else:
                await self.db.chat.chats.touch(chat_id)

            await self.db.chat.chats.adjust_message_count(chat_id, 2)
            await self.db.commit()
        else:
            # Commit the user message before LLM/RAG I/O so SQLite is not write-locked
            # for the duration of external calls (title generation, other chats, etc.).
            await self.db.chat.chats.touch(chat_id)
            await self.db.chat.chats.adjust_message_count(chat_id, 1)
            await self.db.commit()

            try:
                reply_language = reply_language_for_user_text(body.content)

                if chat_type == ChatType.RAG:
                    rag_config = rag_snapshot or RagConfig()
                    pipeline = RagPipeline(self.db, self.settings)
                    rag_result = await pipeline.run(
                        RagQueryContext(
                            query=body.content,
                            history=self._rag_history_messages(history, use_history=use_history_value),
                            rag_config=rag_config,
                            reply_language=reply_language,
                        ),
                    )
                    await self._publish_rag_trace(body.client_id, rag_result.trace)
                    settings_metadata.update(self._rag_retrieval_metadata(rag_result))

                    dt_guidance = None

                    if rag_result.applicable_decision_trees:
                        dt_started = time.perf_counter()
                        dt_guidance = await generate_decision_tree_guidance(
                            client,
                            query=body.content,
                            tree=rag_result.applicable_decision_trees[0],
                            reply_language=reply_language,
                        )
                        dt_duration_ms = int((time.perf_counter() - dt_started) * 1000)
                        candidate = rag_result.applicable_decision_trees[0]
                        rag_result.trace.append(
                            RagTraceStep(
                                step="decision_tree_generation",
                                duration_ms=dt_duration_ms,
                                data={
                                    "chunk_id": candidate.chunk.id,
                                    "title": candidate.chunk.title,
                                    "applied": dt_guidance is not None,
                                },
                            ),
                        )
                        settings_metadata["rag_trace"] = self._serialize_rag_trace(rag_result.trace)
                        await self._publish_rag_trace(body.client_id, rag_result.trace[-1:])

                        if dt_guidance is not None:
                            settings_metadata["decision_tree_guidance"] = dt_guidance.to_metadata()

                    context_for_general = rag_result.context

                    if dt_guidance is not None:
                        context_for_general = build_context_block(
                            exclude_decision_tree_chunks(rag_result.chunks),
                        )

                    assistant_text, llm_metadata = await client.complete(
                        llm_messages,
                        system_prompt=pipeline.build_generation_prompt(
                            context=context_for_general,
                            reply_language=reply_language,
                        ),
                    )
                elif free_mode:
                    assistant_text, llm_metadata = await client.complete(
                        llm_messages,
                        system_prompt=self._resolve_custom_system_prompt(llm_snapshot),
                        harden_user_messages=False,
                    )
                else:
                    assistant_text, llm_metadata = await client.complete(
                        llm_messages,
                        system_prompt=build_system_prompt(reply_language=reply_language),
                    )
            except Exception as exc:
                await self._publish_error(body.client_id, chat_id, exc)
                raise

            assistant_metadata = {**llm_metadata, "requested_at": requested_at, **settings_metadata}
            assistant_message = await self.db.chat.messages.create(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=assistant_text,
                message_metadata=assistant_metadata,
            )

            await self.db.chat.chats.touch(chat_id)
            await self.db.chat.chats.adjust_message_count(chat_id, 1)
            await self.db.commit()

        chunk_map = await self._load_chunk_map_for_metadata(
            [user_message.message_metadata, assistant_message.message_metadata],
        )

        logger.info(
            "chat_message_sent",
            chat_id=chat_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
        )

        if should_generate_title:
            custom_system_prompt = None

            if chat_type == ChatType.LLM and self._is_llm_free_mode(llm_snapshot):
                custom_system_prompt = self._resolve_custom_system_prompt(llm_snapshot)

            schedule_chat_title_generation(
                chat_id=chat_id,
                client_id=body.client_id,
                user_message=body.content,
                chat_type=chat_type,
                custom_system_prompt=custom_system_prompt,
                app_settings=self.settings,
            )

        return SendMessageResponse(
            user_message=self._message_to_response(user_message, chunk_map=chunk_map),
            assistant_message=self._message_to_response(assistant_message, chunk_map=chunk_map),
        )

    @handle_basic_db_errors
    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        body: EditMessageRequest,
    ) -> ChatMessageResponse:
        """
        Edit a user message.
        """

        await self._get_open_chat(chat_id)

        message = await self.db.chat.messages.get_by_id(message_id, chat_id)
        if message is None:
            raise ServiceError(
                detail="Message not found",
                error_code="message_not_found",
                status_code=404,
            )

        if message.role != MessageRole.USER.value:
            raise ServiceError(
                detail="Only user messages can be edited",
                error_code="message_not_editable",
                status_code=400,
            )

        updated = await self.db.chat.messages.update_content(message, body.content)
        await self.db.chat.chats.touch(chat_id)
        await self.db.commit()

        return self._message_to_response(updated)

    @handle_basic_db_errors
    async def set_rating(
        self,
        chat_id: int,
        message_id: int,
        body: SetRatingRequest,
    ) -> ChatMessageResponse:
        """
        Set rating and optional comment on an assistant message.
        """

        message = await self.db.chat.messages.get_by_id(message_id, chat_id)
        if message is None:
            raise ServiceError(
                detail="Message not found",
                error_code="message_not_found",
                status_code=404,
            )

        if message.role != MessageRole.ASSISTANT.value:
            raise ServiceError(
                detail="Only assistant messages can be rated",
                error_code="message_not_rateable",
                status_code=400,
            )

        updated = await self.db.chat.messages.set_rating(
            message,
            rating=body.rating,
            rating_comment=body.comment,
        )
        await self.db.chat.chats.touch(chat_id)
        await self.db.commit()

        return self._message_to_response(updated)

    @handle_basic_db_errors
    async def delete_message(self, chat_id: int, message_id: int) -> None:
        """
        Soft-delete a message.
        """

        message = await self.db.chat.messages.get_by_id(message_id, chat_id)
        if message is None:
            raise ServiceError(
                detail="Message not found",
                error_code="message_not_found",
                status_code=404,
            )

        await self.db.chat.messages.soft_delete(message)
        await self.db.chat.chats.adjust_message_count(chat_id, -1)
        await self.db.chat.chats.touch(chat_id)
        await self.db.commit()
