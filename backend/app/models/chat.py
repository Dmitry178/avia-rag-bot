"""Chat (conversation) SQLModel table."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


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
