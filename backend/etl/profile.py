"""Load and compile per-language ETL document profiles from JSON."""

import json
import re

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from etl.types import ContentType

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_BASE_PROFILE_PATH = _BACKEND_ROOT / "data" / "kb-profile-base.json"


class FaqPairMarkers(BaseModel):
    """
    Markdown markers that delimit one FAQ question/answer pair.
    """

    question_marker: str = Field(description="Literal prefix before the question text, e.g. **Вопрос:**")
    answer_marker: str = Field(description="Literal prefix before the answer text, e.g. **Ответ:**")


class LocaleLabels(BaseModel):
    """
    Retrieval-prefix labels embedded into chunk text for a KB language.
    """

    section: str
    type: str
    source: str
    context: str
    question: str
    answer: str


class SectionKeywordRule(BaseModel):
    """
    Fallback H1 classification when section number is not in section_map.
    """

    content_type: str
    keywords: list[str]


class SopChunkingConfig(BaseModel):
    """
    Token-based splitting rules for SOP sections.
    """

    max_tokens: int = 800
    chars_per_token: int = 4


class DecisionTreeChunkingConfig(BaseModel):
    """
    Regex that matches each decision-tree H2 heading inside chapter 16.
    """

    split_heading_regex: str


class EmbeddedFaqChunkingConfig(BaseModel):
    """
    Regex that locates a trailing FAQ block inside an SOP chapter.
    """

    block_regex: str


class ChunkingConfig(BaseModel):
    """
    Per-content-type chunking parameters shared across KB languages.
    """

    sop: SopChunkingConfig = Field(default_factory=SopChunkingConfig)
    decision_tree: DecisionTreeChunkingConfig
    embedded_faq: EmbeddedFaqChunkingConfig


class DocumentProfileData(BaseModel):
    """
    Validated document profile after merging base and locale JSON files.
    """

    schema_version: int = 1
    locale: str
    section_map: dict[str, str]
    section_keywords: list[SectionKeywordRule] = Field(default_factory=list)
    skip_index_types: list[str]
    static_prompt_sections: list[str]
    labels: LocaleLabels
    faq_pair: FaqPairMarkers
    scenario_split_regex: str
    chunking: ChunkingConfig


@dataclass(frozen=True, slots=True)
class DocumentProfile:
    """
    Runtime profile with compiled regex patterns for parser and chunker.
    """

    locale: str
    section_map: dict[str, ContentType]
    section_keywords: tuple[tuple[ContentType, tuple[str, ...]], ...]
    skip_index_types: frozenset[ContentType]
    static_prompt_sections: frozenset[str]
    labels: LocaleLabels
    max_sop_tokens: int
    chars_per_token: int
    faq_question_marker: str
    faq_answer_marker: str
    faq_pair_re: re.Pattern[str]
    embedded_faq_block_re: re.Pattern[str]
    scenario_split_re: re.Pattern[str]
    decision_tree_split_re: re.Pattern[str]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge override dict into base (override wins on conflicts).
    """

    merged = dict(base)

    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def _content_type(value: str) -> ContentType:
    """
    Parse a content-type string from profile JSON into the enum.
    """

    return ContentType(value)


def build_faq_pair_regex(question_marker: str, answer_marker: str) -> re.Pattern[str]:
    """
    Build a regex that extracts FAQ pairs from markdown using literal Q/A markers.
    """

    question = re.escape(question_marker)
    answer = re.escape(answer_marker)
    pattern = (
        rf"(?:^|\n)\s*(?:\*\s+)?{question}\s*(?P<question>.+?)\s*\n"
        rf"\s*(?:\*\s+)?{answer}\s*(?P<answer>.+?)"
        rf"(?=\n\s*(?:\*\s+)?{question}|\Z)"
    )

    return re.compile(pattern, re.DOTALL)


def compile_document_profile(data: DocumentProfileData) -> DocumentProfile:
    """
    Compile regex patterns and enums from validated profile data.
    """

    section_map = {number: _content_type(content_type) for number, content_type in data.section_map.items()}
    section_keywords = tuple(
        (_content_type(rule.content_type), tuple(rule.keywords)) for rule in data.section_keywords
    )
    skip_index_types = frozenset(_content_type(content_type) for content_type in data.skip_index_types)

    return DocumentProfile(
        locale=data.locale,
        section_map=section_map,
        section_keywords=section_keywords,
        skip_index_types=skip_index_types,
        static_prompt_sections=frozenset(data.static_prompt_sections),
        labels=data.labels,
        max_sop_tokens=data.chunking.sop.max_tokens,
        chars_per_token=data.chunking.sop.chars_per_token,
        faq_question_marker=data.faq_pair.question_marker,
        faq_answer_marker=data.faq_pair.answer_marker,
        faq_pair_re=build_faq_pair_regex(data.faq_pair.question_marker, data.faq_pair.answer_marker),
        embedded_faq_block_re=re.compile(data.chunking.embedded_faq.block_regex, re.MULTILINE),
        scenario_split_re=re.compile(data.scenario_split_regex, re.MULTILINE),
        decision_tree_split_re=re.compile(data.chunking.decision_tree.split_heading_regex, re.MULTILINE),
    )


def load_document_profile_from_paths(
    *,
    base_path: Path,
    locale_path: Path,
) -> DocumentProfile:
    """
    Load base + locale JSON files, merge them, validate, and compile patterns.
    """

    base_payload = json.loads(base_path.read_text(encoding="utf-8"))
    locale_payload = json.loads(locale_path.read_text(encoding="utf-8"))
    merged = _deep_merge(base_payload, locale_payload)
    data = DocumentProfileData.model_validate(merged)

    return compile_document_profile(data)


def resolve_kb_profile_locale_path(language_code: str, backend_root: Path) -> Path:
    """
    Return the locale-specific profile path for a KB language code.
    """

    return backend_root / "data" / f"kb-profile-{language_code}.json"


@lru_cache(maxsize=8)
def get_document_profile(language_code: str, backend_root: str | None = None) -> DocumentProfile:
    """
    Load and cache the compiled document profile for a knowledge-base language.
    """

    root = Path(backend_root) if backend_root is not None else _BACKEND_ROOT
    base_path = root / "data" / "kb-profile-base.json"
    locale_path = resolve_kb_profile_locale_path(language_code, root)

    if not base_path.is_file():
        raise FileNotFoundError(f"KB profile base file not found: {base_path}")

    if not locale_path.is_file():
        raise FileNotFoundError(f"KB profile locale file not found: {locale_path}")

    return load_document_profile_from_paths(base_path=base_path, locale_path=locale_path)
