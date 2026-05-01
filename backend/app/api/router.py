"""Aggregate API routers."""

from fastapi import APIRouter

from app.api.routers import health

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
