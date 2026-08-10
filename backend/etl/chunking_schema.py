"""Load and validate schema-driven ETL chunking configuration."""

import json

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import resolve_kb_chunking_schema_path
from app.exceptions.service import ServiceError


class HeadingPatterns(BaseModel):
    """
    Regex definitions for markdown headings in source documents.
    """

    h1_regex: str = Field(default=r"^# (?P<title>.+)$")
    h2_regex: str = Field(default=r"^## (?P<title>.+)$")
    h3_regex: str = Field(default=r"^### (?P<title>.+)$")
    section_number_regex: str = Field(default=r"^(\d{2})\.\s*")


class SchemaDocument(BaseModel):
    """
    Input document identity and source path.
    """

    document_id: str
    language_code: str
    display_name: str
    source_path: str
    heading_patterns: HeadingPatterns = Field(default_factory=HeadingPatterns)


class SchemaChunkMetaRoute(BaseModel):
    """
    Optional chunk metadata persistence route.
    """

    kind: Literal["sqlite", "jsonl"] = "jsonl"
    db_path: str | None = None
    table: str | None = None
    language_code: str | None = None


class SchemaProtectedProductionTargets(BaseModel):
    """
    Optional production artifact paths that require an explicit overwrite flag.
    """

    chunk_meta_db_path: str | None = None
    faiss_index_path: str | None = None
    manifest_path: str | None = None
    require_explicit_override: bool = True


class SchemaIo(BaseModel):
    """
    Output artifact routing for schema-driven runs.
    """

    output_root: str
    overwrite_policy: Literal["forbid", "allow"] = "forbid"
    chunk_meta: SchemaChunkMetaRoute | None = None
    faiss_index_path: str = "faiss.index"
    manifest_path: str = "manifest.json"
    chunks_export_path: str = "chunks.jsonl"
    protected_production_targets: SchemaProtectedProductionTargets | None = None


class CategoryLabels(BaseModel):
    """
    Localized labels used in chunk prefixes.
    """

    section: str
    type: str
    source: str
    context: str
    question: str
    answer: str


class SchemaCategory(BaseModel):
    """
    Logical category definition from schema.
    """

    id: str
    description: str
    indexable: bool
    allowed_in_static_prompt: bool = False
    labels: CategoryLabels


class ClassificationMatch(BaseModel):
    """
    Supported category matchers for H1 classification.
    """

    section_number_in: list[str] = Field(default_factory=list)
    title_regex: str | None = None
    title_keywords_any: list[str] = Field(default_factory=list)
    path_regex: str | None = None


class SchemaClassificationRule(BaseModel):
    """
    One classification rule with explicit priority.
    """

    id: str
    priority: int
    target_category_id: str
    match: ClassificationMatch


class ChunkingPolicy(BaseModel):
    """
    Chunking policy definition referenced by category bindings.
    """

    id: str
    strategy: Literal[
        "whole_section",
        "by_subheading",
        "qa_pairs",
        "qa_by_heading_prefix",
        "regex_split",
        "token_window",
    ]
    params: dict[str, object] = Field(default_factory=dict)


class CategoryPolicyBinding(BaseModel):
    """
    Bind a category to one chunking policy.
    """

    category_id: str
    policy_id: str
    extras: dict[str, object] = Field(default_factory=dict)


class StaticPromptSource(BaseModel):
    """
    Source selector for static prompt blocks.
    """

    section_numbers: list[str] = Field(default_factory=list)
    category_ids: list[str] = Field(default_factory=list)


class StaticPromptBlock(BaseModel):
    """
    One static prompt block rendered in order.
    """

    id: str
    title: str
    guidance_text: str
    source: StaticPromptSource


class StaticPromptConfig(BaseModel):
    """
    Static prompt assembly section of schema.
    """

    enabled: bool = True
    blocks: list[StaticPromptBlock] = Field(default_factory=list)


class RetrievalLanePresentation(BaseModel):
    """
    Optional per-lane RAG presentation and verification behavior.
    """

    ui_priority: int = 0
    ui_variant: str | None = None
    exclude_from_generation_context: bool = False
    verification_strategy: Literal["none", "dedicated_llm"] = "none"
    verification_no_match_token: str | None = None
    max_verification_candidates: int = 1


class RetrievalLaneSchema(BaseModel):
    """
    Retrieval lane definition.
    """

    id: str
    description: str
    allowed_category_ids: list[str]
    top_k: int
    oversample: int = 10
    min_fetch: int = 80
    min_similarity: float = 0.4
    presentation: RetrievalLanePresentation | None = None


