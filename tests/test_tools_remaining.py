"""Tests for remaining tools: spending, disaster, accounts, downloads."""

import pytest
import respx
from httpx import Response

from usaspending_mcp.client import api
from usaspending_mcp.client.cache import cache
from usaspending_mcp.tools.spending import query_spending
from usaspending_mcp.tools.disaster import query_disaster
from usaspending_mcp.tools.accounts import query_accounts
from usaspending_mcp.tools.downloads import manage_download


@pytest.fixture(autouse=True)
async def _setup():
    await api.close()
    cache.clear_all()
    cache.put("fiscal_year", 2026)
    yield
    await api.close()
    cache.clear_all()


# ── query_spending ────────────────────────────────────────────────────

@respx.mock
async def test_query_spending_by_agency():
    respx.post("/api/v2/spending/").mock(
        return_value=Response(200, json={"results": [{"name": "DOD", "amount": 800e9}]})
    )
    result = await query_spending(breakdown="agency")
    assert "results" in result
    assert result["_query"]["breakdown"] == "agency"


async def test_query_spending_invalid_breakdown():
    result = await query_spending(breakdown="invalid")
    assert "error" in result
    assert "valid_breakdowns" in result


# ── query_disaster ────────────────────────────────────────────────────

@respx.mock
async def test_query_disaster_spending():
    respx.post("/api/v2/disaster/agency/spending/").mock(
        return_value=Response(200, json={"results": [{"name": "FEMA", "amount": 5e9}]})
    )
    result = await query_disaster(disaster_code="L", breakdown="agency")
    assert "results" in result
    assert result["_query"]["disaster_code"] == "L"


@respx.mock
async def test_query_disaster_loans():
    respx.post("/api/v2/disaster/recipient/loans/").mock(
        return_value=Response(200, json={"results": []})
    )
    result = await query_disaster(disaster_code="N", breakdown="recipient", query_type="loans")
    assert result["_query"]["query_type"] == "loans"


async def test_query_disaster_invalid_breakdown():
    result = await query_disaster(disaster_code="L", breakdown="invalid")
    assert "error" in result


# ── query_accounts ────────────────────────────────────────────────────

@respx.mock
async def test_query_accounts_list():
    respx.post("/api/v2/federal_accounts/").mock(
        return_value=Response(200, json={"results": [{"id": 1}], "page_metadata": {}})
    )
    result = await query_accounts()
    assert "results" in result
    assert result["_query"]["action"] == "list"


@respx.mock
async def test_query_accounts_by_id():
    respx.get("/api/v2/federal_accounts/42/").mock(
        return_value=Response(200, json={"id": 42, "account_title": "Treasury General"})
    )
    result = await query_accounts(federal_account_id="42")
    assert result["id"] == 42


@respx.mock
async def test_query_accounts_by_tas():
    respx.get("/api/v2/agency/treasury_account/097-0100/object_class/").mock(
        return_value=Response(200, json={"results": []})
    )
    result = await query_accounts(treasury_account_symbol="097-0100")
    assert result["_query"]["treasury_account_symbol"] == "097-0100"


# ── manage_download ──────────────────────────────────────────────────

@respx.mock
async def test_manage_download_initiate():
    respx.post("/api/v2/bulk_download/awards/").mock(
        return_value=Response(200, json={"file_name": "download_123.zip", "status": "running"})
    )
    result = await manage_download(action="initiate")
    assert result["file_name"] == "download_123.zip"
    assert result["_query"]["action"] == "initiate"


@respx.mock
async def test_manage_download_status():
    respx.get("/api/v2/bulk_download/status/").mock(
        return_value=Response(200, json={"status": "complete", "file_url": "https://..."})
    )
    result = await manage_download(action="status", file_name="download_123.zip")
    assert result["status"] == "complete"


async def test_manage_download_status_no_filename():
    result = await manage_download(action="status")
    assert "error" in result


async def test_manage_download_invalid_action():
    result = await manage_download(action="invalid")
    assert "error" in result
    assert "valid_actions" in result
