from __future__ import annotations

from fastmcp import Client
import pytest

from legal_rag.lexical import indexar
from legal_rag.mcp_server import create_server
from legal_rag.service import LegalSearchService
from test_service import fixture_paths


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_mcp_exposes_only_search_and_accepts_explicit_null(tmp_path):
    paths = fixture_paths(tmp_path)
    indexar(paths)
    server = create_server(LegalSearchService(paths))
    async with Client(server) as client:
        tools = await client.list_tools()
        assert [tool.name for tool in tools] == ["search_legal_sources"]
        result = await client.call_tool("search_legal_sources", {
            "query": "documentos", "strategy": None, "top_k": None,
        })
    data = result.structured_content or result.data
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    assert data["effective_strategy"] == "bm25"
    assert data["results"][0]["chunk_id"] == "lei:art1"