class ChunkingSchemaV3(BaseModel):
    """
    Top-level schema v3.
    """

    schema_version: int = 3
    chunker_version: int
    document: SchemaDocument
    io: SchemaIo
    categories: list[SchemaCategory]
    default_category_id: str
    classification_rules: list[SchemaClassificationRule]
    chunking_policies: list[ChunkingPolicy]
    category_policy_bindings: list[CategoryPolicyBinding]
    static_prompt: StaticPromptConfig
    retrieval_lanes: list[RetrievalLaneSchema]
    baseline_parity: dict[str, object] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuntimeSchemaContext:
    """
    Runtime schema object.
    """

    schema: ChunkingSchemaV3


def _to_path(path_value: str, backend_root: Path, repo_root: Path) -> Path:
    """
    Resolve schema path value against repo/backend roots.
    """

    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()

    if path_value.startswith("backend/"):
        return (repo_root / path).resolve()

    backend_candidate = (backend_root / path).resolve()
    if backend_candidate.exists():
        return backend_candidate

    repo_candidate = (repo_root / path).resolve()
    if repo_candidate.exists():
        return repo_candidate

    return backend_candidate


def _validate_schema_links(schema: ChunkingSchemaV3) -> None:
    """
    Validate referential integrity inside the schema.
    """

    category_ids = {category.id for category in schema.categories}
    if schema.default_category_id not in category_ids:
        raise ServiceError(
            detail=f"default_category_id is unknown: {schema.default_category_id}",
            error_code="etl_schema_invalid_default_category",
            status_code=400,
        )

    policy_ids = {policy.id for policy in schema.chunking_policies}
    bound_categories = set()

    for binding in schema.category_policy_bindings:
        if binding.category_id not in category_ids:
            raise ServiceError(
                detail=f"Unknown category_id in category_policy_bindings: {binding.category_id}",
                error_code="etl_schema_unknown_binding_category",
                status_code=400,
            )

        if binding.policy_id not in policy_ids:
            raise ServiceError(
                detail=f"Unknown policy_id in category_policy_bindings: {binding.policy_id}",
                error_code="etl_schema_unknown_binding_policy",
                status_code=400,
            )

        bound_categories.add(binding.category_id)

    for category_id in category_ids:
        if category_id not in bound_categories:
            raise ServiceError(
                detail=f"Category has no chunking policy binding: {category_id}",
                error_code="etl_schema_missing_category_binding",
                status_code=400,
            )

    for rule in schema.classification_rules:
        if rule.target_category_id not in category_ids:
            raise ServiceError(
                detail=f"Unknown target_category_id in classification_rules: {rule.target_category_id}",
                error_code="etl_schema_unknown_rule_category",
                status_code=400,
            )

    for lane in schema.retrieval_lanes:
        unknown = [item for item in lane.allowed_category_ids if item not in category_ids]
        if unknown:
            raise ServiceError(
                detail=f"Lane '{lane.id}' references unknown categories: {', '.join(unknown)}",
                error_code="etl_schema_unknown_lane_category",
                status_code=400,
            )

    for block in schema.static_prompt.blocks:
        unknown = [item for item in block.source.category_ids if item not in category_ids]
        if unknown:
            raise ServiceError(
                detail=f"Static prompt block '{block.id}' references unknown categories: {', '.join(unknown)}",
                error_code="etl_schema_unknown_static_category",
                status_code=400,
            )


def load_runtime_schema(schema_path: Path, backend_root: Path, repo_root: Path) -> RuntimeSchemaContext:
    """
    Read schema JSON and produce runtime context.
    """

    if not schema_path.is_file():
        raise ServiceError(
            detail=f"Schema file not found: {schema_path}",
            error_code="etl_schema_not_found",
            status_code=404,
        )

    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    schema = ChunkingSchemaV3.model_validate(payload)
    _validate_schema_links(schema)

    return RuntimeSchemaContext(schema=schema)


def resolve_schema_source_path(
    schema: ChunkingSchemaV3,
    *,
    backend_root: Path,
    repo_root: Path,
    source_override: str | None,
) -> Path:
    """
    Resolve markdown source path for schema-driven ingestion.
    """

    if source_override:
        return _to_path(source_override, backend_root, repo_root)

    return _to_path(schema.document.source_path, backend_root, repo_root)


def resolve_schema_output_root(
    schema: ChunkingSchemaV3,
    *,
    backend_root: Path,
    repo_root: Path,
    output_root_override: str | None,
) -> Path:
    """
    Resolve output root for schema-driven run.
    """

    if output_root_override:
        return _to_path(output_root_override, backend_root, repo_root)

    return _to_path(schema.io.output_root, backend_root, repo_root)


@lru_cache(maxsize=8)
def load_runtime_schema_for_language(language_code: str, backend_root: str) -> RuntimeSchemaContext:
    """
    Load and cache runtime schema context by KB language code.
    """

    backend = Path(backend_root)
    repo = backend.parent
    schema_path = resolve_kb_chunking_schema_path(language_code, backend)

    return load_runtime_schema(schema_path, backend, repo)
