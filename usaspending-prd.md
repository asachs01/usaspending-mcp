# USASpending MCP Server — Product Requirements Document

> **Version:** v1.0 — Handoff to Claude Code  
> **Date:** February 2026  
> **Author:** WYRE Technology Engineering  
> **Status:** Pre-development

---

## Document Metadata

| Field | Value |
|---|---|
| Project | usaspending-mcp |
| Author | WYRE Technology Engineering |
| MCP Spec Target | 2025-06-18 (elicitation) + 2025-11-25 (tasks/URL-mode) |
| Python SDK | mcp >= 1.3 (asyncio, StreamableHTTP + STDIO) |
| Packaging | MCPB Extension (.mcpb) |
| Transport Modes | STDIO + Streamable HTTP (SSE-backed) |
| API Source | api.usaspending.gov — public, no auth required |
| License | MIT |

---

## 1. Purpose & Background

The USASpending.gov API exposes the full breadth of United States federal spending data — contracts, grants, loans, direct payments, subawards, and more — through a public REST API requiring no authentication. It is one of the richest open government data sources available, covering hundreds of billions of dollars in annual federal obligations.

Two existing MCP servers address this API:

- **flothjl/usaspending-mcp** — 4 tools, STDIO only, proof-of-concept maturity
- **Khowabunga/usaspending-mcp** — 8 tools, Next.js/Vercel, contracting-focused only

Neither provides comprehensive API coverage, dual transport modes, modern MCP protocol features (elicitation, push notifications, tasks), or portable MCPB packaging.

This project delivers a production-grade, fully-featured MCP server for USASpending.gov architected for the MSP/AI-enablement context: decision-tree tool routing to minimize LLM confusion, lazy-loaded reference data for fast startup, MCP elicitation for interactive disambiguation, server-to-client push notifications for long-running operations, and dual transport to work in both local Claude Desktop/Code contexts and hosted gateway deployments like mcp.wyretechnology.com.

---

## 2. Goals & Non-Goals

### 2.1 Goals

- Full coverage of the 10 functional domains in the USASpending API
- Decision-tree tool routing: ~8–10 top-level tools that route internally, avoiding 50+ tool sprawl
- Lazy loading: no blocking API calls at startup; reference data fetched and cached on first use
- MCP Elicitation (spec 2025-06-18): server can pause tool execution to request missing parameters from the user via structured JSON Schema forms
- MCP Push Notifications (spec 2025-03-26+): server emits progress notifications for long-running operations (bulk downloads, large searches); resource subscriptions for dataset freshness
- Dual transport: STDIO (local, Claude Desktop / Claude Code) and Streamable HTTP with SSE (remote/hosted, mcp.wyretechnology.com gateway)
- Packaged as an MCPB extension for portable installation via `uvx` or the MCPB runtime
- Structured tool output (spec 2025-06-18): all tools return validated JSON alongside text content

### 2.2 Non-Goals

- No write operations — USASpending API is read-only
- No bulk download file management beyond initiating jobs and polling status
- No local database or caching layer beyond in-memory session cache
- No authentication implementation — API is public
- No frontend UI — server only

---

## 3. MCP Protocol Feature Specifications

### 3.1 Elicitation

Elicitation (introduced in MCP spec 2025-06-18) allows a server to pause tool execution mid-flight and request additional structured input from the user through the client. The client presents a form-style UI; the user fills it in; the server resumes. This is distinct from asking the LLM to re-invoke the tool — the elicitation round-trip happens within a single tool call.

> **Key constraint:** Elicitation over Streamable HTTP requires an established SSE channel (GET to the MCP endpoint) before the POST tool call, because the elicitation request is delivered over that SSE channel. The server must maintain session state to correlate the two connections. STDIO mode has no such constraint.

Elicitation will be used in this server for the following scenarios:

- **Award search disambiguation:** user says "find DOD contracts" — server elicits fiscal year, award type (contract/grant/IDV), dollar threshold, and recipient state before executing the search
- **Agency resolution:** if an agency name is ambiguous (e.g., "Agriculture" matches multiple toptier codes), server elicits confirmation of the correct agency from a list
- **Bulk download confirmation:** before initiating a CSV download job, server elicits confirmation of scope and warns about file size
- **Date range clarification:** when a tool receives an open-ended query without a fiscal year, server elicits the intended year range

