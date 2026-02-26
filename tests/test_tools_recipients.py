"""Tests for query_recipient tool."""

import pytest
import respx
from httpx import Response

from usaspending_mcp.client import api
from usaspending_mcp.tools.recipients import query_recipient


@pytest.fixture(autouse=True)
async def _setup():
    await api.close()
    yield
    await api.close()


async def test_query_recipient_requires_input():
    result = await query_recipient()
    assert "error" in result


@respx.mock
async def test_query_recipient_search():
    respx.post("/api/v2/autocomplete/recipient/").mock(
        return_value=Response(200, json={
            "results": [
                {"recipient_name": "Lockheed Martin"},
                {"recipient_name": "Lockheed Enterprises"},
            ]
        })
    )
    result = await query_recipient(search_text="Lockheed")
    assert result["count"] == 2
    assert result["results"][0]["recipient_name"] == "Lockheed Martin"


@respx.mock
async def test_query_recipient_profile():
    respx.get("/api/v2/recipient/abc-123-R/").mock(
        return_value=Response(200, json={
            "name": "Lockheed Martin",
            "recipient_id": "abc-123-R",
            "total_transaction_amount": 1000000,
        })
    )
    result = await query_recipient(recipient_id="abc-123-R")
    assert result["name"] == "Lockheed Martin"
    assert result["_query"]["recipient_id"] == "abc-123-R"


@respx.mock
async def test_query_recipient_profile_takes_precedence():
    """When both search_text and recipient_id are provided, profile wins."""
    respx.get("/api/v2/recipient/abc-123-R/").mock(
        return_value=Response(200, json={"name": "Lockheed Martin", "recipient_id": "abc-123-R"})
    )
    result = await query_recipient(search_text="Lockheed", recipient_id="abc-123-R")
    # Profile returned, not search results
    assert result["name"] == "Lockheed Martin"
