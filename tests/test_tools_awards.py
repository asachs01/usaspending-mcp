"""Tests for search_awards and get_award tools."""

import httpx
import pytest
import respx
from httpx import Response

from usaspending_mcp.client import api
from usaspending_mcp.client.cache import cache
from usaspending_mcp.tools.awards import search_awards, get_award


@pytest.fixture(autouse=True)
async def _setup():
    """Reset client and pre-populate cache for each test."""
    await api.close()
    cache.clear_all()
    # Pre-populate agencies cache
    cache.put("agencies", [
        {"agency_name": "Department of Defense", "toptier_code": "097"},
        {"agency_name": "Department of Agriculture", "toptier_code": "012"},
    ])
    cache.put("fiscal_year", 2026)
    yield
    await api.close()
    cache.clear_all()


async def test_search_awards_requires_keyword_or_agency():
    result = await search_awards()
    assert "error" in result
    assert "keyword" in result["error"]


@respx.mock
async def test_search_awards_by_keyword():
    respx.post("/api/v2/search/spending_by_award/").mock(
        return_value=Response(200, json={
            "results": [{"Award ID": "CONT_123", "Award Amount": 50000}],
            "page_metadata": {"total": 1, "hasNext": False},
        })
    )
    result = await search_awards(keyword="cybersecurity")
    assert result["total"] == 1
    assert len(result["results"]) == 1
    assert result["filters_applied"]["keyword"] == "cybersecurity"


@respx.mock
async def test_search_awards_by_agency():
    respx.post("/api/v2/search/spending_by_award/").mock(
        return_value=Response(200, json={
            "results": [],
            "page_metadata": {"total": 0, "hasNext": False},
        })
    )
    result = await search_awards(agency_name="Department of Defense")
    assert result["total"] == 0
    assert result["filters_applied"]["agency_name"] == "Department of Defense"


async def test_search_awards_bad_agency():
    result = await search_awards(agency_name="Nonexistent Agency")
    assert "error" in result
    assert "resolve" in result["error"]


@respx.mock
async def test_get_award_full():
    respx.get("/api/v2/awards/CONT_123/").mock(
        return_value=Response(200, json={"id": 1, "generated_unique_award_id": "CONT_123"})
    )
    result = await get_award("CONT_123")
    assert result["generated_unique_award_id"] == "CONT_123"


@respx.mock
async def test_get_award_funding():
    respx.post("/api/v2/awards/funding/").mock(
        return_value=Response(200, json={"results": [], "page_metadata": {}})
    )
    result = await get_award("CONT_123", detail_type="funding")
    assert "results" in result


async def test_get_award_invalid_detail_type():
    result = await get_award("CONT_123", detail_type="invalid")
    assert "error" in result
    assert "valid_types" in result


@respx.mock
async def test_get_award_subawards():
    respx.post("/api/v2/subawards/").mock(
        return_value=Response(200, json={"results": [{"id": 1}], "page_metadata": {}})
    )
    result = await get_award("CONT_123", detail_type="subawards")
    assert "results" in result


@respx.mock
async def test_get_award_transactions():
    respx.post("/api/v2/transactions/").mock(
        return_value=Response(200, json={"results": [{"id": 1}], "page_metadata": {}})
    )
    result = await get_award("CONT_123", detail_type="transactions")
    assert "results" in result


@respx.mock
async def test_get_award_federal_account_count():
    respx.get("/api/v2/awards/count/federal_account/CONT_123/").mock(
        return_value=Response(200, json={"federal_account_count": 3})
    )
    result = await get_award("CONT_123", detail_type="federal_account_count")
    assert result["federal_account_count"] == 3


@respx.mock
async def test_search_awards_api_error():
    """Verify API errors are caught and returned as structured dicts."""
    respx.post("/api/v2/search/spending_by_award/").mock(
        return_value=Response(500, text="Internal Server Error")
    )
    result = await search_awards(keyword="test")
    assert "error" in result
    assert "500" in result["error"]


@respx.mock
async def test_get_award_api_error():
    """Verify API errors on get_award are caught."""
    respx.get("/api/v2/awards/BAD_ID/").mock(
        return_value=Response(404, text="Not Found")
    )
    result = await get_award("BAD_ID")
    assert "error" in result
    assert "404" in result["error"]
