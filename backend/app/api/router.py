"""Aggregate API routers."""

from fastapi import APIRouter

from app.api.routers.chat import router as chats_router
from app.api.routers.etl import router as etl_router
from app.api.routers.health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(etl_router)
api_router.include_router(chats_router)
