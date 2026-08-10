"""Unit tests for directory-based schema discovery and path resolution."""

import json

import pytest

from app.exceptions.service import ServiceError
from etl.chunking_schema import (
    CHUNKING_SCHEMA_FORMAT,
    discover_chunking_schemas,
    load_runtime_schema,
    resolve_path_relative_to_schema,
    resolve_schema_chunk_meta_db_path,
    resolve_schema_source_path,
)

from tests.paths import BACKEND_ROOT


DATA_DIR = BACKEND_ROOT / "data"


def test_discover_chunking_schemas_finds_ru_and_en() -> None:
    """
    The shipped backend/data directory should expose both KB schema files.
    """

    schema_paths = discover_chunking_schemas(DATA_DIR)

    assert len(schema_paths) == 2
    assert {path.name for path in schema_paths} == {
        "chunking-schema-en.json",
        "chunking-schema-ru.json",
    }


def test_schema_source_path_is_relative_to_schema_directory() -> None:
    """
    document.source_path should resolve next to the schema JSON file.
    """

    context = load_runtime_schema(
        DATA_DIR / "chunking-schema-en.json",
        BACKEND_ROOT,
        BACKEND_ROOT.parent,
    )

    source_path = resolve_schema_source_path(
        context.schema,
        schema_dir=context.schema_dir,
        backend_root=BACKEND_ROOT,
        repo_root=BACKEND_ROOT.parent,
        source_override=None,
    )

    assert source_path == (DATA_DIR / "rag-document-en.md").resolve()


def test_schema_chunk_meta_db_path_resolves_under_output_root(tmp_path) -> None:
    """
    io.chunk_meta.db_path should resolve under schema output_root.
    """

    schema_dir = tmp_path / "project"
    schema_dir.mkdir()
    schema_path = schema_dir / "chunking-schema-test.json"
    schema_path.write_text(
        json.dumps(
            {
                "format": CHUNKING_SCHEMA_FORMAT,
                "document": {
                    "document_id": "test",
                    "language_code": "en",
                    "display_name": "Test",
                    "source_path": "source.md",
                },
                "io": {
                    "output_root": ".",
                    "chunk_meta": {
                        "kind": "sqlite",
                        "db_path": "app.db",
                    },
                    "faiss_index_path": "faiss.index",
                    "manifest_path": "manifest.json",
                },
                "categories": [
                    {
                        "id": "faq",
                        "description": "FAQ",
                        "indexable": True,
                        "labels": {
                            "section": "Section",
                            "type": "Type",
                            "source": "Source",
                            "context": "Context",
                            "question": "Question",
                            "answer": "Answer",
                        },
                    }
                ],
                "default_category_id": "faq",
                "classification_rules": [],
                "chunking_policies": [
                    {
                        "id": "whole",
                        "strategy": "whole_section",
                        "params": {"emit_chunks": True},
                    }
                ],
                "category_policy_bindings": [{"category_id": "faq", "policy_id": "whole"}],
                "static_prompt": {"enabled": False, "blocks": []},
                "retrieval_lanes": [
                    {
                        "id": "faq",
                        "description": "FAQ lane",
                        "allowed_category_ids": ["faq"],
                        "top_k": 3,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    context = load_runtime_schema(schema_path, BACKEND_ROOT, BACKEND_ROOT.parent)
    db_path = resolve_schema_chunk_meta_db_path(context.schema, schema_dir=context.schema_dir)

    assert db_path == (schema_dir / "app.db").resolve()


def test_resolve_path_relative_to_schema_supports_dot_output_root(tmp_path) -> None:
    """
    output_root '.' should resolve to the schema directory itself.
    """

    schema_dir = tmp_path / "kb"
    schema_dir.mkdir()

    assert resolve_path_relative_to_schema(".", schema_dir) == schema_dir.resolve()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"format": "other-format"},
    ],
)
def test_load_runtime_schema_rejects_unsupported_identity(tmp_path, payload: dict) -> None:
    """
    Schema loader should reject files without the supported format identifier.
    """

    schema_path = tmp_path / "invalid.json"
    schema_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ServiceError) as exc_info:
        load_runtime_schema(schema_path, BACKEND_ROOT, BACKEND_ROOT.parent)

    assert exc_info.value.error_code == "etl_schema_unsupported_format"
