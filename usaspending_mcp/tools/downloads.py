"""manage_download tool — bulk download initiation and polling."""

from __future__ import annotations

import httpx
from mcp.server.fastmcp import Context

from usaspending_mcp.server import mcp
from usaspending_mcp.client import api
from usaspending_mcp.client.cache import cache


@mcp.tool()
async def manage_download(
    action: str,
    award_type: str = "contracts",
    agency_code: str | None = None,
    fiscal_year: int | None = None,
    file_name: str | None = None,
    ctx: Context | None = None,
) -> dict:
    """Manage bulk CSV download jobs for federal spending data.

    Args:
        action: 'initiate' to start a download job, 'status' to check progress
        award_type: Type of awards to download: contracts, assistance, all (default: contracts)
        agency_code: Toptier agency code to filter (optional)
        fiscal_year: Federal fiscal year (defaults to current)
        file_name: File name from a previous initiate call (required for status)
    """
    if action == "status":
        if not file_name:
            return {
                "error": "file_name is required for status checks.",
                "hint": "Use the file_name returned from action='initiate'.",
            }
        if ctx:
            await ctx.info(f"Checking download status for {file_name}")
        try:
            result = await api.get_download_status(file_name)
        except httpx.HTTPStatusError as e:
            return {"error": f"API error {e.response.status_code}", "detail": e.response.text[:200]}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
        if ctx and "status" in result:
            is_done = result.get("status") == "finished"
            await ctx.report_progress(
                progress=1 if is_done else 0,
                total=1,
                message=f"Download status: {result.get('status', 'unknown')}",
            )
        return result

    elif action == "initiate":
        if fiscal_year is None:
            fiscal_year = await cache.get("fiscal_year")

        if ctx:
            await ctx.info(f"Initiating {award_type} download for FY{fiscal_year}")

        filters = {
            "prime_award_types": _get_award_type_codes(award_type),
            "date_type": "action_date",
            "date_range": {
                "start_date": f"{fiscal_year - 1}-10-01",
                "end_date": f"{fiscal_year}-09-30",
            },
        }

        if agency_code:
            filters["agency"] = agency_code

        payload = {
            "filters": filters,
            "columns": [],
            "file_format": "csv",
        }

        try:
            result = await api.initiate_download(payload)
        except httpx.HTTPStatusError as e:
            return {"error": f"API error {e.response.status_code}", "detail": e.response.text[:200]}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

        if ctx:
            await ctx.report_progress(
                progress=0,
                total=100,
                message="Download job initiated — use action='status' to poll",
            )

        result["_query"] = {
            "action": "initiate",
            "award_type": award_type,
            "fiscal_year": fiscal_year,
        }
        return result

    else:
        return {
            "error": f"Unknown action: {action!r}",
            "valid_actions": ["initiate", "status"],
        }


def _get_award_type_codes(award_type: str) -> list[str]:
    """Map friendly award type to API codes."""
    type_map = {
        "contracts": ["A", "B", "C", "D"],
        "assistance": ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
        "all": ["A", "B", "C", "D", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
    }
    return type_map.get(award_type, type_map["contracts"])
