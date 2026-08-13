"""Parity between MCP ingest_schema tool and the shared ingest entrypoint."""

import json
import pytest

from collections.abc import AsyncIterator
from pathlib import Path

from src.mcp.handlers import handle_ingest_schema
from src.mcp.schemas import IngestSchemaToolInput
from src.services.etl import ingest_chunking_schema_at_path

from tests.paths import DATA_DIR


def _prepare_schema(work_dir: Path) -> Path:
    """
    Copy the EN schema into an isolated work directory with local artifact paths.
    """

    work_dir.mkdir(parents=True, exist_ok=True)
    schema = json.loads((DATA_DIR / "chunking-schema-en.json").read_text(encoding="utf-8"))
    schema["document"]["source_path"] = str(DATA_DIR / "rag-document-en.md")
    schema["io"]["chunk_meta"]["db_path"] = "kb.db"
    schema["io"]["faiss_index_path"] = "faiss-en.index"
    schema["io"]["manifest_path"] = "manifest-en.json"

    schema_path = work_dir / "chunking-schema-en.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    return schema_path


async def _mock_iter_embed_batches(self, texts: list[str]) -> AsyncIterator[list[list[float]]]:
    """
    Deterministic fake embeddings (no external LLM).
    """

    dimension = 32

    for offset in range(0, len(texts), 32):
        batch = texts[offset : offset + 32]
        yield [[0.01 * ((offset + index) % 17 + 1)] * dimension for index, _ in enumerate(batch)]


@pytest.mark.asyncio
async def test_ingest_schema_mcp_matches_direct_call(tmp_path, monkeypatch) -> None:
    """
    MCP ``ingest_schema`` and ``ingest_chunking_schema_at_path`` should produce the same ingest stats.
    """

    monkeypatch.setenv("LLM__BASE_URL", "http://embedding.test")
    monkeypatch.setenv("LLM__EMBEDDING_MODEL", "test-embedding")
    monkeypatch.setenv("LLM__API_KEY", "test-key")

    monkeypatch.setattr(
        "src.llm.embeddings.EmbeddingClient.iter_embed_batches",
        _mock_iter_embed_batches,
    )

    mcp_schema = _prepare_schema(tmp_path / "mcp")
    direct_schema = _prepare_schema(tmp_path / "direct")

    mcp_payload = await handle_ingest_schema(
        IngestSchemaToolInput(schema_path=str(mcp_schema), rebuild=True),
    )
    direct_result = await ingest_chunking_schema_at_path(direct_schema, rebuild=True)

    assert mcp_payload["language_code"] == direct_result.language_code
    assert mcp_payload["chunk_count"] == direct_result.chunk_count
    assert mcp_payload["doc_hash"] == direct_result.doc_hash
    assert mcp_payload["added"] == direct_result.added
    assert mcp_payload["updated"] == direct_result.updated
    assert mcp_payload["unchanged"] == direct_result.unchanged
    assert mcp_payload["removed"] == direct_result.removed
