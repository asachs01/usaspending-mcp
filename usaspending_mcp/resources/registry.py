"""MCP resource definitions — subscribable data endpoints."""

from __future__ import annotations

import json

import httpx

from usaspending_mcp.server import mcp
from usaspending_mcp.client.cache import cache
from usaspending_mcp.client import api


@mcp.resource("usaspending://agencies")
async def agencies_resource() -> str:
    """Full list of toptier federal agencies with codes and names."""
    try:
        agencies = await cache.get("agencies")
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        return json.dumps({"error": f"Failed to load agencies: {e}"})
    return json.dumps(agencies, indent=2)


@mcp.resource("usaspending://fiscal-year/current")
async def fiscal_year_resource() -> str:
    """Current US federal fiscal year (Oct 1 start)."""
    fy = await cache.get("fiscal_year")
    return json.dumps({"fiscal_year": fy})


@mcp.resource("usaspending://data-freshness")
async def data_freshness_resource() -> str:
    """Last updated timestamp from USASpending API."""
    try:
        result = await api.get_last_updated()
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        return json.dumps({"error": f"Failed to fetch data freshness: {e}"})
    return json.dumps(result)


@mcp.resource("usaspending://glossary")
async def glossary_resource() -> str:
    """Federal spending glossary terms and definitions."""
    try:
        terms = await api.get_glossary()
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        return json.dumps({"error": f"Failed to fetch glossary: {e}"})
    return json.dumps(terms, indent=2)
