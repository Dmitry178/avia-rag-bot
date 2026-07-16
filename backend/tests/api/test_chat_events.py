"""Chat SSE API tests."""

import pytest

from httpx import AsyncClient
from sse_starlette.sse import EventSourceResponse

from app.api.routers.chat import chat_events


@pytest.mark.asyncio
async def test_chat_events_requires_client_id(client: AsyncClient) -> None:
    """
    SSE endpoint should reject requests without client_id.
    """

    response = await client.get("/api/chats/events")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_events_rejects_empty_client_id(client: AsyncClient) -> None:
    """
    SSE endpoint should reject blank client_id values.
    """

    response = await client.get("/api/chats/events", params={"client_id": ""})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_events_handler_returns_event_source_response() -> None:
    """
    SSE route handler should wrap the subscription generator in EventSourceResponse.
    """

    response = await chat_events(client_id="api-sse-handler-test")

    assert isinstance(response, EventSourceResponse)

