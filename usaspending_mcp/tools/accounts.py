"""query_accounts tool — federal and treasury account data."""

from __future__ import annotations

import httpx

from usaspending_mcp.server import mcp
from usaspending_mcp.client import api


@mcp.tool()
async def query_accounts(
    federal_account_id: str | None = None,
    treasury_account_symbol: str | None = None,
    breakdown: str = "object_class",
    page: int = 1,
    limit: int = 10,
) -> dict:
    """Query federal and treasury account data.

    - With `federal_account_id`: returns account detail
    - With `treasury_account_symbol`: returns TAS breakdown
    - With neither: lists federal accounts

    Args:
        federal_account_id: Federal account ID for detail view
        treasury_account_symbol: Treasury Account Symbol (TAS) for breakdown
        breakdown: TAS breakdown type (default: object_class)
        page: Page number for listing (default 1)
        limit: Results per page (default 10)
    """
    try:
        if federal_account_id:
            result = await api.get_federal_account(federal_account_id)
            result["_query"] = {"federal_account_id": federal_account_id}
            return result

        if treasury_account_symbol:
            result = await api.get_treasury_account(treasury_account_symbol, breakdown)
            result["_query"] = {
                "treasury_account_symbol": treasury_account_symbol,
                "breakdown": breakdown,
            }
            return result

        # List federal accounts
        result = await api.list_federal_accounts({
            "page": page,
            "limit": limit,
            "sort": {"field": "account_number", "direction": "asc"},
        })
        result["_query"] = {"action": "list", "page": page, "limit": limit}
        return result
    except httpx.HTTPStatusError as e:
        return {"error": f"API error {e.response.status_code}", "detail": e.response.text[:200]}
    except httpx.RequestError as e:
        return {"error": f"Network error: {e}"}
