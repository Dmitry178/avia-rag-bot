"""Shared fixtures for HTTP API integration tests."""

import pytest

from httpx import ASGITransport, AsyncClient

from app.core.lifespan import lifespan
from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """
    HTTP client with application lifespan started.
    """

    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client
