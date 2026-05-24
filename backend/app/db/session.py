"""Async database engine and session factory."""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def ensure_database_paths() -> None:
    """
    Create filesystem paths required by the configured database URL.
    """

    settings.data.ensure_exists(settings.backend_root)

    sqlite_path = settings.db.sqlite_file_path(settings.backend_root)
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)


def create_engine() -> AsyncEngine:
    """
    Build an async engine for the configured database URL.
    """

    async_url = settings.db.resolved_async_url(settings.backend_root)
    connect_args: dict[str, object] = {}

    if async_url.startswith("sqlite+"):
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 30

    engine = create_async_engine(async_url, echo=False, pool_pre_ping=True, connect_args=connect_args)

    if async_url.startswith("sqlite+"):
        @event.listens_for(engine.sync_engine, "connect")
        def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


def get_engine() -> AsyncEngine:
    """
    Return a process-wide async engine, created on first use.
    """

    global _engine

    if _engine is None:
        ensure_database_paths()
        _engine = create_engine()

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Return a process-wide async session factory, created on first use.
    """

    global _sessionmaker

    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )

    return _sessionmaker


class _EngineProxy:
    """
    Defer engine creation until first attribute access.
    """

    def __getattr__(self, name: str):
        return getattr(get_engine(), name)


class _SessionFactoryProxy:
    """
    Defer session factory creation until first use.
    """

    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(get_session_factory(), name)


engine = _EngineProxy()
SessionLocal = _SessionFactoryProxy()


async def dispose_engine() -> None:
    """
    Dispose database engine on application shutdown.
    """

    global _engine, _sessionmaker

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
