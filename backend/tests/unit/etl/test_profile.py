"""Unit tests for ETL document profile loading."""

import pytest

from etl.profile import build_faq_pair_regex, get_document_profile, load_document_profile_from_paths
from etl.types import ContentType

from tests.paths import BACKEND_ROOT


def test_get_document_profile_loads_ru_and_en() -> None:
    """
    Both supported KB languages should load compiled profiles.
    """

    ru = get_document_profile("ru", str(BACKEND_ROOT))
    en = get_document_profile("en", str(BACKEND_ROOT))

    assert ru.locale == "ru"
    assert en.locale == "en"
    assert ru.labels.section == "Раздел"
    assert en.labels.section == "Section"


def test_profile_section_map_classifies_special_chapters() -> None:
    """
    Section map should classify meta, FAQ, glossary, trees, and scenarios.
    """

    profile = get_document_profile("ru", str(BACKEND_ROOT))

    assert profile.section_map["00"] == ContentType.META
    assert profile.section_map["14"] == ContentType.FAQ
    assert profile.section_map["16"] == ContentType.DECISION_TREE
    assert ContentType.GLOSSARY in profile.skip_index_types


def test_profile_faq_regex_extracts_english_pairs() -> None:
    """
    English FAQ markers should be recognized by the compiled profile regex.
    """

    profile = get_document_profile("en", str(BACKEND_ROOT))
    text = (
        "* **Question:** What is PRM?\n"
        "  **Answer:** Passengers with reduced mobility.\n\n"
        "* **Question:** What is UMNR?\n"
        "  **Answer:** Unaccompanied minor service.\n"
    )
    matches = list(profile.faq_pair_re.finditer(text))

    assert len(matches) == 2
    assert matches[0].group("question").strip() == "What is PRM?"
    assert matches[1].group("answer").strip() == "Unaccompanied minor service."


def test_load_document_profile_rejects_missing_locale_file() -> None:
    """
    Loading should fail when the locale profile file does not exist.
    """

    with pytest.raises(FileNotFoundError):
        load_document_profile_from_paths(
            base_path=BACKEND_ROOT / "data" / "kb-profile-base.json",
            locale_path=BACKEND_ROOT / "data" / "kb-profile-de.json",
        )


def test_build_faq_pair_regex_supports_list_marker_variant() -> None:
    """
    FAQ regex should match list-style markdown pairs.
    """

    pattern = build_faq_pair_regex("**Вопрос:**", "**Ответ:**")
    text = "* **Вопрос:** Как найти выход?\n  **Ответ:** Смотрите табло.\n"
    match = pattern.search(text)

    assert match is not None
    assert match.group("question").strip() == "Как найти выход?"
