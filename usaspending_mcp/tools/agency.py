"""query_agency tool — agency overview, budgetary resources, sub-agencies, etc."""

from __future__ import annotations

import httpx

from usaspending_mcp.server import mcp
from usaspending_mcp.client import api
from usaspending_mcp.client.cache import cache


# Maps breakdown param values to API sub-endpoint paths
_BREAKDOWN_ENDPOINTS = {
    "budgetary_resources": "budgetary_resources",
    "sub_agencies": "sub_agency",
    "federal_accounts": "federal_account",
    "budget_functions": "budget_function",
    "object_classes": "object_class",
    "program_activities": "program_activity",
    "obligations_by_category": "obligations_by_award_category",
}


async def _resolve_agency_code(agency_name: str) -> tuple[str | None, list[dict]]:
    """Resolve agency name to toptier code. Returns (code, matches)."""
    agencies = await cache.get("agencies")
    name_lower = agency_name.lower()

    # Exact match
    for a in agencies:
        if a.get("agency_name", "").lower() == name_lower:
            return str(a["toptier_code"]), [a]

    # Partial matches
    matches = [
        a for a in agencies
        if name_lower in a.get("agency_name", "").lower()
    ]

    if len(matches) == 1:
        return str(matches[0]["toptier_code"]), matches

    return None, matches


@mcp.tool()
async def query_agency(
    agency_name: str,
    breakdown: str | None = None,
    fiscal_year: int | None = None,
) -> dict:
    """Query federal agency data — overview, budgets, sub-agencies, and more.

    Without a breakdown, returns the agency overview. With a breakdown,
    returns detailed data for that category.

    Args:
        agency_name: Agency name (e.g., 'Department of Defense', 'DOD')
        breakdown: Optional detail type. One of: budgetary_resources,
            sub_agencies, federal_accounts, budget_functions,
            object_classes, program_activities, obligations_by_category
        fiscal_year: Federal fiscal year (defaults to current)
    """
    code, matches = await _resolve_agency_code(agency_name)

    if code is None:
        if matches:
            return {
                "error": f"Ambiguous agency name: {agency_name!r}",
                "matches": [
                    {"name": a["agency_name"], "code": a["toptier_code"]}
                    for a in matches[:10]
                ],
                "hint": "Please specify one of the matching agencies above.",
            }
        return {
            "error": f"No agency found matching: {agency_name!r}",
            "hint": "Try the full agency name (e.g., 'Department of Defense').",
        }

    if fiscal_year is None:
        fiscal_year = await cache.get("fiscal_year")

    # No breakdown → agency overview
    if breakdown is None:
        try:
            result = await api.get_agency(code)
        except httpx.HTTPStatusError as e:
            return {"error": f"API error {e.response.status_code}", "detail": e.response.text[:200]}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
        result["_query"] = {"agency_name": agency_name, "toptier_code": code}
        return result

    # Validate breakdown
    endpoint = _BREAKDOWN_ENDPOINTS.get(breakdown)
    if endpoint is None:
        return {
            "error": f"Unknown breakdown: {breakdown!r}",
            "valid_breakdowns": list(_BREAKDOWN_ENDPOINTS.keys()),
        }

    try:
        result = await api.get_agency_breakdown(
            code, endpoint, fiscal_year=fiscal_year
        )
    except httpx.HTTPStatusError as e:
        return {"error": f"API error {e.response.status_code}", "detail": e.response.text[:200]}
    except httpx.RequestError as e:
        return {"error": f"Network error: {e}"}
    result["_query"] = {
        "agency_name": agency_name,
        "toptier_code": code,
        "breakdown": breakdown,
        "fiscal_year": fiscal_year,
    }
    return result
