"""search_awards and get_award tools."""

from __future__ import annotations

import httpx
from mcp.server.fastmcp import Context

from usaspending_mcp.server import mcp
from usaspending_mcp.client import api
from usaspending_mcp.client.cache import cache


async def _resolve_agency_code(agency_name: str) -> str | None:
    """Resolve an agency name to its toptier code using cached agency list."""
    agencies = await cache.get("agencies")
    name_lower = agency_name.lower()

    # Exact match first
    for a in agencies:
        if a.get("agency_name", "").lower() == name_lower:
            return str(a["toptier_code"])

    # Partial match
    matches = [
        a for a in agencies
        if name_lower in a.get("agency_name", "").lower()
    ]
    if len(matches) == 1:
        return str(matches[0]["toptier_code"])

    return None


def _build_award_filters(
    keyword: str | None = None,
    agency_code: str | None = None,
    award_type: str | None = None,
    fiscal_year: int | None = None,
    naics_code: str | None = None,
    psc_code: str | None = None,
    recipient_name: str | None = None,
    recipient_state: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
) -> dict:
    """Build the filters dict for the spending_by_award POST body."""
    filters: dict = {}

    if keyword:
        filters["keywords"] = [keyword]

    if agency_code:
        filters["agencies"] = [
            {"type": "funding", "tier": "toptier", "toptier_code": agency_code}
        ]

    # Map friendly names to API award type codes
    type_map = {
        "contract": ["A", "B", "C", "D"],
        "grant": ["02", "03", "04", "05"],
        "loan": ["07", "08"],
        "direct_payment": ["06", "10"],
        "idv": ["IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E"],
        "other": ["09", "11"],
    }
    if award_type and award_type in type_map:
        filters["award_type_codes"] = type_map[award_type]

    if fiscal_year:
        filters["time_period"] = [
            {"start_date": f"{fiscal_year - 1}-10-01", "end_date": f"{fiscal_year}-09-30"}
        ]

    if naics_code:
        filters["naics_codes"] = {"require": [naics_code]}

    if psc_code:
        filters["psc_codes"] = {"require": [psc_code]}

    if recipient_name:
        filters["recipient_search_text"] = [recipient_name]

    if recipient_state:
        filters["place_of_performance_locations"] = [
            {"country": "USA", "state": recipient_state}
        ]

    if min_amount is not None or max_amount is not None:
        amount_filter = {}
        if min_amount is not None:
            amount_filter["lower_bound"] = min_amount
        if max_amount is not None:
            amount_filter["upper_bound"] = max_amount
        filters["award_amounts"] = [amount_filter]

    return filters


