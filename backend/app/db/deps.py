from collections.abc import AsyncGenerator

from app.core.db_manager import DBManager
from app.db.session import SessionLocal


async def get_db() -> AsyncGenerator[DBManager, None]:
    """
    FastAPI dependency that provides DBManager.
    """

    async with DBManager(SessionLocal) as db:
        yield db
