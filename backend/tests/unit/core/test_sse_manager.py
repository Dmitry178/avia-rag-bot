"""Unit tests for in-memory SSE pub/sub."""

import asyncio
import pytest

from app.core.sse_manager import SSEManager


@pytest.mark.asyncio
async def test_publish_delivers_to_matching_client() -> None:
    manager = SSEManager()
    queue = await manager.subscribe("client-a")

    await manager.publish("client-a", "chat_title", {"chat_id": 1, "title": "Flood concerns"})

    payload = await asyncio.wait_for(queue.get(), timeout=1)

    assert payload == {
        "event": "chat_title",
        "data": {"chat_id": 1, "title": "Flood concerns"},
    }


@pytest.mark.asyncio
async def test_publish_chat_title_broadcasts_when_client_has_no_subscriber() -> None:
    manager = SSEManager()
    queue = await manager.subscribe("client-b")

    await manager.publish("client-a", "chat_title", {"chat_id": 2, "title": "Flood concerns"})

    payload = await asyncio.wait_for(queue.get(), timeout=1)

    assert payload == {
        "event": "chat_title",
        "data": {"chat_id": 2, "title": "Flood concerns"},
    }


@pytest.mark.asyncio
async def test_publish_non_title_event_does_not_broadcast() -> None:
    manager = SSEManager()
    queue = await manager.subscribe("client-b")

    await manager.publish("client-a", "error", {"message": "boom"})

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue.get(), timeout=0.05)
