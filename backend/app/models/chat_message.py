"""Chat message SQLModel table."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class MessageRole(StrEnum):
    """
    Author role for a chat message.
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(SQLModel, table=True):
    """
    One message in a chat thread (user, assistant, or system).
    """

    __tablename__ = "chat_message"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="Surrogate primary key.",
    )
    chat_id: int = Field(
        foreign_key="chat.id",
        description="Parent chat id.",
    )
    role: str = Field(
        description="Message author role: user, assistant, or system.",
    )
    content: str = Field(
        description="Plain-text message body.",
    )
    rating: int | None = Field(
        default=None,
        description="User rating of an assistant reply (1–5); null if not rated.",
    )
    rating_comment: str | None = Field(
        default=None,
        description="Optional free-text comment accompanying the rating.",
    )
    message_metadata: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
        description="JSON metadata: model, token counts, latency_ms, requested_at, etc.",
    )
    is_deleted: bool = Field(
        default=False,
        description="Soft-delete flag; hidden from history.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the message was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the last edit or rating change.",
    )
