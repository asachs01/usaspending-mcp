"""Thin async httpx wrapper for api.usaspending.gov.

All methods return parsed JSON (dict/list). No caching here — that's
handled by client/cache.py. This module is purely HTTP concerns.
"""

from __future__ import annotations

import httpx

BASE_URL = "https://api.usaspending.gov"

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Lazy-init the shared async client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=BASE_URL,
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
            ),
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"Accept": "application/json"},
        )
    return _client


async def close() -> None:
    """Close the shared client (call on server shutdown)."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── Agency endpoints ──────────────────────────────────────────────────

async def get_agencies() -> list[dict]:
    """Fetch all toptier agencies."""
    r = await _get_client().get("/api/v2/references/toptier_agencies/")
    r.raise_for_status()
    return r.json().get("results", [])


async def get_agency(toptier_code: str) -> dict:
    """Agency overview by toptier code."""
    r = await _get_client().get(f"/api/v2/agency/{toptier_code}/")
    r.raise_for_status()
    return r.json()


async def get_agency_breakdown(toptier_code: str, breakdown: str, **params) -> dict:
    """Agency sub-endpoint (budgetary_resources, sub_agency, etc.)."""
    r = await _get_client().get(
        f"/api/v2/agency/{toptier_code}/{breakdown}/",
        params=params,
    )
    r.raise_for_status()
    return r.json()


# ── Award endpoints ───────────────────────────────────────────────────

async def search_awards(payload: dict) -> dict:
    """POST search for awards (spending_by_award)."""
    r = await _get_client().post(
        "/api/v2/search/spending_by_award/",
        json=payload,
    )
    r.raise_for_status()
    return r.json()


async def get_award(award_id: str) -> dict:
    """Get full award detail by generated unique award ID."""
    r = await _get_client().get(f"/api/v2/awards/{award_id}/")
    r.raise_for_status()
    return r.json()


async def get_award_funding(payload: dict) -> dict:
    """Award funding breakdown by federal account."""
    r = await _get_client().post("/api/v2/awards/funding/", json=payload)
    r.raise_for_status()
    return r.json()


async def get_award_count(award_id: str) -> dict:
    """Award count by federal account."""
    r = await _get_client().get(
        f"/api/v2/awards/count/federal_account/{award_id}/"
    )
    r.raise_for_status()
    return r.json()


# ── Recipient endpoints ──────────────────────────────────────────────

async def autocomplete_recipient(search_text: str) -> list[dict]:
    """Recipient name autocomplete."""
    r = await _get_client().post(
        "/api/v2/autocomplete/recipient/",
        json={"search_text": search_text},
    )
    r.raise_for_status()
    return r.json().get("results", [])


async def get_recipient(recipient_id: str, year: str = "latest") -> dict:
    """Recipient profile detail."""
    r = await _get_client().get(
        f"/api/v2/recipient/{recipient_id}/",
        params={"year": year},
    )
    r.raise_for_status()
    return r.json()


# ── Spending explorer ────────────────────────────────────────────────

async def get_spending(spending_type: str, filters: dict) -> dict:
    """Spending explorer breakdown."""
    r = await _get_client().post(
        "/api/v2/spending/",
        json={"type": spending_type, "filters": filters},
    )
    r.raise_for_status()
    return r.json()


# ── Disaster/emergency funding ───────────────────────────────────────

async def get_disaster_spending(breakdown: str, payload: dict) -> dict:
    """Disaster spending by breakdown category."""
    r = await _get_client().post(
        f"/api/v2/disaster/{breakdown}/spending/",
        json=payload,
    )
    r.raise_for_status()
    return r.json()


async def get_disaster_loans(breakdown: str, payload: dict) -> dict:
    """Disaster loan data by breakdown category."""
    r = await _get_client().post(
        f"/api/v2/disaster/{breakdown}/loans/",
        json=payload,
    )
    r.raise_for_status()
    return r.json()


# ── Federal/treasury accounts ────────────────────────────────────────

async def list_federal_accounts(payload: dict | None = None) -> dict:
    """List federal accounts."""
    r = await _get_client().post(
        "/api/v2/federal_accounts/",
        json=payload or {},
    )
    r.raise_for_status()
    return r.json()


async def get_federal_account(account_id: str) -> dict:
    """Federal account detail."""
    r = await _get_client().get(f"/api/v2/federal_accounts/{account_id}/")
    r.raise_for_status()
    return r.json()


async def get_treasury_account(tas: str, breakdown: str = "object_class") -> dict:
    """Treasury account data by TAS symbol."""
    r = await _get_client().get(
        f"/api/v2/agency/treasury_account/{tas}/{breakdown}/"
    )
    r.raise_for_status()
    return r.json()


# ── Subawards ────────────────────────────────────────────────────────

async def search_subawards(payload: dict) -> dict:
    """Subaward search."""
    r = await _get_client().post("/api/v2/subawards/", json=payload)
    r.raise_for_status()
    return r.json()


# ── Transactions ─────────────────────────────────────────────────────

async def search_transactions(payload: dict) -> dict:
    """Transaction search."""
    r = await _get_client().post("/api/v2/transactions/", json=payload)
    r.raise_for_status()
    return r.json()


# ── Bulk downloads ───────────────────────────────────────────────────

async def initiate_download(payload: dict) -> dict:
    """Initiate a bulk CSV download job."""
    r = await _get_client().post(
        "/api/v2/bulk_download/awards/",
        json=payload,
    )
    r.raise_for_status()
    return r.json()


async def get_download_status(file_name: str) -> dict:
    """Poll download job status."""
    r = await _get_client().get(
        "/api/v2/bulk_download/status/",
        params={"file_name": file_name},
    )
    r.raise_for_status()
    return r.json()


# ── Reference data ───────────────────────────────────────────────────

async def get_naics_codes() -> list[dict]:
    """Fetch NAICS code reference list."""
    r = await _get_client().get("/api/v2/references/naics/")
    r.raise_for_status()
    return r.json().get("results", [])


async def get_psc_codes() -> list[dict]:
    """Fetch PSC code reference list."""
    r = await _get_client().get("/api/v2/references/psc/")
    r.raise_for_status()
    return r.json().get("results", [])


async def get_cfda_programs() -> list[dict]:
    """Fetch CFDA program list."""
    r = await _get_client().post(
        "/api/v2/references/cfda/totals/",
        json={},
    )
    r.raise_for_status()
    return r.json().get("results", [])


async def get_last_updated() -> dict:
    """Data freshness timestamp."""
    r = await _get_client().get("/api/v2/awards/last_updated/")
    r.raise_for_status()
    return r.json()


async def get_glossary(search_term: str | None = None) -> list[dict]:
    """Glossary terms."""
    params = {}
    if search_term:
        params["search"] = search_term
    r = await _get_client().get("/api/v2/references/glossary/", params=params)
    r.raise_for_status()
    return r.json().get("results", [])


def get_current_fiscal_year() -> int:
    """Compute current US federal fiscal year (starts Oct 1)."""
    from datetime import date

    today = date.today()
    return today.year + 1 if today.month >= 10 else today.year
