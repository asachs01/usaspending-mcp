# usaspending-mcp

Production-grade MCP server for US federal spending data via [api.usaspending.gov](https://api.usaspending.gov).

## Features

- **8 decision-tree tools** covering the full USASpending API (awards, agencies, recipients, spending, disaster funding, accounts, downloads)
- **Dual transport:** STDIO (Claude Desktop/Code) and Streamable HTTP + SSE (hosted deployments)
- **Progress notifications** for long-running paginated searches and bulk downloads
- **4 MCP resources:** agencies list, current fiscal year, data freshness, glossary
- **Lazy-loaded reference data** with TTL cache (no blocking startup calls)
- **No authentication required** — USASpending API is public

## Installation

```bash
# From PyPI (when published)
pip install usaspending-mcp

# From GitHub
pip install git+https://github.com/asachs01/usaspending-mcp.git

# For development
git clone https://github.com/asachs01/usaspending-mcp.git
cd usaspending-mcp
pip install -e ".[dev]"
```

## Quick Start

```bash
# STDIO mode (default — for Claude Desktop / Claude Code)
usaspending-mcp

# HTTP mode (for hosted/remote deployments)
usaspending-mcp-http

# With custom port
usaspending-mcp-http --port 9000

# Auto-detect transport
python -m usaspending_mcp.server --transport http
```

## Configuration

### Claude Desktop

```json
{
  "mcpServers": {
    "usaspending": {
      "command": "uvx",
      "args": ["usaspending-mcp"]
    }
  }
}
```

### Claude Code

```json
{
  "mcpServers": {
    "usaspending": {
      "command": "uvx",
      "args": ["usaspending-mcp"]
    }
  }
}
```

### Remote HTTP (e.g., gateway deployment)

```bash
# Start the HTTP server
USASPENDING_MCP_PORT=8765 usaspending-mcp-http

# Connect via mcp-remote in Claude Desktop
{
  "mcpServers": {
    "usaspending": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://your-server:8765/mcp"]
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `USASPENDING_MCP_TRANSPORT` | (auto) | Force transport: `stdio` or `http` |
| `USASPENDING_MCP_HOST` | `0.0.0.0` | HTTP bind host |
| `USASPENDING_MCP_PORT` | `8765` | HTTP bind port |

## Tools

| Tool | Description |
|---|---|
| `search_awards` | Search federal awards by keyword, agency, type, NAICS, PSC, recipient, amount |
| `get_award` | Get award detail, funding, subawards, transactions by award ID |
| `query_agency` | Agency overview + 7 breakdown types (budgets, sub-agencies, accounts, etc.) |
| `query_recipient` | Recipient autocomplete search and full profile detail |
| `query_spending` | Spending explorer by agency, budget function, object class, program activity |
| `query_disaster` | Disaster/emergency funding by DEFC code with 6 breakdown categories |
| `query_accounts` | Federal account detail, treasury account breakdown, account listing |
| `manage_download` | Initiate and poll bulk CSV download jobs |

## Resources

| URI | Description |
|---|---|
| `usaspending://agencies` | Full list of toptier federal agencies |
| `usaspending://fiscal-year/current` | Current US federal fiscal year |
| `usaspending://data-freshness` | Last updated timestamp from the API |
| `usaspending://glossary` | Federal spending glossary terms |

## Development

```bash
# Run tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_tools_awards.py -v
```

## Architecture

```
usaspending_mcp/
  __init__.py          # MCPB extension manifest
  server.py            # Entry point, transport detection, FastMCP setup
  client/
    api.py             # Async httpx wrapper for all API domains
    cache.py           # In-memory lazy cache with per-key TTL
  tools/
    registry.py        # Imports all tool modules for registration
    awards.py          # search_awards, get_award
    agency.py          # query_agency (8 sub-routes)
    recipients.py      # query_recipient
    spending.py        # query_spending
    disaster.py        # query_disaster
    accounts.py        # query_accounts
    downloads.py       # manage_download
  decision_tree/
    router.py          # Parameter inspection and missing-param detection
    elicitor.py        # JSON Schema builder for elicitation
  resources/
    registry.py        # MCP resource definitions
  transport/
    http.py            # HTTP config
    session.py         # Per-session subscription tracking
  notifications/
    progress.py        # Progress notification helpers
```

## License

MIT
