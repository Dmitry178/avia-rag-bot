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


async def _ensure_etl_columns() -> None:
    """
    Add incremental ETL columns to existing SQLite dev DBs.
    """

    async with engine.begin() as conn:
        def _missing_columns(sync_conn) -> list[tuple[str, str]]:
            inspector = inspect(sync_conn)
            missing: list[tuple[str, str]] = []

            if "chunk_meta" in inspector.get_table_names():
                chunk_columns = {column["name"] for column in inspector.get_columns("chunk_meta")}
                if "content_hash" not in chunk_columns:
                    missing.append(
                        ("chunk_meta", "ALTER TABLE chunk_meta ADD COLUMN content_hash VARCHAR NOT NULL DEFAULT ''")
                    )

            if "index_manifest" in inspector.get_table_names():
                manifest_columns = {column["name"] for column in inspector.get_columns("index_manifest")}
                if "chunker_version" not in manifest_columns:
                    missing.append(
                        (
                            "index_manifest",
                            "ALTER TABLE index_manifest ADD COLUMN chunker_version VARCHAR NOT NULL DEFAULT ''",
                        )
                    )

            return missing

        for _table, statement in await conn.run_sync(_missing_columns):
            await conn.execute(text(statement))


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


async def _ensure_multilingual_schema() -> None:
    """
    Add language_code columns for multilingual RAG; drop legacy kb_language table if present.
    """

    async with engine.begin() as conn:
        def _needs_chunk_meta_rebuild(sync_conn) -> bool:
            inspector = inspect(sync_conn)
            if "chunk_meta" not in inspector.get_table_names():
                return False

            columns = {column["name"] for column in inspector.get_columns("chunk_meta")}
            return "language_code" not in columns

        def _chunk_meta_columns(sync_conn) -> set[str]:
            inspector = inspect(sync_conn)
            if "chunk_meta" not in inspector.get_table_names():
                return set()

            return {column["name"] for column in inspector.get_columns("chunk_meta")}

        needs_rebuild = await conn.run_sync(_needs_chunk_meta_rebuild)

        if needs_rebuild:
            columns = await conn.run_sync(_chunk_meta_columns)
            if columns:
                await conn.execute(
                    text(
                        """
                        CREATE TABLE chunk_meta_new (
                            language_code VARCHAR NOT NULL DEFAULT 'ru',
                            id INTEGER NOT NULL,
                            content TEXT NOT NULL,
                            content_type VARCHAR NOT NULL,
                            section VARCHAR NOT NULL,
                            title VARCHAR NOT NULL,
                            node_id VARCHAR NOT NULL DEFAULT '',
                            content_hash VARCHAR NOT NULL DEFAULT '',
                            parent_id INTEGER,
                            token_count INTEGER NOT NULL DEFAULT 0,
                            source_path VARCHAR NOT NULL DEFAULT '',
                            created_at DATETIME NOT NULL,
                            PRIMARY KEY (language_code, id)
                        )
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        INSERT INTO chunk_meta_new (
                            language_code, id, content, content_type, section, title,
                            node_id, content_hash, parent_id, token_count, source_path, created_at
                        )
                        SELECT
                            'ru', id, content, content_type, section, title,
                            node_id, content_hash, parent_id, token_count, source_path, created_at
                        FROM chunk_meta
                        """
                    )
                )
                await conn.execute(text("DROP TABLE chunk_meta"))
                await conn.execute(text("ALTER TABLE chunk_meta_new RENAME TO chunk_meta"))

        def _missing_columns(sync_conn) -> list[str]:
            inspector = inspect(sync_conn)
            statements: list[str] = []

            if "chat" in inspector.get_table_names():
                chat_columns = {column["name"] for column in inspector.get_columns("chat")}
                if "language_code" not in chat_columns:
                    statements.append(
                        "ALTER TABLE chat ADD COLUMN language_code VARCHAR NOT NULL DEFAULT 'ru'"
                    )

            if "index_manifest" in inspector.get_table_names():
                manifest_columns = {column["name"] for column in inspector.get_columns("index_manifest")}
                if "language_code" not in manifest_columns:
                    statements.append(
                        "ALTER TABLE index_manifest ADD COLUMN language_code VARCHAR NOT NULL DEFAULT 'ru'"
                    )

            return statements

        for statement in await conn.run_sync(_missing_columns):
            await conn.execute(text(statement))

        def _has_kb_language_table(sync_conn) -> bool:
            inspector = inspect(sync_conn)
            return "kb_language" in inspector.get_table_names()

        if await conn.run_sync(_has_kb_language_table):
            await conn.execute(text("DROP TABLE kb_language"))


async def init_db() -> None:
    """
    Create all SQLModel tables if they do not exist.
    """

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    await _ensure_chat_type_column()
    await _ensure_etl_columns()
    await _ensure_chat_rag_columns()
    await _ensure_multilingual_schema()
