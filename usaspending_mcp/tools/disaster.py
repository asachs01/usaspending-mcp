"""query_disaster tool — disaster/emergency funding via DEFC codes."""

from __future__ import annotations

from usaspending_mcp.server import mcp
from usaspending_mcp.client import api


_VALID_BREAKDOWNS = [
    "agency", "award", "recipient", "cfda",
    "federal_account", "object_class",
]


@mcp.tool()
async def query_disaster(
    disaster_code: str,
    breakdown: str = "agency",
    query_type: str = "spending",
) -> dict:
    """Query disaster/emergency funding by DEFC (Disaster Emergency Fund Code).

    Args:
        disaster_code: DEFC code (e.g., 'L' for COVID-19, 'N' for Infrastructure)
        breakdown: Category breakdown. One of:
            agency, award, recipient, cfda, federal_account, object_class
        query_type: 'spending' (default) or 'loans'
    """
    if breakdown not in _VALID_BREAKDOWNS:
        return {
            "error": f"Unknown breakdown: {breakdown!r}",
            "valid_breakdowns": _VALID_BREAKDOWNS,
        }

    payload = {
        "filter": {
            "def_codes": [disaster_code],
        },
        "spending_type": "total",
    }

    if query_type == "loans":
        result = await api.get_disaster_loans(breakdown, payload)
    else:
        result = await api.get_disaster_spending(breakdown, payload)

    result["_query"] = {
        "disaster_code": disaster_code,
        "breakdown": breakdown,
        "query_type": query_type,
    }
    return result
