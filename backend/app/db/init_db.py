"""Create database tables on startup (chats only)."""

from sqlalchemy import inspect, text
from sqlmodel import SQLModel

from app.db.session import engine
from app.models import Chat, ChatMessage  # noqa: F401


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


async def _ensure_chat_rag_columns() -> None:
    """
    Add RAG settings and message_count columns to existing chat tables.
    """

    async with engine.begin() as conn:
        def _missing_chat_columns(sync_conn) -> list[str]:
            inspector = inspect(sync_conn)
            if "chat" not in inspector.get_table_names():
                return []

            existing = {column["name"] for column in inspector.get_columns("chat")}
            statements: list[str] = []

            if "message_count" not in existing:
                statements.append("ALTER TABLE chat ADD COLUMN message_count INTEGER NOT NULL DEFAULT 0")

            if "rag_config" not in existing:
                statements.append("ALTER TABLE chat ADD COLUMN rag_config JSON")

            if "use_history" not in existing:
                statements.append("ALTER TABLE chat ADD COLUMN use_history BOOLEAN")

            if "llm_config" not in existing:
                statements.append("ALTER TABLE chat ADD COLUMN llm_config JSON")

            return statements

        statements = await conn.run_sync(_missing_chat_columns)
        for statement in statements:
            await conn.execute(text(statement))

        if any("message_count" in statement for statement in statements):
            await conn.execute(
                text(
                    """
                    UPDATE chat
                    SET message_count = (
                        SELECT COUNT(*)
                        FROM chat_message
                        WHERE chat_message.chat_id = chat.id
                          AND chat_message.is_deleted = 0
                    )
                    """
                )
            )


async def _ensure_chat_language_column() -> None:
    """
    Add language_code to chat when missing.
    """

    async with engine.begin() as conn:
        def _missing(sync_conn) -> str | None:
            inspector = inspect(sync_conn)
            if "chat" not in inspector.get_table_names():
                return None

            chat_columns = {column["name"] for column in inspector.get_columns("chat")}
            if "language_code" not in chat_columns:
                return "ALTER TABLE chat ADD COLUMN language_code VARCHAR NOT NULL DEFAULT 'ru'"

            return None

        statement = await conn.run_sync(_missing)
        if statement:
            await conn.execute(text(statement))


async def init_db() -> None:
    """
    Create chat tables if they do not exist.
    """

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    await _ensure_chat_type_column()
    await _ensure_chat_rag_columns()
    await _ensure_chat_language_column()
