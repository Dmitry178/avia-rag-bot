"""Background chat title generation after the first user message."""

import asyncio

from app.core.chat_constants import is_default_chat_title
from app.core.config import Settings, settings
from app.core.db_manager import DBManager
from app.core.logs import logger
from app.core.sse_manager import sse_manager
from app.db.session import SessionLocal
from app.llm.chat_title import generate_chat_title
from app.models.chat import ChatType

_background_tasks: set[asyncio.Task[None]] = set()


def schedule_chat_title_generation(
    *,
    chat_id: int,
    client_id: str | None,
    user_message: str,
    chat_type: ChatType,
    custom_system_prompt: str | None,
    app_settings: Settings | None = None,
) -> None:
    """
    Fire-and-forget title generation; safe when the chat is deleted mid-flight.
    """

    task = asyncio.create_task(
        _generate_and_persist(
            chat_id=chat_id,
            client_id=client_id,
            user_message=user_message,
            chat_type=chat_type,
            custom_system_prompt=custom_system_prompt,
            app_settings=app_settings or settings,
        ),
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _generate_and_persist(
    *,
    chat_id: int,
    client_id: str | None,
    user_message: str,
    chat_type: ChatType,
    custom_system_prompt: str | None,
    app_settings: Settings,
) -> None:
    try:
        title = await generate_chat_title(
            app_settings.llm,
            user_message=user_message,
            chat_type=chat_type,
            custom_system_prompt=custom_system_prompt,
        )
    except Exception as exc:
        logger.warning(
            "chat_title_generation_failed",
            chat_id=chat_id,
            error=str(exc),
        )
        if client_id:
            await sse_manager.publish(
                client_id,
                "error",
                {
                    "message": str(exc),
                    "chat_id": chat_id,
                    "error_code": "chat_title_error",
                },
            )
        return

    try:
        async with DBManager(SessionLocal) as db:
            chat = await db.chat.chats.get_by_id(chat_id)
            if chat is None:
                return

            if not is_default_chat_title(chat.title):
                return

            updated = await db.chat.chats.update_title(chat_id, title)
            if updated is None:
                return

            await db.commit()
    except Exception as exc:
        logger.warning(
            "chat_title_persist_failed",
            chat_id=chat_id,
            error=str(exc),
        )
        return

    if client_id:
        await sse_manager.publish(
            client_id,
            "chat_title",
            {"chat_id": chat_id, "title": title},
        )

    logger.info("chat_title_generated", chat_id=chat_id, title=title)