**Implementation requirements:**

- Declare elicitation capability during initialization: `capabilities.elicitation = {}`
- Use `elicitation/create` with `requestedSchema` containing only primitive types (string, number, boolean) — complex types not supported
- Each field in `requestedSchema` MUST include a `description` property to guide the user
- Decision tree in each tool MUST check which parameters are already provided and only elicit for missing ones — do not blanket-elicit if input is sufficient
- For HTTP transport: implement session management so elicitation requests are routed to the correct SSE channel
- Handle all three user response states: `accepted` (data provided), `declined`, `cancelled` — each must have a defined fallback behavior

---

### 3.2 Push Notifications (Server-to-Client Notifications)

MCP supports server-initiated JSON-RPC notifications — one-way messages the server sends to the client without a corresponding request. These are not the same as elicitation (which is request/response). Push notifications are used for progress reporting and resource change events.

This server uses three notification patterns:

#### 3.2.1 Progress Notifications

For long-running tool calls (large searches, bulk download polling), the server emits `notifications/progress` messages. The client includes a `progressToken` in the tool request metadata; the server uses that token in each progress notification.

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "abc123",
    "progress": 45,
    "total": 100,
    "message": "Fetching page 3 of 8 from search API..."
  }
}
```

Tools that MUST emit progress notifications:

- `search_awards` — paginated POST search, can take multiple seconds
- `manage_download` — async bulk download job, may take minutes
- `query_spending` — aggregated multi-year queries

#### 3.2.2 Resource Subscriptions

The server exposes key data as MCP Resources. Clients can subscribe via `resources/subscribe`. The server then emits `notifications/resources/updated` when the data changes; the client re-fetches via `resources/read`.

Resources exposed:

- `usaspending://agencies` — full agency list (updates when `last_updated` changes or 24h TTL expires)
- `usaspending://fiscal-year/current` — current active fiscal year
- `usaspending://data-freshness` — last updated timestamp from the API

#### 3.2.3 Log Notifications

The server emits `notifications/message` (log-level notifications) for debug and info events during tool execution. These surface in MCP Inspector and supporting clients without disrupting the tool response flow.

> **Implementation note:** In STDIO mode, notifications are written to stdout as JSON-RPC notification objects interleaved with responses. In HTTP/SSE mode, notifications are sent over the SSE stream associated with the session. The asyncio-based server must maintain an active SSE connection per session to support both elicitation and notifications in HTTP mode.

---

### 3.3 Structured Tool Output

All tools MUST return both:

- **Structured content** — machine-readable JSON conforming to a declared `outputSchema`
- **Unstructured text content** — human-readable summary

This satisfies MCP spec 2025-06-18 requirements and allows downstream agents to parse tool results reliably without regex.

---

### 3.4 Tasks (MCP spec 2025-11-25)

The November 2025 spec introduced Tasks as a first-class abstraction for tracking async work. Bulk download operations (initiate + poll) SHOULD be implemented as MCP Tasks rather than manual polling tools, where the client runtime supports it. The implementation should declare task support in capabilities and degrade gracefully to progress-notification polling for older clients.

---

## 4. Architecture

### 4.1 Module Structure

```
usaspending_mcp/
  __init__.py
  server.py           # Entry point, transport detection, capability declaration
  transport/
    stdio.py          # STDIO transport handler
    http.py           # Streamable HTTP + SSE transport handler
    session.py        # Session state for HTTP mode (elicitation correlation)
  tools/
    registry.py       # Tool registration and routing
    agency.py         # Agency domain tools
    awards.py         # Award search and detail tools
    recipients.py     # Recipient tools
    spending.py       # Spending explorer / trends tools
    disaster.py       # Disaster/emergency funding tools
    accounts.py       # Federal and treasury account tools
    subawards.py      # Subaward tools
    downloads.py      # Bulk download initiation and polling
  decision_tree/
    router.py         # Intent classification and parameter extraction
    elicitor.py       # Builds elicitation/create requests for missing params
  client/
    api.py            # Thin async httpx wrapper for api.usaspending.gov
    cache.py          # In-memory lazy cache with TTL
  resources/
    registry.py       # MCP resource definitions and subscription tracking
    freshness.py      # Data freshness polling
  notifications/
    progress.py       # Progress notification helpers
    log.py            # Log notification helpers
```

