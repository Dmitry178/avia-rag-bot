"""Chat API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.chat_message import MessageRole


class ChatSummaryResponse(BaseModel):
    """
    Chat row for the sidebar list.
    """

    id: int
    title: str
    is_closed: bool
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None


class ChatMessageResponse(BaseModel):
    """
    Single message in chat history.
    """

    id: int
    chat_id: int
    role: MessageRole
    content: str
    rating: int | None = None
    rating_comment: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ChatDetailResponse(BaseModel):
    """
    Chat with full non-deleted message history.
    """

    id: int
    title: str
    is_closed: bool
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    messages: list[ChatMessageResponse]


class CreateChatRequest(BaseModel):
    """
    Create a new chat thread.
    """

    title: str = Field(default="New chat", min_length=1, max_length=200)


class SendMessageRequest(BaseModel):
    """
    Send a user message; LLM reply is returned synchronously in the response body.
    """

    content: str = Field(min_length=1)
    client_id: str | None = Field(
        default=None,
        description="Optional SSE client id to receive error sideband events",
    )


class SendMessageResponse(BaseModel):
    """
    User message plus synchronous assistant reply.
    """

    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


class EditMessageRequest(BaseModel):
    """
    Edit an existing user message.
    """

    content: str = Field(min_length=1)


class SetRatingRequest(BaseModel):
    """
    Rate an assistant message.
    """

    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ChatSSEEventData(BaseModel):
    """
    Payload for chat SSE events.
    """

    message: str
    chat_id: int | None = None
    error_code: str | None = None
