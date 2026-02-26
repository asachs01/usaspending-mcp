"""Tests for query_agency tool."""

import pytest
import respx
from httpx import Response

from usaspending_mcp.client import api
from usaspending_mcp.client.cache import cache
from usaspending_mcp.tools.agency import query_agency


@pytest.fixture(autouse=True)
async def _setup():
    await api.close()
    cache.clear_all()
    cache.put("agencies", [
        {"agency_name": "Department of Defense", "toptier_code": "097"},
        {"agency_name": "Department of Agriculture", "toptier_code": "012"},
        {"agency_name": "Department of the Army", "toptier_code": "021"},
    ])
    cache.put("fiscal_year", 2026)
    yield
    await api.close()
    cache.clear_all()


@respx.mock
async def test_query_agency_overview():
    respx.get("/api/v2/agency/097/").mock(
        return_value=Response(200, json={
            "toptier_code": "097",
            "name": "Department of Defense",
        })
    )
    result = await query_agency("Department of Defense")
    assert result["toptier_code"] == "097"
    assert result["_query"]["agency_name"] == "Department of Defense"


@respx.mock
async def test_query_agency_with_breakdown():
    respx.get("/api/v2/agency/097/sub_agency/").mock(
        return_value=Response(200, json={"results": [{"name": "Army"}]})
    )
    result = await query_agency("Department of Defense", breakdown="sub_agencies")
    assert "results" in result
    assert result["_query"]["breakdown"] == "sub_agencies"


async def test_query_agency_not_found():
    result = await query_agency("Nonexistent Agency")
    assert "error" in result
    assert "No agency found" in result["error"]


async def test_query_agency_ambiguous():
    # "Department" matches all three agencies
    result = await query_agency("Department")
    assert "error" in result
    assert "Ambiguous" in result["error"]
    assert len(result["matches"]) == 3


async def test_query_agency_invalid_breakdown():
    result = await query_agency("Department of Defense", breakdown="invalid")
    assert "error" in result
    assert "valid_breakdowns" in result
