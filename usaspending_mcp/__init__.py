"""USASpending MCP Server — federal spending data via api.usaspending.gov."""

from importlib.metadata import version as _pkg_version, PackageNotFoundError as _PNF

try:
    _version = _pkg_version("usaspending-mcp")
except _PNF:
    _version = "0.0.0"

extension_manifest = {
    "name": "usaspending-mcp",
    "display_name": "USASpending.gov Federal Spending Data",
    "version": _version,
    "description": "MCP server for US federal spending data via api.usaspending.gov",
    "transport_modes": ["stdio", "http"],
    "capabilities": ["tools", "resources", "elicitation", "notifications"],
    "mcp_spec_version": "2025-06-18",
    "no_auth_required": True,
}
