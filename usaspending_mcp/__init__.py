"""USASpending MCP Server — federal spending data via api.usaspending.gov."""

extension_manifest = {
    "name": "usaspending-mcp",
    "display_name": "USASpending.gov Federal Spending Data",
    "version": "0.1.0",
    "description": "MCP server for US federal spending data via api.usaspending.gov",
    "transport_modes": ["stdio", "http"],
    "capabilities": ["tools", "resources", "elicitation", "notifications"],
    "mcp_spec_version": "2025-06-18",
    "no_auth_required": True,
}
