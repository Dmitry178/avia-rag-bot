"""Unit tests for chat title generation helpers."""

from app.core.chat_constants import is_default_chat_title
from app.llm.chat_title import (
    resolve_summarization_model,
    build_title_user_prompt,
    normalize_chat_title,
    parse_chat_title_response,
)
from app.models.chat import ChatType


def test_is_default_chat_title() -> None:
    assert is_default_chat_title("New chat")
    assert is_default_chat_title("Новый чат")
    assert not is_default_chat_title("Budget request")


def test_normalize_chat_title_truncates_long_text() -> None:
    long_title = "x" * 60

    normalized = normalize_chat_title(long_title, max_length=48)

    assert len(normalized) <= 48
    assert normalized.endswith("…")


def test_build_title_user_prompt_rag_uses_question_only() -> None:
    prompt = build_title_user_prompt(
        user_message="Where is baggage claim?",
        chat_type=ChatType.RAG,
        custom_system_prompt="You are a pirate.",
    )

    assert "baggage claim" in prompt
    assert "pirate" not in prompt
    assert "same language" in prompt.lower()


def test_build_title_user_prompt_llm_custom_includes_system_prompt() -> None:
    prompt = build_title_user_prompt(
        user_message="Issue 1000 coins to the army",
        chat_type=ChatType.LLM,
        custom_system_prompt="You are the royal treasurer.",
    )

    assert "royal treasurer" in prompt
    assert "1000 coins" in prompt
    assert "same language" in prompt.lower()


def test_build_title_user_prompt_llm_builtin_uses_question_only() -> None:
    prompt = build_title_user_prompt(
        user_message="Hello",
        chat_type=ChatType.LLM,
        custom_system_prompt=None,
    )

    assert "Hello" in prompt
    assert "system prompt" not in prompt.lower()


def test_resolve_summarization_model_prefers_dedicated_setting() -> None:
    from app.core.config import LLMSettings

    settings = LLMSettings(
        model="main-model",
        summarization_model="summary-model",
    )

    assert resolve_summarization_model(settings) == "summary-model"


def test_resolve_summarization_model_falls_back_to_main_model() -> None:
    from app.core.config import LLMSettings

    settings = LLMSettings(model="main-model")

    assert resolve_summarization_model(settings) == "main-model"


def test_parse_chat_title_response_strips_quotes_and_first_line() -> None:
    assert parse_chat_title_response('"Treasury payout"\nExtra text') == "Treasury payout"
    assert parse_chat_title_response("# Baggage rules") == "Baggage rules"
    assert parse_chat_title_response("Army funding request.") == "Army funding request"
