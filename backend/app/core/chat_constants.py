"""Shared chat defaults used by API and title generation."""

DEFAULT_CHAT_TITLE = "New chat"

# Titles sent by the frontend for freshly created chats (i18n).
DEFAULT_CHAT_TITLES = frozenset({DEFAULT_CHAT_TITLE, "Новый чат"})

MAX_CHAT_TITLE_LENGTH = 48


def is_default_chat_title(title: str) -> bool:
    """
    Return True when the chat still has an auto-generated placeholder title.
    """

    return title.strip() in DEFAULT_CHAT_TITLES
