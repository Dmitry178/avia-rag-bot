"""Prompt-injection detection and user-message hardening for LLM calls."""

import re

from enum import StrEnum
from typing import Final

_USER_MESSAGE_START: Final = "<<USER>>"
_USER_MESSAGE_END: Final = "<</USER>>"

_INJECTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?)", re.I),
    re.compile(r"disregard\s+(your\s+)?(instructions?|rules?|guidelines?|system\s+prompt)", re.I),
    re.compile(r"forget\s+(everything|all|your)\s+(instructions?|rules?|guidelines?)", re.I),
    re.compile(r"forget\s+(everything|all)\s+(you\s+)?(were\s+)?told", re.I),
    re.compile(r"forget\s+(the\s+)?(system\s+)?prompt", re.I),
    re.compile(r"(you\s+are\s+now|act\s+as|pretend\s+(to\s+be|you\s+are)|role\s*play\s+as)\b", re.I),
    re.compile(r"(reveal|show|print|repeat|output)\s+(your\s+)?(system\s+)?prompt", re.I),
    re.compile(r"(override|replace|change)\s+(the\s+)?(system\s+)?(prompt|instructions?)", re.I),
    re.compile(r"\b(jailbreak|dan\s+mode|developer\s+mode|god\s+mode|unrestricted\s+mode)\b", re.I),
    re.compile(r"new\s+instructions?\s*:", re.I),
    re.compile(r"<\s*/?\s*(system|instruction|prompt)\s*>", re.I),
    re.compile(r"\[(INST|SYS|SYSTEM)\]", re.I),
    re.compile(
        r"(respond|answer|reply)\s+(without|with\s+no)\s+(restrictions?|limits?|filters?|safety)",
        re.I,
    ),
    re.compile(r"игнорируй\s+(все\s+)?(предыдущие|выше|ранние)\s+(инструкции|правила|указания)", re.I),
    re.compile(r"забудь\s+(все|свои)\s+(инструкции|правила|указания)", re.I),
    re.compile(r"забудь\s+(все\s+|свои\s+|системн\w*\s+)?(промпт|инструкции|правила|указания)", re.I),
    re.compile(r"(ты\s+теперь|действуй\s+как|притворись|представь\s+что\s+ты)\b", re.I),
    re.compile(r"(покажи|выведи|раскрой|повтори)\s+(системный\s+)?промпт", re.I),
    re.compile(r"новые\s+инструкции\s*:", re.I),
)

_COOKING_OR_RECIPE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\b(recipe|рецепт)\b", re.I),
    re.compile(r"\b(how\s+to\s+(cook|make|prepare|bake)|cooking)\b", re.I),
    re.compile(r"(как\s+)?(приготовить|готовить|готовится|сварить|запечь|пожарить)\b", re.I),
    re.compile(
        r"\b(суп|борщ|паста|пицц|куриц\w*|chicken\s+soup|beef\s+stew|pasta|pizza)\b",
        re.I,
    ),
)

_CATERING_REGULATORY_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bHACCP\b", re.I),
    re.compile(r"\b(food\s+safety|shelf\s+life)\b", re.I),
    re.compile(r"(санитарн|гигиен|срок\w*\s+годности|хранени\w*)", re.I),
    re.compile(r"(безопасност\w*\s+питани|бортов\w+\s+питани)", re.I),
    re.compile(r"\b(catering\s+(standard|regulation|requirement)s?)\b", re.I),
    re.compile(r"(правил\w*|требовани\w*|регламент\w*).{0,40}(питани|catering)", re.I),
)

_GENERAL_OFF_TOPIC_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(
        r"\b(write|debug|explain)\s+(me\s+)?(a\s+)?(python|javascript|java|c\+\+)(\s+\w+)?\b",
        re.I,
    ),
    re.compile(r"\b(напиши|создай)\s+(код|скрипт|программу)\b", re.I),
    re.compile(r"\b(write|tell)\s+(me\s+)?(a\s+)?(poem|story|joke)\b", re.I),
    re.compile(r"\b(напиши|расскажи)\s+(стих|историю|анекдот)\b", re.I),
    re.compile(r"\b(homework|курсовую|реферат|эссе)\b", re.I),
)


class BlockReason(StrEnum):
    """
    Why a user message was blocked before the LLM call.
    """

    INJECTION = "prompt_injection"
    OFF_TOPIC = "off_topic"


def sanitize_user_content(content: str) -> str:
    """
    Remove control characters that could confuse parsers or hide injection text.
    """

    cleaned = content.replace("\x00", "")
    cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)

    return cleaned.strip()


def wrap_user_message(content: str) -> str:
    """
    Delimit user content so the model can treat it as data, not instructions.
    """

    sanitized = sanitize_user_content(content)
    return f"{_USER_MESSAGE_START}\n{sanitized}\n{_USER_MESSAGE_END}"


def harden_messages_for_llm(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    Wrap only the latest user message with boundaries before sending to the LLM.

    Historical messages are already stored as plain text; re-wrapping the full
    history on every turn would add unnecessary tokens and latency.
    """

    if not messages:
        return []

    last_user_index = max(
        (index for index, message in enumerate(messages) if message.get("role") == "user"),
        default=-1,
    )

    hardened: list[dict[str, str]] = []

    for index, message in enumerate(messages):
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "user" and index == last_user_index:
            hardened.append({"role": "user", "content": wrap_user_message(content)})
        else:
            hardened.append({"role": role, "content": content})

    return hardened


def _matches_any(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def is_prompt_injection_attempt(text: str) -> bool:
    """
    Return True when the text matches known prompt-injection or jailbreak patterns.
    """

    normalized = sanitize_user_content(text)

    if not normalized:
        return False

    return _matches_any(_INJECTION_PATTERNS, normalized)


def is_off_topic_request(text: str) -> bool:
    """
    Return True when the message is outside aviation scope, including disguised off-topic asks.
    """

    normalized = sanitize_user_content(text)

    if not normalized:
        return False

    if _matches_any(_GENERAL_OFF_TOPIC_PATTERNS, normalized):
        return True

    if _matches_any(_COOKING_OR_RECIPE_PATTERNS, normalized):
        return not _matches_any(_CATERING_REGULATORY_PATTERNS, normalized)

    return False


def evaluate_user_message(text: str) -> BlockReason | None:
    """
    Decide whether a user message should be blocked before calling the LLM.
    """

    if is_prompt_injection_attempt(text):
        return BlockReason.INJECTION

    if is_off_topic_request(text):
        return BlockReason.OFF_TOPIC

    return None


def _contains_cyrillic(text: str) -> bool:
    return any("\u0400" <= char <= "\u04ff" for char in text)


def reply_language_for_user_text(text: str) -> str:
    """
    Infer reply language from the user's message (Russian if Cyrillic is present, else English).
    """

    return "ru" if _contains_cyrillic(text) else "en"


_BLOCKED_REFUSALS: Final[dict[str, str]] = {
    "ru": "Я могу отвечать только на вопросы по авиации.",
    "en": "I can only answer aviation-related questions.",
}


def blocked_refusal(user_text: str) -> str:
    """
    Static assistant reply when a user message is blocked before the LLM call.
    """

    return _BLOCKED_REFUSALS[reply_language_for_user_text(user_text)]
