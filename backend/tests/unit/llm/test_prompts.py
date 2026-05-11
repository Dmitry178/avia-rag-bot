"""Unit tests for system prompt helpers."""

from app.llm.prompts import build_system_prompt


def test_build_system_prompt_adds_russian_language_hint() -> None:
    prompt = build_system_prompt(reply_language="ru")

    assert "Reply entirely in Russian" in prompt
    assert "do not use English" in prompt


def test_build_system_prompt_adds_english_language_hint() -> None:
    prompt = build_system_prompt(reply_language="en")

    assert "Reply entirely in English" in prompt


def test_build_system_prompt_without_language_returns_base() -> None:
    base = build_system_prompt()
    with_hint = build_system_prompt(reply_language="ru")

    assert "Reply entirely in Russian" not in base
    assert len(with_hint) > len(base)
