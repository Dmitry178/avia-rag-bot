"""Chat API integration tests."""

import pytest

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_chats(client: AsyncClient) -> None:
    """
    Created chat should appear in the listing.
    """

    create = await client.post("/api/chats", json={"title": "Test chat"})
    assert create.status_code == 200
    chat_id = create.json()["id"]

    listing = await client.get("/api/chats")
    assert listing.status_code == 200
    ids = [item["id"] for item in listing.json()]
    assert chat_id in ids


@pytest.mark.asyncio
async def test_get_chat_returns_empty_messages(client: AsyncClient) -> None:
    """
    New chat detail should include title and an empty message list.
    """

    create = await client.post("/api/chats", json={"title": "Empty"})
    chat_id = create.json()["id"]

    detail = await client.get(f"/api/chats/{chat_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["title"] == "Empty"
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_soft_delete_chat(client: AsyncClient) -> None:
    """
    Soft-deleted chat should return 404 on subsequent fetch.
    """

    create = await client.post("/api/chats", json={"title": "To delete"})
    chat_id = create.json()["id"]

    deleted = await client.delete(f"/api/chats/{chat_id}")
    assert deleted.status_code == 204

    detail = await client.get(f"/api/chats/{chat_id}")
    assert detail.status_code == 404
