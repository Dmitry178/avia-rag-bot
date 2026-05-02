"""ETL API integration tests."""

import pytest

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_etl_stats_returns_counts(client: AsyncClient) -> None:
    """
    ETL stats endpoint should return total and per-content-type counts.
    """

    response = await client.get("/api/etl/stats")

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "by_content_type" in data


@pytest.mark.asyncio
async def test_etl_manifest_not_found_without_index(client: AsyncClient) -> None:
    """
    ETL manifest endpoint should return 404 when no index is built.
    """

    response = await client.get("/api/etl/manifest")

    assert response.status_code == 404
