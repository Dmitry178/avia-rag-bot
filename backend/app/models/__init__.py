"""SQLModel table definitions."""

from app.models.chat import Chat
from app.models.chat_message import ChatMessage

__all__ = [
    "Chat",
    "ChatMessage",
]