---

### 4.2 Transport Detection

The entry point (`server.py`) detects transport mode at startup using the following decision tree:

1. If `--transport http` flag is present → HTTP mode
2. If `--transport stdio` flag is present → STDIO mode
3. If neither flag: check `sys.stdin.isatty()` → if True, print usage and exit; if False (piped), default to STDIO
4. Environment variable `USASPENDING_MCP_TRANSPORT=http` overrides flag defaults

Both transports share the identical tool registry, decision tree, and API client. Transport is purely a wiring concern.

---

### 4.3 Decision Tree Tool Routing

Rather than exposing every API endpoint as a separate tool (which causes LLM tool-selection confusion at scale), the server exposes 8 top-level domain tools. Each tool accepts a broad set of optional parameters and internally routes to the correct API endpoint(s) based on which parameters are provided.

| Tool Name | Domain / Routing Logic |
|---|---|
| `query_agency` | Agency overview, budgetary resources, sub-agencies, budget functions, federal accounts. Routes by: code only → overview; + `breakdown` param → specific sub-endpoint |
| `search_awards` | Full-text and filtered award search. Routes by: keyword only → keyword search; + agency → agency-scoped; + award_type/naics/psc → filtered search. Paginates with progress notifications. |
| `get_award` | Single award detail, funding, subawards, transactions. Routes by: `award_id` (required). Sub-routes on `detail_type` param: full / funding / subawards / transactions |
| `query_recipient` | Recipient search (autocomplete) and recipient profile detail. Routes by: search text → autocomplete; + `recipient_id` → full profile |
| `query_spending` | Spending explorer — budget functions, object classes, program activities. Routes by: `breakdown` param |
| `query_disaster` | Disaster/emergency funding — agency spending, award spending, loan data, recipient breakdowns. Routes by: `disaster_code` (DEFC codes) + `breakdown` |
| `query_accounts` | Federal account and treasury account data. Routes by: presence of `federal_account_id` vs `treasury_account_symbol` |
| `manage_download` | Bulk download job management. Routes by: `action` param: `initiate` → start job; `status` → poll job. Uses progress notifications and Tasks where supported. |

Each tool's routing logic is implemented as an explicit conditional tree in its handler — deterministic and testable, not LLM reasoning.

---

### 4.4 Lazy Loading and Caching

The server performs zero blocking API calls at startup. All reference data is loaded on first use and held in an in-memory cache with TTL:

| Data | Loaded When / TTL |
|---|---|
| Agency list (toptier codes + names) | First call needing agency resolution / TTL 24h |
| NAICS code list | First `search_awards` call with naics filter / TTL 24h |
| PSC code list | First `search_awards` call with psc filter / TTL 24h |
| Current fiscal year | First any call / TTL 12h |
| Glossary terms | On-demand via `autocomplete/glossary` — never pre-loaded |
| CFDA program list | First disaster or grant search / TTL 24h |

Cache invalidation: `resources/updated` notifications trigger cache eviction for the affected resource. The `freshness.py` module polls `/api/v2/awards/last_updated/` on a 30-minute interval (HTTP mode only) and emits resource subscription notifications when the timestamp changes.

---

## 5. Tool Specifications

### 5.1 Elicitation Decision Tree (per tool)

Every tool MUST follow this pattern before executing its API call:

1. Inspect provided parameters. Build a list of MISSING required parameters.
2. If list is empty → proceed directly to API call.
3. If list is non-empty AND client declared elicitation capability → send `elicitation/create` with a schema covering only the missing fields.
4. If client response is `accepted` → merge returned values into parameters, proceed.
5. If client response is `declined` or `cancelled` → return a graceful error message explaining what was needed.
6. If client did NOT declare elicitation capability → return an error listing the missing required parameters and ask the LLM to re-invoke with them.

> **Never use elicitation to request credentials, PII, or API keys.** USASpending requires no auth. Elicitation is strictly for query parameter disambiguation.

---

### 5.2 Tool: `search_awards`

The flagship tool. Supports keyword search, agency-scoped search, and filtered search by NAICS, PSC, award type, date range, dollar range, and recipient.

**Input Schema** (all optional, but at least one of `keyword` or `agency_name` required):

