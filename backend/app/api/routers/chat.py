"""Chat API routes."""

import json

from collections.abc import AsyncIterator
from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from app.core.db_manager import DBManager
from app.db.deps import get_db
from app.core.sse_manager import sse_manager
from app.schemas.chat import (
    ChatDetailResponse,
    ChatMessageResponse,
    ChatSummaryResponse,
    CreateChatRequest,
    EditMessageRequest,
    SendMessageRequest,
    SendMessageResponse,
    SetRatingRequest,
)
from app.services.chat import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get(
    "/events",
    summary="Chat SSE stream",
    description="Subscribe to sideband chat events (errors). Pass the same client_id as in POST /messages.",
)
async def chat_events(client_id: str = Query(..., min_length=1)) -> EventSourceResponse:
    """
    SSE stream for chat error notifications and future async events.
    """

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        async with sse_manager.subscription(client_id) as queue:
            while True:
                payload = await queue.get()
                yield {
                    "event": payload["event"],
                    "data": json.dumps(payload["data"], ensure_ascii=False),
                }

    return EventSourceResponse(event_generator())


@router.get(
    "",
    summary="List chats",
    description="Return all non-deleted chats ordered by last activity.",
    response_model=list[ChatSummaryResponse],
)
async def list_chats(db: DBManager = Depends(get_db)) -> list[ChatSummaryResponse]:
    """
    List chat threads for the sidebar.
    """

    return await ChatService(db).list_chats()


@router.post(
    "",
    summary="Create chat",
    description="Create a new empty chat thread.",
    response_model=ChatSummaryResponse,
)
async def create_chat(
    body: CreateChatRequest,
    db: DBManager = Depends(get_db),
) -> ChatSummaryResponse:
    """
    Create a new chat.
    """

    return await ChatService(db).create_chat(body)


@router.get(
    "/{chat_id}",
    summary="Get chat",
    description="Return chat metadata and non-deleted message history.",
    response_model=ChatDetailResponse,
)
async def get_chat(chat_id: int, db: DBManager = Depends(get_db)) -> ChatDetailResponse:
    """
    Get chat with messages.
    """

    return await ChatService(db).get_chat(chat_id)


@router.delete(
    "/{chat_id}",
    summary="Delete chat",
    description="Soft-delete a chat (is_deleted=true).",
    status_code=204,
)
async def delete_chat(chat_id: int, db: DBManager = Depends(get_db)) -> None:
    """
    Soft-delete chat.
    """

    await ChatService(db).delete_chat(chat_id)


@router.post(
    "/{chat_id}/close",
    summary="Close chat",
    description="Mark chat as closed; no new messages allowed.",
    response_model=ChatSummaryResponse,
)
async def close_chat(chat_id: int, db: DBManager = Depends(get_db)) -> ChatSummaryResponse:
    """
    Close chat thread.
    """

    return await ChatService(db).close_chat(chat_id)


@router.post(
    "/{chat_id}/messages",
    summary="Send message",
    description="Send user message and receive synchronous LLM reply in response body.",
    response_model=SendMessageResponse,
)
async def send_message(
    chat_id: int,
    body: SendMessageRequest,
    db: DBManager = Depends(get_db),
) -> SendMessageResponse:
    """
    Send a message and get assistant reply (non-streaming).
    """

    return await ChatService(db).send_message(chat_id, body)


@router.patch(
    "/{chat_id}/messages/{message_id}",
    summary="Edit message",
    description="Edit a user message body.",
    response_model=ChatMessageResponse,
)
async def edit_message(
    chat_id: int,
    message_id: int,
    body: EditMessageRequest,
    db: DBManager = Depends(get_db),
) -> ChatMessageResponse:
    """
    Edit user message.
    """

    return await ChatService(db).edit_message(chat_id, message_id, body)


@router.post(
    "/{chat_id}/messages/{message_id}/rating",
    summary="Rate message",
    description="Set rating (1–5) and/or comment on an assistant message.",
    response_model=ChatMessageResponse,
)
async def rate_message(
    chat_id: int,
    message_id: int,
    body: SetRatingRequest,
    db: DBManager = Depends(get_db),
) -> ChatMessageResponse:
    """
    Rate assistant reply.
    """

    return await ChatService(db).set_rating(chat_id, message_id, body)


@router.delete(
    "/{chat_id}/messages/{message_id}",
    summary="Delete message",
    description="Soft-delete a message (is_deleted=true).",
    status_code=204,
)
async def delete_message(
    chat_id: int,
    message_id: int,
    db: DBManager = Depends(get_db),
) -> None:
    """
    Soft-delete message.
    """

    await ChatService(db).delete_message(chat_id, message_id)
