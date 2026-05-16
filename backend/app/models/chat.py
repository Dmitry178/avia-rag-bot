"""Chat (conversation) SQLModel table."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class ChatType(StrEnum):
    """
    Chat pipeline mode: plain LLM or RAG.
    """

    LLM = "llm"
    RAG = "rag"


class Chat(SQLModel, table=True):
    """
    A single user conversation thread in the chat sidebar.
    """

    __tablename__ = "chat"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="Surrogate primary key.",
    )
    title: str = Field(
        default="New chat",
        description="Display title in the chat list (may be auto-generated later).",
    )
    chat_type: str = Field(
        default=ChatType.LLM.value,
        description="Chat pipeline mode: llm (plain LLM) or rag (RAG assistant).",
    )
    is_closed: bool = Field(
        default=False,
        description="When true, no new messages can be sent to this chat.",
    )
    is_deleted: bool = Field(
        default=False,
        description="Soft-delete flag; hidden from list and detail endpoints.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the chat was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the last message or metadata change.",
    )
    closed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the chat was closed; null while open.",
    )
    message_count: int = Field(
        default=0,
        description="Number of non-deleted messages in the chat (denormalized for list UI).",
    )
    rag_config: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Last RAG pipeline toggles for this chat; null for LLM chats or unset.",
    )
    use_history: bool | None = Field(
        default=None,
        description="Whether to include chat history in context; null until configured.",
    )
    llm_config: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="LLM mode settings (custom prompt toggles); null for RAG chats or unset.",
    )