| Parameter | Type / Description |
|---|---|
| `keyword` | string — free text search term |
| `agency_name` | string — resolved to toptier code via lazy cache |
| `award_type` | string — `contract` \| `grant` \| `loan` \| `direct_payment` \| `idv` \| `other` |
| `fiscal_year` | integer — defaults to current FY via lazy cache if not provided |
| `naics_code` | string — 2–6 digit NAICS code |
| `psc_code` | string — 4-character PSC code |
| `recipient_name` | string — resolved via autocomplete |
| `recipient_state` | string — 2-letter state code |
| `min_amount` | number — minimum award obligation |
| `max_amount` | number — maximum award obligation |
| `page` | integer — pagination page number (default 1) |
| `limit` | integer — results per page (default 10, max 100) |

**Elicitation Trigger:** If neither `keyword` nor `agency_name` is provided, elicit: `keyword` (string), `agency_name` (string), `fiscal_year` (integer), `award_type` (string). Validate that at least one of keyword/agency_name is provided after elicitation.

**Progress Notifications:** Emit `notifications/progress` per page fetched when `total_pages > 1`.

---

### 5.3 Tool: `query_agency`

Returns agency data at varying levels of detail. Routing is determined by the `breakdown` parameter.

| `breakdown` value | API Endpoint Called |
|---|---|
| *(none — default)* | `/api/v2/agency/{code}/` — overview |
| `budgetary_resources` | `/api/v2/agency/{code}/budgetary_resources/` |
| `sub_agencies` | `/api/v2/agency/{code}/sub_agency/` |
| `federal_accounts` | `/api/v2/agency/{code}/federal_account/` |
| `budget_functions` | `/api/v2/agency/{code}/budget_function/` |
| `object_classes` | `/api/v2/agency/{code}/object_class/` |
| `program_activities` | `/api/v2/agency/{code}/program_activity/` |
| `obligations_by_category` | `/api/v2/agency/{code}/obligations_by_award_category/` |

**Elicitation Trigger:** If `agency_name` matches multiple agencies in the lazy-loaded cache, elicit confirmation with a select-style schema listing the top 5 matching agencies by name and code.

---

### 5.4 Tool: `get_award`

Retrieves detail for a specific award by its generated unique award ID (e.g. `CONT_IDV_TMHQ10C0040_2044`).

| `detail_type` value | API Endpoint Called |
|---|---|
| `full` *(default)* | `/api/v2/awards/{id}/` — complete award detail |
| `funding` | `/api/v2/awards/funding` — funding breakdown by federal account |
| `subawards` | `/api/v2/subawards/` filtered by award_id |
| `transactions` | `/api/v2/transactions/` filtered by award_id |
| `federal_accounts` | `/api/v2/awards/count/federal_account/{id}/` |

---

### 5.5 Tool: `query_recipient`

Recipient search and profile detail.

- `search_text` provided → `/api/v2/autocomplete/recipient/` (autocomplete)
- `recipient_id` provided → `/api/v2/recipient/{id}/` (full profile)
- Both provided → profile takes precedence

---

### 5.6 Tool: `query_spending`

Spending explorer breakdowns.

| `breakdown` value | API Endpoint Called |
|---|---|
| `agency` | `/api/v2/spending/?type=agency` |
| `budget_function` | `/api/v2/spending/?type=budget_function` |
| `object_class` | `/api/v2/spending/?type=object_class` |
| `program_activity` | `/api/v2/spending/?type=program_activity` |

**Elicitation Trigger:** If `breakdown` not provided, elicit it.

---

### 5.7 Tool: `query_disaster`

Disaster/emergency funding using DEFC (Disaster Emergency Fund Code) values.

- Routes to `/api/v2/disaster/{breakdown}/spending/` or `/api/v2/disaster/{breakdown}/loans/`
- Supported breakdowns: `agency`, `award`, `recipient`, `cfda`, `federal_account`, `object_class`
- **Elicitation Trigger:** If no `disaster_code` provided, present a list of active DEFC codes and elicit selection.

---

### 5.8 Tool: `query_accounts`

Federal and treasury account data.

- `federal_account_id` provided → `/api/v2/federal_accounts/{id}/`
- `treasury_account_symbol` provided → `/api/v2/agency/treasury_account/{tas}/object_class/` etc.
- Neither provided → list federal accounts: `/api/v2/federal_accounts/`

---

### 5.9 Tool: `manage_download`

