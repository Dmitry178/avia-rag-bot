"""Chat use cases: CRUD, messaging, ratings (simple LLM, no RAG yet)."""

from datetime import UTC, datetime

from app.core.config import Settings, settings
from app.core.db_manager import DBManager
from app.core.logs import logger
from app.core.sse_manager import sse_manager
from app.exceptions import handle_basic_db_errors
from app.exceptions.service import ServiceError
from app.llm.chat import ChatCompletionClient
from app.models.chat import ChatType
from app.models.chat_message import MessageRole
from app.schemas.chat import (
    ChatDetailResponse,
    ChatMessageResponse,
    ChatSummaryResponse,
    CreateChatRequest,
    EditMessageRequest,
    SendMessageRequest,
    SendMessageResponse,
    SetRatingRequest,
)


class ChatService:
    """
    Orchestrates chat list, history, and synchronous LLM replies.

    RAG, streaming, and trace SSE are planned for later stages.
    """

    def __init__(self, db: DBManager, app_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = app_settings or settings

    @staticmethod
    def _chat_to_summary(chat) -> ChatSummaryResponse:
        return ChatSummaryResponse(
            id=chat.id,
            title=chat.title,
            chat_type=ChatType(chat.chat_type),
            is_closed=chat.is_closed,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            closed_at=chat.closed_at,
        )

    @staticmethod
    def _message_to_response(message) -> ChatMessageResponse:
        return ChatMessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            role=MessageRole(message.role),
            content=message.content,
            rating=message.rating,
            rating_comment=message.rating_comment,
            metadata=message.message_metadata,
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

        chat = await self.db.chat.chats.create(title=body.title, chat_type=body.chat_type)
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

        return ChatDetailResponse(
            id=chat.id,
            title=chat.title,
            chat_type=ChatType(chat.chat_type),
            is_closed=chat.is_closed,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            closed_at=chat.closed_at,
            messages=[self._message_to_response(message) for message in messages],
        )

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

        user_message = await self.db.chat.messages.create(
            chat_id=chat_id,
            role=MessageRole.USER,
            content=body.content,
        )

        history = await self.db.chat.messages.list_by_chat(chat_id)
        llm_messages = [
            {"role": message.role, "content": message.content}
            for message in history
            if message.role in {MessageRole.USER.value, MessageRole.ASSISTANT.value}
        ]

        client = ChatCompletionClient(self.settings.llm)

        try:
            assistant_text, llm_metadata = await client.complete(llm_messages)
        except Exception as exc:
            await self._publish_error(body.client_id, chat_id, exc)
            await self.db.rollback()
            raise

        requested_at = datetime.now(UTC).isoformat()
        assistant_metadata = {**llm_metadata, "requested_at": requested_at}

        assistant_message = await self.db.chat.messages.create(
            chat_id=chat_id,
            role=MessageRole.ASSISTANT,
            content=assistant_text,
            message_metadata=assistant_metadata,
        )

        await self.db.chat.chats.touch(chat_id)
        await self.db.commit()

        logger.info(
            "chat_message_sent",
            chat_id=chat_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
        )

        return SendMessageResponse(
            user_message=self._message_to_response(user_message),
            assistant_message=self._message_to_response(assistant_message),
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
        await self.db.chat.chats.touch(chat_id)
        await self.db.commit()
