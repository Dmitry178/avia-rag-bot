"""Health API integration tests."""

import pytest

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz_returns_ok(client: AsyncClient) -> None:
    """
    Liveness endpoint should report ok status.
    """

    response = await client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readyz_returns_ok(client: AsyncClient) -> None:
    """
    Readiness endpoint should report ok when database is reachable.
    """

    response = await client.get("/api/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
