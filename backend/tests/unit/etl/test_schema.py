"""Unit tests for schema loading and FAQ helpers."""

from etl.chunking_schema import load_runtime_schema_for_language
from etl.faq_regex import build_faq_pair_regex

from tests.paths import BACKEND_ROOT


def test_runtime_schema_loads_ru_and_en() -> None:
    """
    Both supported KB languages should load schema v3 runtime config.
    """

    ru = load_runtime_schema_for_language("ru", str(BACKEND_ROOT)).schema
    en = load_runtime_schema_for_language("en", str(BACKEND_ROOT)).schema

    assert ru.document.language_code == "ru"
    assert en.document.language_code == "en"
    assert any(category.labels.section == "Раздел" for category in ru.categories)
    assert any(category.labels.section == "Section" for category in en.categories)


def test_schema_has_policy_binding_for_each_category() -> None:
    """
    Every declared category should have a policy binding.
    """

    schema = load_runtime_schema_for_language("ru", str(BACKEND_ROOT)).schema
    category_ids = {item.id for item in schema.categories}
    binding_ids = {item.category_id for item in schema.category_policy_bindings}

    assert category_ids == binding_ids


def test_runtime_schema_context_loads_ru() -> None:
    """
    Runtime schema loader should resolve RU schema and expose lane config.
    """

    context = load_runtime_schema_for_language("ru", str(BACKEND_ROOT))

    assert context.schema.document.language_code == "ru"
    assert any(lane.id == "sop" for lane in context.schema.retrieval_lanes)


def test_faq_regex_extracts_english_pairs() -> None:
    """
    English FAQ markers should be recognized by the schema FAQ regex.
    """

    schema = load_runtime_schema_for_language("en", str(BACKEND_ROOT)).schema
    faq_policy_id = next(item.policy_id for item in schema.category_policy_bindings if item.category_id == "faq")
    faq_policy = next(item for item in schema.chunking_policies if item.id == faq_policy_id)
    question_marker = str(faq_policy.params.get("question_marker"))
    answer_marker = str(faq_policy.params.get("answer_marker"))
    pattern = build_faq_pair_regex(question_marker, answer_marker)
    text = (
        "* **Question:** What is PRM?\n"
        "  **Answer:** Passengers with reduced mobility.\n\n"
        "* **Question:** What is UMNR?\n"
        "  **Answer:** Unaccompanied minor service.\n"
    )
    matches = list(pattern.finditer(text))

    assert len(matches) == 2
    assert matches[0].group("question").strip() == "What is PRM?"
    assert matches[1].group("answer").strip() == "Unaccompanied minor service."


def test_build_faq_pair_regex_supports_list_marker_variant() -> None:
    """
    FAQ regex should match list-style markdown pairs.
    """

    pattern = build_faq_pair_regex("**Вопрос:**", "**Ответ:**")
    text = "* **Вопрос:** Как найти выход?\n  **Ответ:** Смотрите табло.\n"
    match = pattern.search(text)

    assert match is not None
    assert match.group("question").strip() == "Как найти выход?"