Initiates and monitors bulk CSV download jobs (async — API returns a `file_name` and status).

**Actions:**

- `action=initiate` — POST to `/api/v2/bulk_download/awards/` with filters, returns job ID. Emits progress notifications during poll loop. Creates MCP Task where client supports it (2025-11-25).
- `action=status` — GET `/api/v2/bulk_download/status/?file_name={file_name}`, returns current job status and download URL when complete.

**Elicitation Trigger:** Before initiating, elicit confirmation: *"This download may generate a large CSV file. Confirm you want to proceed."* Boolean field: `confirmed`.

---

## 6. MCP Resources

The server exposes the following as subscribable MCP Resources:

| Resource URI | Content / Update Trigger |
|---|---|
| `usaspending://agencies` | JSON array of all toptier agencies. Updated when `last_updated` changes or 24h TTL expires. |
| `usaspending://fiscal-year/current` | Current fiscal year integer. Computed from current date (FY starts Oct 1). |
| `usaspending://data-freshness` | Timestamp from `/api/v2/awards/last_updated/`. Updated every 30 min in HTTP mode. |
| `usaspending://glossary` | Array of glossary terms and definitions. Loaded on first access. |

Resource subscriptions are tracked per-session in HTTP mode. When a subscribed resource updates, the server emits `notifications/resources/updated` to all subscribed clients.

---

## 7. Transport Implementation Details

### 7.1 STDIO Mode

Standard MCP STDIO transport per spec. The server reads JSON-RPC messages from stdin (newline-delimited) and writes responses and notifications to stdout. Stderr is used for server logging only.

- **Entry point:** `usaspending-mcp` (via `console_scripts` in pyproject.toml)
- **Launch:** `uvx usaspending-mcp` or `python -m usaspending_mcp`
- **Session state:** single-session, no HTTP session management needed
- **Elicitation:** delivered synchronously within the request/response cycle
- **Notifications:** written to stdout as JSON-RPC notification objects
- No port binding, no network exposure

---

### 7.2 Streamable HTTP + SSE Mode

Implements the Streamable HTTP transport (MCP spec 2025-06-18, replacing deprecated HTTP+SSE from 2024-11-05). Single MCP endpoint supporting both GET and POST.

- **Entry point:** `usaspending-mcp-http`
- **Default port:** 8765 (configurable via `--port` or `USASPENDING_MCP_PORT`)
- `GET /mcp` → establishes SSE channel (`text/event-stream`). Server sends notifications and elicitation requests on this channel.
- `POST /mcp` → receives JSON-RPC request. Response is either `application/json` (simple) or `text/event-stream` (streaming with progress notifications).
- **Session management:** session ID assigned at GET time. POST requests include `Mcp-Session-Id` header. Elicitation requests are routed to the SSE channel for that session ID.
- **Origin validation:** server validates `Origin` header on all connections to prevent DNS rebinding attacks.
- **Backwards compatibility:** also expose legacy `/sse` and `/message` endpoints for older clients (2024-11-05 style) behind a feature flag.
- **Graceful degradation:** if a POST arrives without an established SSE channel, elicitation and push notifications are silently skipped for that request.

---

## 8. MCPB Extension Packaging

The server is packaged as an MCPB extension for portable, runtime-managed installation.

### 8.1 pyproject.toml

```toml
[project]
name = "usaspending-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["mcp>=1.3", "httpx>=0.27", "anyio>=4.0"]

[project.scripts]
usaspending-mcp = "usaspending_mcp.server:main_stdio"
usaspending-mcp-http = "usaspending_mcp.server:main_http"

[project.entry-points."mcpb.extensions"]
usaspending-mcp = "usaspending_mcp:extension_manifest"
```

### 8.2 MCPB Manifest (`__init__.py`)

```python
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
```

### 8.3 Claude Desktop / Claude Code Config (STDIO)

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

---

## 9. Build Order for Claude Code

Each phase should be independently testable with `mcp-inspector` before proceeding.

