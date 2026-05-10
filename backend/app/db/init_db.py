"""Create database tables on startup."""

from sqlalchemy import inspect, text
from sqlmodel import SQLModel

from app.db.session import engine
from app.models import Chat, ChatMessage, ChunkMeta, IndexManifest  # noqa: F401


async def _ensure_chat_type_column() -> None:
    """
    Add chat_type column to existing chat tables (SQLite dev DBs).
    """

    async with engine.begin() as conn:
        def _has_column(sync_conn) -> bool:
            inspector = inspect(sync_conn)
            if "chat" not in inspector.get_table_names():
                return True

            return any(column["name"] == "chat_type" for column in inspector.get_columns("chat"))

        has_column = await conn.run_sync(_has_column)
        if has_column:
            return

        await conn.execute(
            text("ALTER TABLE chat ADD COLUMN chat_type VARCHAR NOT NULL DEFAULT 'llm'")
        )


async def init_db() -> None:
    """
    Create all SQLModel tables if they do not exist.
    """

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    await _ensure_chat_type_column()
