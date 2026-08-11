"""ETL API integration tests."""

import pytest

from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.exceptions import ServiceError
from tests.api.mocks import (
    MOCK_CHUNK_STATS,
    MOCK_CHUNK_STATS_RU,
    MOCK_INGEST_ALL_RESPONSE,
    MOCK_INGEST_RESPONSE,
    MOCK_MANIFEST_RESPONSE,
    MOCK_MANIFEST_RESPONSE_EN,
)

SCHEMA_PATH = "data/chunking-schema-ru.json"


@pytest.mark.asyncio
async def test_etl_ingest_returns_mocked_response(client: AsyncClient) -> None:
    """
    Ingest endpoint should return the service result when ingestion succeeds.
    """

    with patch("app.api.routers.etl.ingest_chunking_schema_at_path", new_callable=AsyncMock) as ingest_mock:
        ingest_mock.return_value = MOCK_INGEST_RESPONSE
        response = await client.post(
            "/api/etl/ingest",
            json={"schema_path": SCHEMA_PATH, "rebuild": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["chunk_count"] == 42
    assert data["doc_hash"] == "deadbeef"
    assert data["embedded"] == 12
    ingest_mock.assert_awaited_once()
    schema_path = ingest_mock.await_args.args[0]
    call_kwargs = ingest_mock.await_args.kwargs
    assert call_kwargs["rebuild"] is False
    assert call_kwargs["source_path"] is None
    assert str(schema_path).endswith(SCHEMA_PATH)


@pytest.mark.asyncio
async def test_etl_ingest_passes_rebuild_and_source_path(client: AsyncClient) -> None:
    """
    Ingest endpoint should forward rebuild flag and optional source_path to the service.
    """

    with patch("app.api.routers.etl.ingest_chunking_schema_at_path", new_callable=AsyncMock) as ingest_mock:
        ingest_mock.return_value = MOCK_INGEST_RESPONSE
        response = await client.post(
            "/api/etl/ingest",
            json={
                "schema_path": SCHEMA_PATH,
                "rebuild": True,
                "source_path": "/custom/doc.md",
            },
        )

    assert response.status_code == 200
    ingest_mock.assert_awaited_once()
    call_kwargs = ingest_mock.await_args.kwargs
    assert call_kwargs["rebuild"] is True
    assert call_kwargs["source_path"] == "/custom/doc.md"


@pytest.mark.asyncio
async def test_etl_ingest_propagates_service_error(client: AsyncClient) -> None:
    """
    Ingest endpoint should map service failures to HTTP error responses.
    """

    with patch("app.api.routers.etl.ingest_chunking_schema_at_path", new_callable=AsyncMock) as ingest_mock:
        ingest_mock.side_effect = ServiceError(
            detail="Knowledge base file not found",
            error_code="etl_source_not_found",
            status_code=404,
        )
        response = await client.post("/api/etl/ingest", json={"schema_path": SCHEMA_PATH})

    assert response.status_code == 404
    assert response.json()["error_code"] == "etl_source_not_found"


@pytest.mark.asyncio
async def test_etl_ingest_requires_schema_path(client: AsyncClient) -> None:
    """
    Ingest endpoint should reject requests without schema_path.
    """

    response = await client.post("/api/etl/ingest", json={"rebuild": False})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_etl_ingest_all_returns_mocked_results(client: AsyncClient) -> None:
    """
    Ingest-all endpoint should return one IngestResponse per language from the service.
    """

    with patch("app.api.routers.etl.ETLService") as etl_service_cls:
        etl_service_cls.return_value.ingest_all = AsyncMock(return_value=MOCK_INGEST_ALL_RESPONSE)
        response = await client.post("/api/etl/ingest-all", json={"rebuild": False})

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["language_code"] == "ru"
    assert data["results"][0]["chunk_count"] == 42
    etl_service_cls.return_value.ingest_all.assert_awaited_once_with(rebuild=False)


@pytest.mark.asyncio
async def test_etl_ingest_all_forwards_rebuild_flag(client: AsyncClient) -> None:
    """
    Ingest-all endpoint should pass rebuild=true to the service.
    """

    with patch("app.api.routers.etl.ETLService") as etl_service_cls:
        etl_service_cls.return_value.ingest_all = AsyncMock(return_value=MOCK_INGEST_ALL_RESPONSE)
        response = await client.post("/api/etl/ingest-all", json={"rebuild": True})

    assert response.status_code == 200
    etl_service_cls.return_value.ingest_all.assert_awaited_once_with(rebuild=True)


@pytest.mark.asyncio
async def test_etl_ingest_all_propagates_service_error(client: AsyncClient) -> None:
    """
    Ingest-all endpoint should map service failures to HTTP error responses.
    """

    with patch("app.api.routers.etl.ETLService") as etl_service_cls:
        etl_service_cls.return_value.ingest_all = AsyncMock(
            side_effect=ServiceError(
                detail="Embedding provider unavailable",
                error_code="etl_embedding_mismatch",
                status_code=502,
            ),
        )
        response = await client.post("/api/etl/ingest-all", json={})

    assert response.status_code == 502
    assert response.json()["error_code"] == "etl_embedding_mismatch"


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
async def test_etl_stats_returns_mocked_distribution(client: AsyncClient) -> None:
    """
    ETL stats endpoint should serialize the service response unchanged.
    """

    with patch("app.api.routers.etl.ETLService") as etl_service_cls:
        etl_service_cls.return_value.stats = AsyncMock(return_value=MOCK_CHUNK_STATS)
        response = await client.get("/api/etl/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 42
    assert data["by_content_type"]["sop"] == 20


@pytest.mark.asyncio
async def test_etl_stats_returns_empty_counts_for_fresh_database(client: AsyncClient) -> None:
    """
    ETL stats on an empty test database should report zero chunks.
    """

    response = await client.get("/api/etl/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["by_content_type"] == {}


@pytest.mark.asyncio
async def test_etl_stats_forwards_language_code_filter(client: AsyncClient) -> None:
    """
    ETL stats endpoint should forward an optional language_code query parameter.
    """

    with patch("app.api.routers.etl.ETLService") as etl_service_cls:
        etl_service_cls.return_value.stats = AsyncMock(return_value=MOCK_CHUNK_STATS_RU)
        response = await client.get("/api/etl/stats", params={"language_code": "ru"})

    assert response.status_code == 200
    data = response.json()
    assert data["language_code"] == "ru"
    assert data["total"] == 10
    etl_service_cls.return_value.stats.assert_awaited_once_with(language_code="ru")


@pytest.mark.asyncio
async def test_etl_manifest_not_found_without_index(client: AsyncClient) -> None:
    """
    ETL manifest endpoint should return 404 when no index is built.
    """

    response = await client.get("/api/etl/manifest")

    assert response.status_code == 404
    assert response.json()["error_code"] == "etl_not_indexed"


@pytest.mark.asyncio
async def test_etl_manifest_returns_mocked_metadata(client: AsyncClient) -> None:
    """
    ETL manifest endpoint should return latest index metadata from the service.
    """

    with patch("app.api.routers.etl.ETLService") as etl_service_cls:
        etl_service_cls.return_value.manifest = AsyncMock(return_value=MOCK_MANIFEST_RESPONSE)
        response = await client.get("/api/etl/manifest")

    assert response.status_code == 200
    data = response.json()
    assert data["chunk_count"] == 42
    assert data["embedding_model"] == "text-embedding-test"
    assert data["chunker_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_etl_manifest_includes_built_at_timestamp(client: AsyncClient) -> None:
    """
    ETL manifest response should include a UTC built_at timestamp.
    """

    with patch("app.api.routers.etl.ETLService") as etl_service_cls:
        etl_service_cls.return_value.manifest = AsyncMock(return_value=MOCK_MANIFEST_RESPONSE)
        response = await client.get("/api/etl/manifest")

    assert response.status_code == 200
    built_at = response.json()["built_at"]
    assert built_at.endswith("+00:00") or built_at.endswith("Z")


@pytest.mark.asyncio
async def test_etl_manifest_forwards_language_code_query(client: AsyncClient) -> None:
    """
    ETL manifest endpoint should forward language_code to the service.
    """

    with patch("app.api.routers.etl.ETLService") as etl_service_cls:
        etl_service_cls.return_value.manifest = AsyncMock(return_value=MOCK_MANIFEST_RESPONSE_EN)
        response = await client.get("/api/etl/manifest", params={"language_code": "en"})

    assert response.status_code == 200
    data = response.json()
    assert data["language_code"] == "en"
    assert data["chunk_count"] == 21
    etl_service_cls.return_value.manifest.assert_awaited_once_with(language_code="en")
