"""Tests for API client — uses respx to mock httpx requests."""

import pytest
import respx
from httpx import Response

from usaspending_mcp.client import api


@pytest.fixture(autouse=True)
async def _reset_client():
    """Ensure fresh client for each test."""
    await api.close()
    yield
    await api.close()


@respx.mock
async def test_get_agencies():
    respx.get("/api/v2/references/toptier_agencies/").mock(
        return_value=Response(200, json={"results": [{"agency_name": "DOD"}]})
    )
    result = await api.get_agencies()
    assert result == [{"agency_name": "DOD"}]


@respx.mock
async def test_get_agency():
    respx.get("/api/v2/agency/012/").mock(
        return_value=Response(200, json={"toptier_code": "012", "name": "Agriculture"})
    )
    result = await api.get_agency("012")
    assert result["toptier_code"] == "012"


@respx.mock
async def test_search_awards():
    respx.post("/api/v2/search/spending_by_award/").mock(
        return_value=Response(200, json={"results": [], "page_metadata": {"total": 0}})
    )
    result = await api.search_awards({"filters": {}, "limit": 10, "page": 1})
    assert "results" in result


@respx.mock
async def test_get_award():
    respx.get("/api/v2/awards/CONT_123/").mock(
        return_value=Response(200, json={"id": 1, "generated_unique_award_id": "CONT_123"})
    )
    result = await api.get_award("CONT_123")
    assert result["generated_unique_award_id"] == "CONT_123"


@respx.mock
async def test_autocomplete_recipient():
    respx.post("/api/v2/autocomplete/recipient/").mock(
        return_value=Response(200, json={"results": [{"recipient_name": "Acme Corp"}]})
    )
    result = await api.autocomplete_recipient("Acme")
    assert result[0]["recipient_name"] == "Acme Corp"


@respx.mock
async def test_get_download_status():
    respx.get("/api/v2/bulk_download/status/").mock(
        return_value=Response(200, json={"status": "complete", "file_url": "https://..."})
    )
    result = await api.get_download_status("test_file.zip")
    assert result["status"] == "complete"


def test_get_current_fiscal_year():
    fy = api.get_current_fiscal_year()
    assert isinstance(fy, int)
    assert 2020 <= fy <= 2030


@respx.mock
async def test_get_last_updated():
    respx.get("/api/v2/awards/last_updated/").mock(
        return_value=Response(200, json={"last_updated": "2026-02-25"})
    )
    result = await api.get_last_updated()
    assert "last_updated" in result
