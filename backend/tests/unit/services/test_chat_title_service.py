"""Unit tests for background chat title persistence."""

import pytest

from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.core.db_manager import DBManager
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.chat import ChatType
from app.services.chat_title import _generate_and_persist


@pytest.fixture(autouse=True)
async def _init_database() -> None:
    await init_db()


@pytest.mark.asyncio
async def test_generate_and_persist_updates_title_in_db() -> None:
    async with DBManager(SessionLocal) as db:
        chat = await db.chat.chats.create(title="New chat", chat_type=ChatType.LLM)
        chat_id = chat.id
        await db.commit()

    with patch(
        "app.services.chat_title.generate_chat_title",
        new_callable=AsyncMock,
        return_value="Treasury payout",
    ):
        await _generate_and_persist(
            chat_id=chat_id,
            client_id=None,
            user_message="Issue 1000 coins",
            chat_type=ChatType.LLM,
            custom_system_prompt=None,
            app_settings=settings,
        )

    async with DBManager(SessionLocal) as db:
        chat = await db.chat.chats.get_by_id(chat_id)
        assert chat is not None
        assert chat.title == "Treasury payout"


@pytest.mark.asyncio
async def test_generate_and_persist_skips_deleted_chat() -> None:
    async with DBManager(SessionLocal) as db:
        chat = await db.chat.chats.create(title="New chat", chat_type=ChatType.LLM)
        chat_id = chat.id
        await db.chat.chats.soft_delete(chat_id)
        await db.commit()

    with patch(
        "app.services.chat_title.generate_chat_title",
        new_callable=AsyncMock,
        return_value="Should not apply",
    ) as generate_mock:
        await _generate_and_persist(
            chat_id=chat_id,
            client_id=None,
            user_message="Hello",
            chat_type=ChatType.LLM,
            custom_system_prompt=None,
            app_settings=settings,
        )

    generate_mock.assert_awaited_once()

    async with DBManager(SessionLocal) as db:
        chat = await db.chat.chats.get_by_id(chat_id)
        assert chat is None


@pytest.mark.asyncio
async def test_generate_and_persist_skips_non_default_title() -> None:
    async with DBManager(SessionLocal) as db:
        chat = await db.chat.chats.create(title="Custom title", chat_type=ChatType.LLM)
        chat_id = chat.id
        await db.commit()

    with patch(
        "app.services.chat_title.generate_chat_title",
        new_callable=AsyncMock,
        return_value="Generated title",
    ):
        await _generate_and_persist(
            chat_id=chat_id,
            client_id=None,
            user_message="Hello",
            chat_type=ChatType.LLM,
            custom_system_prompt=None,
            app_settings=settings,
        )

    async with DBManager(SessionLocal) as db:
        chat = await db.chat.chats.get_by_id(chat_id)
        assert chat is not None
        assert chat.title == "Custom title"


@pytest.mark.asyncio
async def test_generate_and_persist_publishes_sse_on_generation_failure() -> None:
    async with DBManager(SessionLocal) as db:
        chat = await db.chat.chats.create(title="New chat", chat_type=ChatType.LLM)
        chat_id = chat.id
        await db.commit()

    with (
        patch(
            "app.services.chat_title.generate_chat_title",
            new_callable=AsyncMock,
            side_effect=RuntimeError("model does not support tool use"),
        ),
        patch("app.services.chat_title.sse_manager.publish", new_callable=AsyncMock) as publish_mock,
    ):
        await _generate_and_persist(
            chat_id=chat_id,
            client_id="test-client",
            user_message="Hello",
            chat_type=ChatType.LLM,
            custom_system_prompt=None,
            app_settings=settings,
        )

    publish_mock.assert_awaited_once()
    assert publish_mock.await_args.args[0] == "test-client"
    assert publish_mock.await_args.args[1] == "error"
    assert publish_mock.await_args.args[2]["error_code"] == "chat_title_error"
    assert "tool use" in publish_mock.await_args.args[2]["message"]
