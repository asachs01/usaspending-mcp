# USASpending MCP Server

## Project Overview
Production-grade MCP server for USASpending.gov federal spending data. Python, async, dual transport (STDIO + Streamable HTTP).

## Tech Stack
- Python 3.11+
- mcp >= 1.3 (MCP SDK)
- httpx >= 0.27 (async HTTP client)
- anyio >= 4.0 (async runtime)
- pytest + pytest-asyncio (testing)

## Architecture
- 8 decision-tree tools routing internally to USASpending API endpoints
- Lazy-loaded reference data with TTL cache
- MCP elicitation for parameter disambiguation
- Progress notifications for long-running operations
- Dual transport: STDIO and Streamable HTTP + SSE

## Key Conventions
- All tools return structured JSON + human-readable text
- No blocking API calls at startup (lazy loading only)
- Decision tree routing is deterministic (if/elif), not LLM-driven
- USASpending API is public, no auth required
- This is a read-only server (no write operations)

## Build & Test
- `pip install -e .` or `uv pip install -e .` for local dev
- `pytest` for test suite
- `python -m usaspending_mcp.server --transport stdio` for STDIO mode
- `python -m usaspending_mcp.server --transport http` for HTTP mode (port 8765)

## Module Structure
```
usaspending_mcp/
  __init__.py          # MCPB manifest
  server.py            # Entry point, transport detection
  transport/           # STDIO and HTTP transport handlers
  tools/               # 8 domain tools + registry
  decision_tree/       # Router and elicitor
  client/              # API client and cache
  resources/           # MCP resources and freshness polling
  notifications/       # Progress and log notifications
```

## Task Management
Using Taskmaster. Tasks are in `.taskmaster/tasks/tasks.json`.

## PRD Reference
Full PRD is in `usaspending-prd.md` at project root.
