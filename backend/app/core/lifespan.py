"""Application startup and shutdown lifecycle."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logs import logger
from app.db.init_db import init_db
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Run startup/shutdown hooks for the FastAPI application.
    """

    settings.data.ensure_exists()
    settings.faiss.ensure_exists(settings.backend_root)
    await init_db()
    logger.info("application_started", data_dir=settings.data.dir)

    yield

    await dispose_engine()
    logger.info("application_stopped")
