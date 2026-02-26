# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-26

### Added
- 8 MCP tools covering full USASpending API: search_awards, get_award, query_agency, query_recipient, query_spending, query_disaster, query_accounts, manage_download
- 4 MCP resources: agencies, fiscal-year/current, data-freshness, glossary
- Dual transport support: STDIO and Streamable HTTP + SSE
- Async httpx API client for api.usaspending.gov (all 10 domains)
- In-memory lazy cache with per-key TTL and thundering-herd protection
- Decision-tree routing with deterministic if/elif logic per tool
- Elicitation framework (JSON Schema builder for missing parameters)
- Progress notifications via ctx.report_progress for paginated searches and downloads
- Session subscription tracking for resource notifications
- MCPB extension manifest for portable installation
- Transport detection from CLI args, env vars, and stdin state
- 67 tests (unit + integration) with respx mocking
- Comprehensive README with configuration examples
- MIT License
