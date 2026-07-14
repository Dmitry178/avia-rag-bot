"""Retry helpers for OpenAI-compatible HTTP APIs (rate limits, transient errors)."""

import asyncio
import httpx

from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.logs import logger

RETRYABLE_STATUS_CODES = frozenset({429, 503})
DEFAULT_MAX_ATTEMPTS = 4
DEFAULT_BASE_DELAY_SEC = 1.0
DEFAULT_MAX_DELAY_SEC = 30.0
TITLE_GENERATION_INITIAL_DELAY_SEC = 2.0

T = TypeVar("T")


def retry_delay_seconds(response: httpx.Response | None, attempt: int) -> float:
    """
    Compute backoff delay for a retry attempt.

    Honors Retry-After when present; otherwise uses exponential backoff.
    """

    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), DEFAULT_MAX_DELAY_SEC)
            except ValueError:
                pass

    return min(DEFAULT_BASE_DELAY_SEC * (2**attempt), DEFAULT_MAX_DELAY_SEC)


async def post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    **kwargs: object,
) -> httpx.Response:
    """
    POST with retries on HTTP 429/503.
    """

    last_response: httpx.Response | None = None

    for attempt in range(max_attempts):
        response = await client.post(url, **kwargs)  # type: ignore[arg-type]
        last_response = response

        if response.status_code not in RETRYABLE_STATUS_CODES:
            return response

        if attempt == max_attempts - 1:
            return response

        delay = retry_delay_seconds(response, attempt)
        logger.warning(
            "llm_http_retry",
            url=url,
            status_code=response.status_code,
            attempt=attempt + 1,
            max_attempts=max_attempts,
            delay_sec=delay,
        )
        await asyncio.sleep(delay)

    assert last_response is not None
    return last_response


def is_retryable_http_status(status_code: int) -> bool:
    return status_code in RETRYABLE_STATUS_CODES


async def call_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    is_retryable: Callable[[BaseException], bool],
    operation_name: str,
) -> T:
    """
    Retry an async operation when ``is_retryable`` returns True.
    """

    last_error: BaseException | None = None

    for attempt in range(max_attempts):
        try:
            return await operation()
        except BaseException as exc:
            last_error = exc
            if not is_retryable(exc) or attempt == max_attempts - 1:
                raise

            delay = retry_delay_seconds(None, attempt)
            logger.warning(
                "llm_operation_retry",
                operation=operation_name,
                attempt=attempt + 1,
                max_attempts=max_attempts,
                delay_sec=delay,
                error=str(exc),
            )
            await asyncio.sleep(delay)

    assert last_error is not None
    raise last_error
