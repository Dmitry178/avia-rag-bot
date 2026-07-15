"""Chat message persistence."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage, MessageRole


class ChatMessageRepository:
    """
    CRUD operations for messages within a chat.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_chat(self, chat_id: int) -> list[ChatMessage]:
        """
        Return non-deleted messages for a chat in chronological order.
        """

        statement = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id, ChatMessage.is_deleted.is_(False))
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def find_user_message_by_client_id(
        self,
        chat_id: int,
        client_message_id: str,
    ) -> ChatMessage | None:
        """
        Return the newest non-deleted user message tagged with client_message_id.
        """

        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.chat_id == chat_id,
                ChatMessage.role == MessageRole.USER.value,
                ChatMessage.is_deleted.is_(False),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(50)
        )
        result = await self.session.execute(statement)

        for message in result.scalars().all():
            if message.message_metadata.get("client_message_id") == client_message_id:
                return message

        return None

    async def get_by_id(self, message_id: int, chat_id: int) -> ChatMessage | None:
        """
        Return a message scoped to chat_id or None if missing or soft-deleted.
        """

        statement = select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.chat_id == chat_id,
            ChatMessage.is_deleted.is_(False),
        )
        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        chat_id: int,
        role: MessageRole | str,
        content: str,
        message_metadata: dict | None = None,
    ) -> ChatMessage:
        """
        Insert a new message.
        """

        now = datetime.now(UTC)
        message = ChatMessage(
            chat_id=chat_id,
            role=str(role),
            content=content,
            message_metadata=message_metadata or {},
            created_at=now,
            updated_at=now,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)

        return message

    async def update_content(self, message: ChatMessage, content: str) -> ChatMessage:
        """
        Edit message body.
        """

        message.content = content
        message.updated_at = datetime.now(UTC)
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)

        return message

    async def set_rating(
        self,
        message: ChatMessage,
        *,
        rating: int | None,
        rating_comment: str | None,
    ) -> ChatMessage:
        """
        Set or clear user rating on an assistant message.
        """

        message.rating = rating
        message.rating_comment = rating_comment
        message.updated_at = datetime.now(UTC)
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def soft_delete(self, message: ChatMessage) -> ChatMessage:
        """
        Mark message as deleted.
        """

        message.is_deleted = True
        message.updated_at = datetime.now(UTC)
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)

        return message
