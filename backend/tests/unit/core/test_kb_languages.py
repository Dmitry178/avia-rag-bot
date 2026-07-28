"""Unit tests for hardcoded KB language definitions in config."""

import pytest

from app.core.config import (
    DEFAULT_KB_LANGUAGE,
    get_kb_language,
    list_kb_language_codes,
    resolve_kb_document_path,
    settings,
)
from app.exceptions.service import ServiceError


def test_list_kb_language_codes_returns_ru_and_en() -> None:
    """
    Supported languages should be ru and en in stable order.
    """

    assert list_kb_language_codes() == ["ru", "en"]


def test_get_kb_language_returns_definition() -> None:
    """
    Known language codes should resolve to document paths.
    """

    language = get_kb_language("en")

    assert language.code == "en"
    assert language.document_path.endswith("rag-document-en.md")


def test_get_kb_language_rejects_unknown_code() -> None:
    """
    Unknown language codes should raise a service error.
    """

    with pytest.raises(ServiceError) as exc_info:
        get_kb_language("de")

    assert exc_info.value.error_code == "kb_language_unknown"


def test_resolve_kb_document_path_is_under_backend_root() -> None:
    """
    Relative document paths should resolve against backend root.
    """

    path = resolve_kb_document_path(DEFAULT_KB_LANGUAGE, settings.backend_root)

    assert path == settings.backend_root / "data/rag-document-ru.md"
