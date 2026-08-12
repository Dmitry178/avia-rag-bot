"""ETL-only database manager (no chat repositories)."""

from sqlalchemy.exc import IllegalStateChangeError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.repositories.chunk import ChunkRepository
from src.repositories.index_manifest import IndexManifestRepository


class DBManager:
    """
    Async DB manager for KB tables (ChunkMeta, IndexManifest).
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session: AsyncSession | None = None
        self.etl: "DBManager.EtlDBManager"

    class EtlDBManager:
        """
        ETL-related repositories.
        """

        def __init__(self, session: AsyncSession) -> None:
            self.chunks = ChunkRepository(session)
            self.index_manifest = IndexManifestRepository(session)

    async def __aenter__(self) -> "DBManager":
        self.session = self.session_factory()
        self.etl = self.EtlDBManager(self.session)
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
            return
        await self.session.rollback()
