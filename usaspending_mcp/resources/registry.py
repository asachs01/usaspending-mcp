"""MCP resource definitions — subscribable data endpoints."""

from __future__ import annotations

import json

from usaspending_mcp.server import mcp
from usaspending_mcp.client.cache import cache
from usaspending_mcp.client import api


@mcp.resource("usaspending://agencies")
async def agencies_resource() -> str:
    """Full list of toptier federal agencies with codes and names."""
    agencies = await cache.get("agencies")
    return json.dumps(agencies, indent=2)


@mcp.resource("usaspending://fiscal-year/current")
async def fiscal_year_resource() -> str:
    """Current US federal fiscal year (Oct 1 start)."""
    fy = await cache.get("fiscal_year")
    return json.dumps({"fiscal_year": fy})


@mcp.resource("usaspending://data-freshness")
async def data_freshness_resource() -> str:
    """Last updated timestamp from USASpending API."""
    result = await api.get_last_updated()
    return json.dumps(result)


@mcp.resource("usaspending://glossary")
async def glossary_resource() -> str:
    """Federal spending glossary terms and definitions."""
    terms = await api.get_glossary()
    return json.dumps(terms, indent=2)
