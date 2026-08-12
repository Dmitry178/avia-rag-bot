"""Load and validate schema-driven ETL chunking configuration."""

import json

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.core.config import resolve_kb_chunking_schema_path
from src.exceptions.service import ServiceError


CHUNKING_SCHEMA_FORMAT = "rag.chunking-schema.v3"


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
    label: str
    description: str = ""
    allowed_category_ids: list[str]
    top_k: int
    oversample: int = 10
    min_fetch: int = 80
    min_similarity: float = 0.4
    presentation: RetrievalLanePresentation | None = None


class ChunkingSchemaV3(BaseModel):
    """
    Top-level chunking schema (format rag.chunking-schema.v3).
    """

    format: str
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
    Runtime schema object with resolved filesystem anchors.
    """

    schema: ChunkingSchemaV3
    schema_path: Path
    schema_dir: Path


def resolve_path_relative_to_schema(path_value: str, schema_dir: Path) -> Path:
    """
    Resolve a path relative to the directory that contains the schema JSON file.
    """

    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()

    return (schema_dir / path).resolve()


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


def _validate_schema_identity(payload: dict[str, object], *, schema_path: Path) -> None:
    """
    Ensure the JSON file is a supported RAG chunking schema.
    """

    schema_format = payload.get("format")
    if schema_format != CHUNKING_SCHEMA_FORMAT:
        raise ServiceError(
            detail=(
                f"Unsupported schema format in {schema_path.name}: "
                f"expected {CHUNKING_SCHEMA_FORMAT!r}, got {schema_format!r}"
            ),
            error_code="etl_schema_unsupported_format",
            status_code=400,
        )


def discover_chunking_schemas(directory: Path) -> list[Path]:
    """
    Find supported chunking schema JSON files in a directory (non-recursive).
    """

    if not directory.is_dir():
        raise ServiceError(
            detail=f"Schema directory not found: {directory}",
            error_code="etl_schema_directory_not_found",
            status_code=404,
        )

    discovered: list[Path] = []

    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if payload.get("format") == CHUNKING_SCHEMA_FORMAT:
            discovered.append(path.resolve())

    if not discovered:
        raise ServiceError(
            detail=(
                f"No {CHUNKING_SCHEMA_FORMAT} schema files found in {directory}. "
                "Expected one or more *.json files with a matching format field."
            ),
            error_code="etl_schema_directory_empty",
            status_code=404,
        )

    return discovered


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

    resolved_schema_path = schema_path.resolve()
    schema_dir = resolved_schema_path.parent

    if not resolved_schema_path.is_file():
        raise ServiceError(
            detail=f"Schema file not found: {resolved_schema_path}",
            error_code="etl_schema_not_found",
            status_code=404,
        )

    payload = json.loads(resolved_schema_path.read_text(encoding="utf-8"))
    _validate_schema_identity(payload, schema_path=resolved_schema_path)
    schema = ChunkingSchemaV3.model_validate(payload)
    _validate_schema_links(schema)

    return RuntimeSchemaContext(
        schema=schema,
        schema_path=resolved_schema_path,
        schema_dir=schema_dir,
    )


def resolve_schema_source_path(
    schema: ChunkingSchemaV3,
    *,
    schema_dir: Path,
    backend_root: Path,
    repo_root: Path,
    source_override: str | None,
) -> Path:
    """
    Resolve markdown source path for schema-driven ingestion.
    """

    if source_override:
        return _to_path(source_override, backend_root, repo_root)

    return resolve_path_relative_to_schema(schema.document.source_path, schema_dir)


def resolve_schema_output_root(
    schema: ChunkingSchemaV3,
    *,
    schema_dir: Path,
    backend_root: Path,
    repo_root: Path,
    output_root_override: str | None,
) -> Path:
    """
    Resolve output root for schema-driven run.
    """

    if output_root_override:
        return _to_path(output_root_override, backend_root, repo_root)

    return resolve_path_relative_to_schema(schema.io.output_root, schema_dir)


def resolve_schema_chunk_meta_db_path(schema: ChunkingSchemaV3, *, schema_dir: Path) -> Path | None:
    """
    Resolve SQLite chunk metadata database path declared in schema io.chunk_meta.
    """

    chunk_meta = schema.io.chunk_meta
    if chunk_meta is None or chunk_meta.kind != "sqlite" or not chunk_meta.db_path:
        return None

    output_root = resolve_schema_output_root(
        schema,
        schema_dir=schema_dir,
        backend_root=schema_dir,
        repo_root=schema_dir.parent,
        output_root_override=None,
    )

    return (output_root / chunk_meta.db_path).resolve()


@lru_cache(maxsize=8)
def load_runtime_schema_for_language(language_code: str, backend_root: str) -> RuntimeSchemaContext:
    """
    Load and cache runtime schema context by KB language code.
    """

    backend = Path(backend_root)
    repo = backend.parent
    schema_path = resolve_kb_chunking_schema_path(language_code, backend)

    return load_runtime_schema(schema_path, backend, repo)
