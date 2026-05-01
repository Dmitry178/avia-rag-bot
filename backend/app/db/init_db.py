"""Create database tables on startup."""

from sqlmodel import SQLModel

from app.db.session import engine
from app.models import ChunkMeta, IndexManifest  # noqa: F401


async def init_db() -> None:
    """
    Create all SQLModel tables if they do not exist.
    """

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
