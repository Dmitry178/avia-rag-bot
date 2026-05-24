"""Tests for DB error normalization."""

import httpx

from app.exceptions.db_errors import _map_exception
from app.exceptions.service import ServiceError


def test_map_exception_preserves_httpx_message() -> None:
    mapped = _map_exception(httpx.ConnectError("Name or service not known"))

    assert isinstance(mapped, ServiceError)
    assert mapped.detail == "Name or service not known"
    assert mapped.error_code == "external_api_error"
    assert mapped.status_code == 502


def test_map_exception_preserves_value_error_message() -> None:
    mapped = _map_exception(ValueError("FAISS dimension mismatch"))

    assert isinstance(mapped, ServiceError)
    assert mapped.detail == "FAISS dimension mismatch"
    assert mapped.error_code == "internal_error"


def test_map_exception_preserves_existing_service_error_detail() -> None:
    original = ServiceError(
        detail="Embedding API error: 502",
        error_code="embedding_api_error",
        status_code=502,
    )

    mapped = _map_exception(original)

    assert isinstance(mapped, ServiceError)
    assert mapped.detail == "Embedding API error: 502"
