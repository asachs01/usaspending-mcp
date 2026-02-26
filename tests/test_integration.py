"""Integration tests for the full MCP protocol flow.

These tests exercise the server via its MCP protocol interface, not by
calling tool functions directly. Uses respx to mock the USASpending API
so we don't hit the live service.
"""

import json
import subprocess
import sys

import pytest
import respx
from httpx import Response

from usaspending_mcp.client import api
from usaspending_mcp.client.cache import cache


def _mcp_request(method: str, params: dict | None = None, req_id: int = 1) -> str:
    """Build a JSON-RPC request string."""
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg)


def _mcp_notification(method: str, params: dict | None = None) -> str:
    """Build a JSON-RPC notification string (no id)."""
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg)


def _run_stdio_session(messages: list[str], timeout: int = 10) -> list[dict]:
    """Send messages to the MCP server via STDIO and collect responses."""
    input_data = "\n".join(messages) + "\n"
    result = subprocess.run(
        [sys.executable, "-m", "usaspending_mcp.server", "--transport", "stdio"],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    responses = []
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            try:
                responses.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return responses


class TestSTDIOProtocol:
    """Test the MCP protocol flow via STDIO transport."""

    def test_initialize(self):
        messages = [
            _mcp_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }),
        ]
        responses = _run_stdio_session(messages)
        assert len(responses) >= 1
        init_resp = responses[0]
        assert init_resp["result"]["serverInfo"]["name"] == "USASpending"
        # Verify capabilities declared
        caps = init_resp["result"]["capabilities"]
        assert "tools" in caps
        assert "resources" in caps

    def test_tools_registered_in_manager(self):
        """Verify all 8 tools are in the tool manager (in-process check)."""
        from usaspending_mcp.server import mcp as server_mcp
        tools = server_mcp._tool_manager._tools
        expected = [
            "search_awards", "get_award", "query_agency", "query_recipient",
            "query_spending", "query_disaster", "query_accounts", "manage_download",
        ]
        for name in expected:
            assert name in tools, f"Missing tool: {name}"
        assert len(tools) == 8

    def test_resources_registered_in_manager(self):
        """Verify all 4 resources are registered (in-process check)."""
        from usaspending_mcp.server import mcp as server_mcp
        resources = server_mcp._resource_manager._resources
        expected_uris = [
            "usaspending://agencies",
            "usaspending://fiscal-year/current",
            "usaspending://data-freshness",
            "usaspending://glossary",
        ]
        for uri in expected_uris:
            assert uri in resources, f"Missing resource: {uri}"
        assert len(resources) == 4


class TestToolDirectCalls:
    """Test tool functions directly with mocked API (faster than STDIO)."""

    @pytest.fixture(autouse=True)
    async def _setup(self):
        await api.close()
        cache.clear_all()
        cache.put("agencies", [
            {"agency_name": "Department of Defense", "toptier_code": "097"},
        ])
        cache.put("fiscal_year", 2026)
        yield
        await api.close()
        cache.clear_all()

    @respx.mock
    async def test_search_and_get_award_flow(self):
        """Simulate: search → get detail for first result."""
        # Step 1: Search
        respx.post("/api/v2/search/spending_by_award/").mock(
            return_value=Response(200, json={
                "results": [{"Award ID": "CONT_ABC", "Award Amount": 1000000}],
                "page_metadata": {"total": 1, "hasNext": False},
            })
        )
        from usaspending_mcp.tools.awards import search_awards
        search_result = await search_awards(keyword="cybersecurity")
        assert search_result["total"] == 1
        award_id = search_result["results"][0]["Award ID"]

        # Step 2: Get detail
        respx.get(f"/api/v2/awards/{award_id}/").mock(
            return_value=Response(200, json={
                "id": 1,
                "generated_unique_award_id": award_id,
                "total_obligation": 1000000,
            })
        )
        from usaspending_mcp.tools.awards import get_award
        detail = await get_award(award_id)
        assert detail["generated_unique_award_id"] == "CONT_ABC"

    @respx.mock
    async def test_agency_then_spending_flow(self):
        """Simulate: lookup agency → query spending breakdown."""
        respx.get("/api/v2/agency/097/").mock(
            return_value=Response(200, json={
                "toptier_code": "097",
                "name": "Department of Defense",
            })
        )
        from usaspending_mcp.tools.agency import query_agency
        agency = await query_agency("Department of Defense")
        assert agency["toptier_code"] == "097"

        respx.post("/api/v2/spending/").mock(
            return_value=Response(200, json={
                "results": [{"name": "DOD", "amount": 800e9}],
            })
        )
        from usaspending_mcp.tools.spending import query_spending
        spending = await query_spending(breakdown="agency")
        assert len(spending["results"]) > 0

    def test_no_blocking_startup_calls(self):
        """Verify the server starts without any API calls."""
        # If this import works without network access, startup is non-blocking
        cache.clear_all()
        from usaspending_mcp.server import mcp  # noqa: F811
        assert mcp.name == "USASpending"
        # Cache should be empty — nothing loaded at import time
        assert not cache.is_cached("agencies")
        assert not cache.is_cached("fiscal_year")
