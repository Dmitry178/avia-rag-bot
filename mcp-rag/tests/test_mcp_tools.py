"""Unit tests for MCP tool registration and serialization."""

import pytest

from src.mcp.serialize import serialize_rag_pipeline_result
from src.models.chunk_meta import ChunkMeta
from src.rag.types import RagPipelineResult, RagTraceStep, RetrievedChunk
from src.server import mcp


@pytest.mark.asyncio
async def test_mcp_server_registers_v1_tools() -> None:
    """
    FastMCP server should expose all v1 tools from the migration playbook.
    """

    tools = await mcp.list_tools()
    tool_names = {tool.name for tool in tools}
    expected = {"retrieve", "ingest_schema", "ingest_directory", "ingest_all", "index_status", "stats"}

    assert expected.issubset(tool_names)


def test_serialize_rag_pipeline_result_matches_contract() -> None:
    """
    Serialized retrieve output should include chunk, trace, and verification fields.
    """

    chunk = ChunkMeta(
        id=42,
        language_code="ru",
        content="[Раздел: 01] body",
        content_type="sop",
        section="01. Test",
        title="Test",
        node_id="node",
        content_hash="hash",
        token_count=10,
        source_path="data/rag-document-ru.md",
    )
    item = RetrievedChunk(chunk=chunk, score=0.42, vector_similarity=0.42, retrieval_lane="sop")
    result = RagPipelineResult(
        context="context block",
        chunks=[item],
        trace=[RagTraceStep(step="rag_config", duration_ms=0, data={"use_hyde": False})],
        search_queries=["query"],
        verification_candidates=[],
        applicable_decision_trees=[],
    )

    payload = serialize_rag_pipeline_result(result, language_code="ru")

    assert payload["context"] == "context block"
    assert payload["search_queries"] == ["query"]
    assert payload["chunks"][0]["id"] == 42
    assert payload["chunks"][0]["retrieval_lane"] == "sop"
    assert payload["trace"][0]["step"] == "rag_config"


@pytest.mark.asyncio
async def test_stats_tool_returns_distribution() -> None:
    """
    Stats tool should return total and per-type counts from the KB database.
    """

    from src.mcp.handlers import handle_stats
    from src.mcp.schemas import StatsToolInput

    payload = await handle_stats(StatsToolInput(language_code="ru"))

    assert payload["language_code"] == "ru"
    assert isinstance(payload["total"], int)
    assert isinstance(payload["by_content_type"], dict)


@pytest.mark.asyncio
async def test_index_status_reports_manifest_and_paths() -> None:
    """
    Index status should return manifest metadata (when indexed) and filesystem paths.
    """

    from src.mcp.handlers import handle_index_status
    from src.mcp.schemas import LanguageToolInput

    payload = await handle_index_status(LanguageToolInput(language_code="ru"))

    assert payload["language_code"] == "ru"
    assert "paths" in payload
    assert "faiss_index" in payload["paths"]
    assert isinstance(payload["paths"]["faiss_index_exists"], bool)
    assert payload["manifest"] is None or isinstance(payload["manifest"], dict)
