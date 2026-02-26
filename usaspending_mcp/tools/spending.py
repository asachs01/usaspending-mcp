"""query_spending tool — spending explorer breakdowns."""

from __future__ import annotations

import httpx

from usaspending_mcp.server import mcp
from usaspending_mcp.client import api
from usaspending_mcp.client.cache import cache


_VALID_BREAKDOWNS = ["agency", "budget_function", "object_class", "program_activity"]


@mcp.tool()
async def query_spending(
    breakdown: str,
    fiscal_year: int | None = None,
) -> dict:
    """Explore federal spending by category.

    Args:
        breakdown: How to break down spending. One of:
            agency, budget_function, object_class, program_activity
        fiscal_year: Federal fiscal year (defaults to current)
    """
    if breakdown not in _VALID_BREAKDOWNS:
        return {
            "error": f"Unknown breakdown: {breakdown!r}",
            "valid_breakdowns": _VALID_BREAKDOWNS,
        }

    if fiscal_year is None:
        fiscal_year = await cache.get("fiscal_year")

    filters = {"fiscal_year": fiscal_year}
    try:
        result = await api.get_spending(breakdown, filters)
    except httpx.HTTPStatusError as e:
        return {"error": f"API error {e.response.status_code}", "detail": e.response.text[:200]}
    except httpx.RequestError as e:
        return {"error": f"Network error: {e}"}
    result["_query"] = {"breakdown": breakdown, "fiscal_year": fiscal_year}
    return result
