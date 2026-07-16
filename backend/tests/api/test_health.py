"""Health API integration tests."""

import pytest

from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_healthz_returns_ok(client: AsyncClient) -> None:
    """
    Liveness endpoint should report ok status.
    """

    response = await client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_healthz_returns_json_content_type(client: AsyncClient) -> None:
    """
    Liveness endpoint should respond with JSON.
    """

    response = await client.get("/api/healthz")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_healthz_rejects_post_method(client: AsyncClient) -> None:
    """
    Liveness endpoint should only accept GET requests.
    """

    response = await client.post("/api/healthz")

    assert response.status_code == 405


@pytest.mark.asyncio
async def test_readyz_returns_ok(client: AsyncClient) -> None:
    """
    Readiness endpoint should report ok when database is reachable.
    """

    response = await client.get("/api/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readyz_returns_not_ready_when_db_unreachable(client: AsyncClient) -> None:
    """
    Readiness endpoint should return 503 when dependencies are unavailable.
    """

    with patch("app.api.routers.health.HealthService") as health_service_cls:
        health_service_cls.return_value.is_ready = AsyncMock(return_value=False)
        response = await client.get("/api/readyz")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


@pytest.mark.asyncio
async def test_readyz_returns_json_content_type(client: AsyncClient) -> None:
    """
    Readiness endpoint should respond with JSON on success.
    """

    response = await client.get("/api/readyz")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
