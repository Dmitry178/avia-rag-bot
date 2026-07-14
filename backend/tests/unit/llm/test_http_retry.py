"""Unit tests for LLM HTTP retry helpers."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.llm.http_retry import (
    call_with_retry,
    post_with_retry,
    retry_delay_seconds,
)


def test_retry_delay_seconds_honors_retry_after_header() -> None:
    response = httpx.Response(429, headers={"Retry-After": "5"})

    assert retry_delay_seconds(response, attempt=0) == 5.0


def test_retry_delay_seconds_uses_exponential_backoff() -> None:
    assert retry_delay_seconds(None, attempt=0) == 1.0
    assert retry_delay_seconds(None, attempt=1) == 2.0
    assert retry_delay_seconds(None, attempt=2) == 4.0


@pytest.mark.asyncio
async def test_post_with_retry_retries_on_429() -> None:
    client = AsyncMock(spec=httpx.AsyncClient)
    client.post = AsyncMock(
        side_effect=[
            httpx.Response(429, request=httpx.Request("POST", "https://example.com")),
            httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", "https://example.com")),
        ],
    )

    with patch("app.llm.http_retry.asyncio.sleep", new_callable=AsyncMock) as sleep_mock:
        response = await post_with_retry(client, "https://example.com/chat/completions", json={})

    assert response.status_code == 200
    assert client.post.await_count == 2
    sleep_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_with_retry_returns_last_response_when_exhausted() -> None:
    client = AsyncMock(spec=httpx.AsyncClient)
    client.post = AsyncMock(
        return_value=httpx.Response(429, request=httpx.Request("POST", "https://example.com")),
    )

    with patch("app.llm.http_retry.asyncio.sleep", new_callable=AsyncMock):
        response = await post_with_retry(
            client,
            "https://example.com/chat/completions",
            max_attempts=2,
            json={},
        )

    assert response.status_code == 429
    assert client.post.await_count == 2


@pytest.mark.asyncio
async def test_call_with_retry_retries_retryable_errors() -> None:
    operation = AsyncMock(side_effect=[RuntimeError("429"), "ok"])

    with patch("app.llm.http_retry.asyncio.sleep", new_callable=AsyncMock) as sleep_mock:
        result = await call_with_retry(
            operation,
            is_retryable=lambda exc: isinstance(exc, RuntimeError),
            operation_name="test_op",
        )

    assert result == "ok"
    assert operation.await_count == 2
    sleep_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_call_with_retry_reraises_non_retryable_errors() -> None:
    operation = AsyncMock(side_effect=ValueError("bad request"))

    with patch("app.llm.http_retry.asyncio.sleep", new_callable=AsyncMock) as sleep_mock:
        with pytest.raises(ValueError, match="bad request"):
            await call_with_retry(
                operation,
                is_retryable=lambda _exc: False,
                operation_name="test_op",
            )

    assert operation.await_count == 1
    sleep_mock.assert_not_awaited()
