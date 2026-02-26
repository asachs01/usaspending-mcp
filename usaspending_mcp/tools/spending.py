"""query_spending tool — spending explorer breakdowns."""

from __future__ import annotations

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
    result = await api.get_spending(breakdown, filters)
    result["_query"] = {"breakdown": breakdown, "fiscal_year": fiscal_year}
    return result
