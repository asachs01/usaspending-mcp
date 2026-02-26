"""Parameter inspection and missing-param detection for decision-tree routing.

Each tool defines its parameter requirements. The router inspects what was
provided and determines what's missing before the tool can execute.
"""

from __future__ import annotations

from typing import Any

from usaspending_mcp.decision_tree.elicitor import (
    build_missing_params_message,
    build_missing_params_schema,
)


# ── Parameter requirement definitions per tool ────────────────────────

SEARCH_AWARDS_PARAMS = {
    "keyword": {
        "type": "string",
        "description": "Free text search term for awards",
        "required": False,
    },
    "agency_name": {
        "type": "string",
        "description": "Agency name to search within",
        "required": False,
    },
    "fiscal_year": {
        "type": "integer",
        "description": "Federal fiscal year (Oct-Sep)",
        "required": False,
    },
    "award_type": {
        "type": "string",
        "description": "Type of award to search for",
        "enum": ["contract", "grant", "loan", "direct_payment", "idv", "other"],
        "required": False,
    },
}

QUERY_SPENDING_PARAMS = {
    "breakdown": {
        "type": "string",
        "description": "Spending breakdown category",
        "enum": ["agency", "budget_function", "object_class", "program_activity"],
        "required": True,
    },
}

QUERY_DISASTER_PARAMS = {
    "disaster_code": {
        "type": "string",
        "description": "DEFC (Disaster Emergency Fund Code) value",
        "required": True,
    },
}

MANAGE_DOWNLOAD_PARAMS = {
    "confirmed": {
        "type": "boolean",
        "description": "Confirm you want to initiate this download (may generate large files)",
        "required": True,
    },
}


def check_missing(
    provided: dict[str, Any],
    requirements: dict[str, dict],
) -> dict[str, dict]:
    """Check which required parameters are missing.

    Returns dict of missing param definitions (empty if all provided).
    """
    missing = {}
    for name, spec in requirements.items():
        if spec.get("required", True) and provided.get(name) is None:
            missing[name] = spec
    return missing


def check_search_awards_params(provided: dict[str, Any]) -> dict[str, dict] | None:
    """Special check for search_awards: at least keyword OR agency_name required."""
    if provided.get("keyword") or provided.get("agency_name"):
        return None  # Sufficient

    # Neither provided — need at least one
    return {
        "keyword": SEARCH_AWARDS_PARAMS["keyword"],
        "agency_name": SEARCH_AWARDS_PARAMS["agency_name"],
    }


def make_error_response(tool_name: str, missing: dict[str, dict]) -> dict:
    """Build a structured error response for missing parameters."""
    return {
        "error": build_missing_params_message(tool_name, missing),
        "missing_parameters": list(missing.keys()),
        "schema": build_missing_params_schema(missing),
        "hint": "Please provide the missing parameters and try again.",
    }
