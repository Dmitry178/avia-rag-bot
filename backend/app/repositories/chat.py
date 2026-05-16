"""Chat persistence."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat, ChatType


class ChatRepository:
    """
    CRUD and lifecycle operations for chat threads.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self, chat_type: ChatType | None = None) -> list[Chat]:
        """
        Return non-deleted chats ordered by last activity.
        """

        statement = select(Chat).where(Chat.is_deleted.is_(False))

        if chat_type is not None:
            statement = statement.where(Chat.chat_type == chat_type.value)

        statement = statement.order_by(Chat.updated_at.desc())
        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def get_by_id(self, chat_id: int) -> Chat | None:
        """
        Return a chat by id or None if missing or soft-deleted.
        """

        statement = select(Chat).where(Chat.id == chat_id, Chat.is_deleted.is_(False))
        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def create(
        self,
        title: str = "New chat",
        chat_type: ChatType = ChatType.LLM,
        *,
        rag_config: dict | None = None,
        llm_config: dict | None = None,
        use_history: bool | None = None,
    ) -> Chat:
        """
        Insert a new open chat.
        """

        now = datetime.now(UTC)
        chat = Chat(
            title=title,
            chat_type=chat_type.value,
            message_count=0,
            rag_config=rag_config,
            llm_config=llm_config,
            use_history=use_history,
            created_at=now,
            updated_at=now,
        )
        self.session.add(chat)
        await self.session.flush()
        await self.session.refresh(chat)

        return chat

    async def adjust_message_count(self, chat_id: int, delta: int) -> None:
        """
        Increment or decrement denormalized message_count (floored at zero).
        """

        chat = await self.get_by_id(chat_id)
        if chat is None:
            return

        chat.message_count = max(0, chat.message_count + delta)
        chat.updated_at = datetime.now(UTC)
        self.session.add(chat)
        await self.session.flush()

    async def update_settings(
        self,
        chat_id: int,
        *,
        rag_config: dict | None = None,
        llm_config: dict | None = None,
        use_history: bool | None = None,
        update_rag_config: bool = False,
        update_llm_config: bool = False,
        update_use_history: bool = False,
    ) -> Chat | None:
        """
        Update chat-level RAG/LLM settings.
        """

        chat = await self.get_by_id(chat_id)
        if chat is None:
            return None

        if update_rag_config:
            chat.rag_config = rag_config

        if update_llm_config:
            chat.llm_config = llm_config

        if update_use_history:
            chat.use_history = use_history

        chat.updated_at = datetime.now(UTC)
        self.session.add(chat)
        await self.session.flush()
        await self.session.refresh(chat)

        return chat

    async def touch(self, chat_id: int) -> None:
        """
        Bump updated_at after a new message.
        """

        await self.session.execute(
            update(Chat).where(Chat.id == chat_id).values(updated_at=datetime.now(UTC))
        )

    async def soft_delete(self, chat_id: int) -> Chat | None:
        """
        Mark chat as deleted; returns updated row or None if not found.
        """

        chat = await self.get_by_id(chat_id)
        if chat is None:
            return None

        chat.is_deleted = True
        chat.updated_at = datetime.now(UTC)
        self.session.add(chat)
        await self.session.flush()
        await self.session.refresh(chat)

        return chat

    async def close(self, chat_id: int) -> Chat | None:
        """
        Mark chat as closed; returns updated row or None if not found.
        """

        chat = await self.get_by_id(chat_id)
        if chat is None:
            return None

        now = datetime.now(UTC)
        chat.is_closed = True
        chat.closed_at = now
        chat.updated_at = now
        self.session.add(chat)
        await self.session.flush()
        await self.session.refresh(chat)

        return chat
