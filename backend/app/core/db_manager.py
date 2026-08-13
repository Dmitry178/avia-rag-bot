from sqlalchemy.exc import IllegalStateChangeError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.chat import ChatRepository
from app.repositories.chat_message import ChatMessageRepository
from app.repositories.health import HealthRepository


class DBManager:
    """
    Async DB manager (context-managed).

    - Provides a single AsyncSession per request/task.
    - Exposes repositories as attributes.
    - Rolls back on exception, always closes the session.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session: AsyncSession | None = None

        self.health: HealthRepository
        self.chat: "DBManager.ChatDBManager"

    class ChatDBManager:
        """
        Chat-related repositories.
        """

        def __init__(self, session: AsyncSession) -> None:
            self.chats = ChatRepository(session)
            self.messages = ChatMessageRepository(session)

    async def __aenter__(self) -> "DBManager":
        self.session = self.session_factory()

        self.chat = self.ChatDBManager(self.session)
        self.health = HealthRepository(self.session)

        return self

    async def __aexit__(self, exc_type, _exc_val, _exc_tb) -> None:
        if self.session is None:
            return

        try:
            if self.session.in_transaction():
                await self.session.rollback()
        except Exception:
            pass

        try:
            await self.session.close()
        except IllegalStateChangeError:
            pass

    async def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("DBManager session is not initialized")
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("DBManager session is not initialized")
        await self.session.rollback()
