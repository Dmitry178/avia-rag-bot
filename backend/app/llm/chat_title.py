"""pydantic-ai agent that summarizes the first user message into a sidebar title."""

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.chat_constants import MAX_CHAT_TITLE_LENGTH
from app.core.config import LLMSettings
from app.llm.http_retry import call_with_retry, is_retryable_http_status
from app.llm.prompt_guard import reply_language_for_user_text
from app.models.chat import ChatType

_LANGUAGE_RULE = (
    "The title MUST use exactly the same language as the user's message — never translate. "
    "English message → English title; Russian message → Russian title."
)

_TITLE_LANGUAGE_HINTS: dict[str, str] = {
    "ru": (
        "The user's message is in Russian. Write the title entirely in Russian. "
        "Do not use English or any other language."
    ),
    "en": (
        "The user's message is in English. Write the title entirely in English. "
        "Do not use Russian or any other language."
    ),
}

_TITLE_INSTRUCTIONS = (
    "You generate very short chat titles for a sidebar list. "
    f"Maximum {MAX_CHAT_TITLE_LENGTH} characters. "
    f"{_LANGUAGE_RULE} "
    "Reuse key words from the user's message; do not paraphrase into another language. "
    "If the message is already short, keep the title close to the original wording. "
    "No quotes, no markdown, no trailing punctuation, no labels like 'Title:'. "
    "Always output a non-empty title. Reply with the title text only — no explanation."
)


def _title_language_hint(reply_language: str | None) -> str:
    if reply_language is None or reply_language not in _TITLE_LANGUAGE_HINTS:
        return ""

    return f" {_TITLE_LANGUAGE_HINTS[reply_language]}"


def resolve_summarization_model(settings: LLMSettings) -> str:
    model = settings.summarization_model or settings.model
    if not model:
        raise ValueError("LLM summarization model is not configured")

    return model


def _build_title_agent(settings: LLMSettings, *, reply_language: str | None = None) -> Agent:
    if not settings.base_url:
        raise ValueError("LLM is not configured")

    model_name = resolve_summarization_model(settings)
    provider = OpenAIProvider(
        base_url=settings.base_url.rstrip("/"),
        api_key=settings.api_key or "not-needed",
    )
    model = OpenAIChatModel(model_name, provider=provider)

    instructions = f"{_TITLE_INSTRUCTIONS}{_title_language_hint(reply_language)}"

    return Agent(model=model, instructions=instructions)


def normalize_chat_title(title: str, *, max_length: int = MAX_CHAT_TITLE_LENGTH) -> str:
    """
    Collapse whitespace and trim to sidebar-friendly length.
    """

    cleaned = " ".join(title.strip().split())

    if len(cleaned) <= max_length:
        return cleaned

    truncated = cleaned[: max_length - 1].rstrip()

    return f"{truncated}…"


def parse_chat_title_response(text: str) -> str:
    """
    Normalize a plain-text model reply into a sidebar title.
    """

    raw_lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not raw_lines:
        raise ValueError("Empty chat title response")

    first_line = " ".join(raw_lines[0].split())
    if first_line.startswith("#"):
        first_line = first_line.lstrip("#").strip()

    if len(first_line) >= 2 and first_line[0] in "\"'" and first_line[-1] == first_line[0]:
        first_line = first_line[1:-1].strip()

    first_line = first_line.rstrip(".,;:!?")

    if not first_line:
        raise ValueError("Empty chat title response")

    return normalize_chat_title(first_line)


def build_title_user_prompt(
    *,
    user_message: str,
    chat_type: ChatType,
    custom_system_prompt: str | None = None,
    reply_language: str | None = None,
) -> str:
    """
    Build the user prompt for title generation.

    RAG chats and LLM chats with the built-in system prompt use only the question.
    LLM chats with a custom system prompt may use that prompt as extra context.
    """

    message = user_message.strip()
    language_hint = _title_language_hint(reply_language)
    title_task = (
        f"Create a short sidebar title for the user's first message.{language_hint}\n"
        f"{_LANGUAGE_RULE}"
    )

    if chat_type == ChatType.LLM and custom_system_prompt:
        return (
            "The user configured this system prompt for the chat:\n"
            "---\n"
            f"{custom_system_prompt.strip()}\n"
            "---\n\n"
            "Given that context and the user's first message below, "
            f"create a short sidebar title.{language_hint}\n"
            f"{_LANGUAGE_RULE}\n\n"
            f"User message:\n{message}"
        )

    return f"{title_task}\n\nUser message:\n{message}"


async def generate_chat_title(
    settings: LLMSettings,
    *,
    user_message: str,
    chat_type: ChatType,
    custom_system_prompt: str | None = None,
) -> str:
    """
    Call the title agent and return a normalized sidebar title.
    """

    reply_language = reply_language_for_user_text(user_message)
    agent = _build_title_agent(settings, reply_language=reply_language)
    prompt = build_title_user_prompt(
        user_message=user_message,
        chat_type=chat_type,
        custom_system_prompt=custom_system_prompt,
        reply_language=reply_language,
    )
    result = await call_with_retry(
        lambda: agent.run(prompt),
        is_retryable=lambda exc: isinstance(exc, ModelHTTPError)
        and is_retryable_http_status(exc.status_code),
        operation_name="generate_chat_title",
    )

    return parse_chat_title_response(str(result.output))
