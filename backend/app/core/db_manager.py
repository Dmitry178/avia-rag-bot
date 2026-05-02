from sqlalchemy.exc import IllegalStateChangeError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.chat import ChatRepository
from app.repositories.chat_message import ChatMessageRepository
from app.repositories.chunk import ChunkRepository
from app.repositories.health import HealthRepository
from app.repositories.index_manifest import IndexManifestRepository


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

        # repositories (set in __aenter__)
        self.health: HealthRepository
        self.etl: "DBManager.EtlDBManager"
        self.chat: "DBManager.ChatDBManager"

    class EtlDBManager:
        """
        ETL-related repositories.
        """

        def __init__(self, session: AsyncSession) -> None:
            self.chunks = ChunkRepository(session)
            self.index_manifest = IndexManifestRepository(session)

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
        self.etl = self.EtlDBManager(self.session)
        self.health = HealthRepository(self.session)

        return self

    async def __aexit__(self, exc_type, _exc_val, _exc_tb) -> None:
        if self.session is None:
            return

        # Always end any open transaction before returning the connection to the pool.
        # Relying on session.close() alone can leave connections "idle in transaction"
        # if a transaction was implicitly started (even for read-only queries).
        try:
            if self.session.in_transaction():
                await self.session.rollback()
        except Exception:
            # Best-effort: never fail request teardown due to rollback issues.
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
            return
        await self.session.rollback()
