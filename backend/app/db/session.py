"""Async database engine and session factory."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def ensure_database_paths() -> None:
    """
    Create filesystem paths required by the configured database URL.
    """

    settings.data.ensure_exists()

    sqlite_path = settings.db.sqlite_file_path
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)


def create_engine() -> AsyncEngine:
    """
    Create a singleton-style async engine.
    """

    async_url = settings.db.async_url
    connect_args = {"check_same_thread": False} if async_url.startswith("sqlite+") else {}

    return create_async_engine(async_url, echo=False, pool_pre_ping=True, connect_args=connect_args)


ensure_database_paths()
engine = create_engine()
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def dispose_engine() -> None:
    """
    Dispose database engine on application shutdown.
    """

    await engine.dispose()
