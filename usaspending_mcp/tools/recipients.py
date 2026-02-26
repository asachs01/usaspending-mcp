"""query_recipient tool — recipient search and profile detail."""

from __future__ import annotations

import httpx

from usaspending_mcp.server import mcp
from usaspending_mcp.client import api


@mcp.tool()
async def query_recipient(
    search_text: str | None = None,
    recipient_id: str | None = None,
    year: str = "latest",
) -> dict:
    """Search for or get details about federal award recipients.

    Provide `search_text` for autocomplete search, or `recipient_id` for
    a full recipient profile. If both are provided, the profile lookup
    takes precedence.

    Args:
        search_text: Name search text (autocomplete)
        recipient_id: Recipient unique ID for full profile
        year: Fiscal year for profile data (default: 'latest')
    """
    try:
        if recipient_id:
            result = await api.get_recipient(recipient_id, year=year)
            result["_query"] = {"recipient_id": recipient_id, "year": year}
            return result

        if search_text:
            results = await api.autocomplete_recipient(search_text)
            return {
                "results": results,
                "count": len(results),
                "_query": {"search_text": search_text},
            }
    except httpx.HTTPStatusError as e:
        return {"error": f"API error {e.response.status_code}", "detail": e.response.text[:200]}
    except httpx.RequestError as e:
        return {"error": f"Network error: {e}"}

    return {
        "error": "Provide either 'search_text' for search or 'recipient_id' for profile.",
        "hint": "Example: search_text='Lockheed' or recipient_id='abc-123-R'",
    }
