"""Shared runtime helpers for MCP tool handlers."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

from src.core.config import Settings, settings
from src.core.db_manager import DBManager
from src.core.logs import setup_logging
from src.db.init_db import init_db
from src.db.session import SessionLocal

T = TypeVar("T")

_runtime_initialized = False


def ensure_runtime() -> None:
    """
    One-time logging setup for the MCP server process.
    """

    global _runtime_initialized

    if _runtime_initialized:
        return

    setup_logging(settings.log)
    _runtime_initialized = True


async def with_app_db(
    handler: Callable[[DBManager, Settings], Awaitable[T]],
    *,
    app_settings: Settings | None = None,
) -> T:
    """
    Open the default KB SQLite database and run an async handler.
    """

    ensure_runtime()
    resolved_settings = app_settings or settings
    await init_db()

    async with DBManager(SessionLocal) as db:
        return await handler(db, resolved_settings)


def resolve_schemas_dir(app_settings: Settings | None = None) -> Path:
    """
    Return the configured KB schemas directory.
    """

    resolved_settings = app_settings or settings
    return Path(resolved_settings.resolve_data_dir())


def resolve_schema_path(schema_path: str, *, app_settings: Settings | None = None) -> Path:
    """
    Resolve a schema path relative to the KB data directory or as absolute.
    """

    path = Path(schema_path)
    if path.is_absolute():
        return path.resolve()

    return (resolve_schemas_dir(app_settings) / path).resolve()