@mcp.tool()
async def search_awards(
    keyword: str | None = None,
    agency_name: str | None = None,
    award_type: str | None = None,
    fiscal_year: int | None = None,
    naics_code: str | None = None,
    psc_code: str | None = None,
    recipient_name: str | None = None,
    recipient_state: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    page: int = 1,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict:
    """Search federal awards (contracts, grants, loans, etc.).

    At least one of `keyword` or `agency_name` should be provided.
    Results include award descriptions, amounts, recipients, and agencies.

    Args:
        keyword: Free text search term
        agency_name: Agency name (resolved to toptier code automatically)
        award_type: One of: contract, grant, loan, direct_payment, idv, other
        fiscal_year: Federal fiscal year (Oct-Sep). Defaults to current FY.
        naics_code: 2-6 digit NAICS code filter
        psc_code: 4-character PSC code filter
        recipient_name: Recipient name search text
        recipient_state: 2-letter US state code
        min_amount: Minimum award obligation amount
        max_amount: Maximum award obligation amount
        page: Page number (default 1)
        limit: Results per page (default 10, max 100)
    """
    if not keyword and not agency_name:
        return {
            "error": "At least one of 'keyword' or 'agency_name' is required.",
            "hint": "Provide a search term or agency name to search awards.",
        }

    # Resolve agency name to code
    agency_code = None
    if agency_name:
        agency_code = await _resolve_agency_code(agency_name)
        if agency_code is None:
            return {
                "error": f"Could not resolve agency: {agency_name!r}",
                "hint": "Try a more specific agency name (e.g., 'Department of Defense').",
            }

    # Default to current fiscal year if not specified
    if fiscal_year is None:
        fiscal_year = await cache.get("fiscal_year")

    limit = min(max(limit, 1), 100)

    filters = _build_award_filters(
        keyword=keyword,
        agency_code=agency_code,
        award_type=award_type,
        fiscal_year=fiscal_year,
        naics_code=naics_code,
        psc_code=psc_code,
        recipient_name=recipient_name,
        recipient_state=recipient_state,
        min_amount=min_amount,
        max_amount=max_amount,
    )

    payload = {
        "filters": filters,
        "fields": [
            "Award ID",
            "Recipient Name",
            "Start Date",
            "End Date",
            "Award Amount",
            "Total Outlays",
            "Description",
            "def_codes",
            "COVID-19 Obligations",
            "COVID-19 Outlays",
            "Infrastructure Obligations",
            "Infrastructure Outlays",
            "Awarding Agency",
            "Awarding Sub Agency",
            "Contract Award Type",
            "Award Type",
            "Funding Agency",
            "Funding Sub Agency",
        ],
        "page": page,
        "limit": limit,
        "subawards": False,
        "order": "desc",
        "sort": "Award Amount",
    }

    if ctx:
        await ctx.info(f"Searching awards (page {page}, limit {limit})")

    try:
        result = await api.search_awards(payload)
    except httpx.HTTPStatusError as e:
        return {"error": f"API error {e.response.status_code}", "detail": e.response.text[:200]}
    except httpx.RequestError as e:
        return {"error": f"Network error: {e}"}

    awards = result.get("results", [])
    page_meta = result.get("page_metadata", {})
    total = page_meta.get("total", 0)
    has_next = page_meta.get("hasNext", False)

    if ctx:
        await ctx.report_progress(
            progress=page,
            total=max(1, (total + limit - 1) // limit) if total else 1,
            message=f"Fetched page {page} — {len(awards)} results of {total} total",
        )

    return {
        "results": awards,
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": has_next,
        "filters_applied": {
            k: v for k, v in {
                "keyword": keyword,
                "agency_name": agency_name,
                "award_type": award_type,
                "fiscal_year": fiscal_year,
            }.items() if v is not None
        },
    }


@mcp.tool()
async def get_award(
    award_id: str,
    detail_type: str = "full",
) -> dict:
    """Get details for a specific federal award.

    Args:
        award_id: Generated unique award ID (e.g., 'CONT_IDV_TMHQ10C0040_2044')
        detail_type: Level of detail — one of: full, funding, subawards, transactions, federal_account_count
    """
    valid_types = ["full", "funding", "subawards", "transactions", "federal_account_count"]
    if detail_type not in valid_types:
        return {
            "error": f"Unknown detail_type: {detail_type!r}",
            "valid_types": valid_types,
        }

    try:
        if detail_type == "full":
            return await api.get_award(award_id)
        elif detail_type == "funding":
            return await api.get_award_funding({
                "award_id": award_id,
                "limit": 10,
                "page": 1,
                "order": "desc",
                "sort": "reporting_fiscal_date",
            })
        elif detail_type == "subawards":
            return await api.search_subawards({
                "award_id": award_id,
                "limit": 10,
                "page": 1,
                "order": "desc",
                "sort": "subaward_number",
            })
        elif detail_type == "transactions":
            return await api.search_transactions({
                "award_id": award_id,
                "limit": 10,
                "page": 1,
                "order": "desc",
                "sort": "action_date",
            })
        elif detail_type == "federal_account_count":
            return await api.get_award_count(award_id)
    except httpx.HTTPStatusError as e:
        return {"error": f"API error {e.response.status_code}", "detail": e.response.text[:200]}
    except httpx.RequestError as e:
        return {"error": f"Network error: {e}"}