| Phase | Deliverable / Acceptance Criteria |
|---|---|
| **Phase 1: Scaffold** | Project structure, pyproject.toml, empty module stubs, transport detection in server.py, MCPB manifest. Test: `uvx usaspending-mcp` prints capabilities without error. |
| **Phase 2: API Client + Cache** | httpx async client in `client/api.py` wrapping the 10 API domains. Lazy cache in `client/cache.py` with TTL. Test: direct Python import and `cache.get('agencies')` fetches and caches. |
| **Phase 3: Core Tools (STDIO)** | Implement `search_awards`, `query_agency`, `get_award`, `query_recipient`. Decision tree routing. No elicitation yet. Test with mcp-inspector via STDIO. |
| **Phase 4: Elicitation** | Add `elicitor.py`. Wire elicitation into all Phase 3 tools. Declare elicitation capability. Test with mcp-inspector. |
| **Phase 5: Remaining Tools** | Implement `query_spending`, `query_disaster`, `query_accounts`, `manage_download`. Wire elicitation into `manage_download`. Test all 8 tools. |
| **Phase 6: Notifications** | Add progress notification emission to `search_awards` and `manage_download`. Add resource definitions and subscription tracking. Freshness polling in HTTP mode. |
| **Phase 7: HTTP Transport** | Implement `transport/http.py` with Streamable HTTP + SSE. Session management for elicitation correlation. Origin validation. Legacy endpoint compat. Test via curl and mcp-inspector HTTP mode. |
| **Phase 8: MCPB Packaging** | Finalize MCPB manifest, test `uvx` install from GitHub, verify both entry points. Build `.mcpb` artifact. Write README with config examples for Claude Desktop, Claude Code, and WYRE gateway. |
| **Phase 9: Tasks (stretch)** | Wrap `manage_download` in MCP Task abstraction per 2025-11-25 spec. Degrade gracefully for older clients. |

---

## 10. API Coverage Matrix

| API Domain | Covered By Tool |
|---|---|
| Agency overview, budgetary resources, sub-agencies | `query_agency` |
| Agency budget functions, object classes, program activities | `query_agency` |
| Award search (keyword, agency, filtered) | `search_awards` |
| Award detail, funding, subawards, transactions | `get_award` |
| Award count endpoints | `get_award` (detail_type=counts) |
| Autocomplete (agencies, recipients, NAICS, PSC, locations) | Internal — used by decision tree for name resolution |
| Recipient search and profile | `query_recipient` |
| Spending explorer (budget function, object class) | `query_spending` |
| Disaster/emergency spending (DEFC codes) | `query_disaster` |
| Federal accounts and treasury accounts | `query_accounts` |
| Subaward search | `get_award` (detail_type=subawards) |
| Bulk download initiation and polling | `manage_download` |
| Data last updated | Internal — used by freshness.py for resource notifications |

---

## 11. Testing Requirements

- Unit tests for decision tree routing logic (mock client — no API calls required)
- Unit tests for lazy cache TTL behavior and eviction
- Unit tests for `elicitor.py` schema generation given various missing-parameter combinations
- Integration tests using mcp-inspector in STDIO mode against live api.usaspending.gov (idempotent reads only)
- Integration tests for HTTP transport: establish SSE channel via GET, then POST tool calls
- Elicitation flow test: verify `declined` / `cancelled` responses return graceful errors
- Progress notification test: verify `notifications/progress` messages are emitted for paginated search
- MCPB packaging test: clean install via `uvx` from GitHub, both entry points functional

---

## 12. Open Questions for Implementation

1. **Python MCP SDK elicitation support:** Confirm `mcp >= 1.3` includes `elicitation/create` handling in the asyncio server class. If not, may need to implement the message type manually on top of the transport.

2. **MCPB bundle spec entry-point key:** Confirm the exact key for `mcpb.extensions` — the spec was still evolving as of late 2025. Cross-reference the Anthropic MCPB blog post before Phase 8.

3. **Tasks spec Python SDK support:** Check Python SDK support for Task primitives (2025-11-25) before committing to Phase 9. May require manual JSON-RPC implementation.

4. **Multiple elicitations per tool call:** A Medium article (Aug 2025) documented that multiple sequential elicitation requests within a single tool call are buggy in the TypeScript SDK. Python SDK status unknown — test this in Phase 4 before designing any tool that needs more than one elicitation round.

5. **mcp.wyretechnology.com gateway:** Confirm gateway supports Streamable HTTP transport and SSE session management for hosted deployment. STDIO-only gateways would require the HTTP transport to be exposed via a sidecar.

---

*WYRE Technology | usaspending-mcp PRD v1.0 | February 2026 | Prepared for Claude Code handoff*