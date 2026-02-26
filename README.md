# usaspending-mcp

Production-grade MCP server for US federal spending data via [api.usaspending.gov](https://api.usaspending.gov).

## Features

- 8 decision-tree tools covering the full USASpending API
- Dual transport: STDIO and Streamable HTTP + SSE
- MCP elicitation for interactive parameter disambiguation
- Progress notifications for long-running operations
- Lazy-loaded reference data with TTL cache
- No authentication required (public API)

## Quick Start

```bash
# Install
pip install usaspending-mcp

# STDIO mode (for Claude Desktop / Claude Code)
usaspending-mcp

# HTTP mode (for hosted deployments)
usaspending-mcp-http --port 8765
```

## Claude Desktop Configuration

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

## License

MIT
