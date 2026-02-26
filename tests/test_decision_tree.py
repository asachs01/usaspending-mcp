"""Tests for decision tree router and elicitor."""

from usaspending_mcp.decision_tree.elicitor import (
    build_missing_params_schema,
    build_missing_params_message,
)
from usaspending_mcp.decision_tree.router import (
    check_missing,
    check_search_awards_params,
    make_error_response,
    QUERY_SPENDING_PARAMS,
    MANAGE_DOWNLOAD_PARAMS,
)


def test_build_schema_basic():
    missing = {
        "fiscal_year": {"type": "integer", "description": "FY year"},
        "keyword": {"type": "string", "description": "Search term"},
    }
    schema = build_missing_params_schema(missing)
    assert schema["type"] == "object"
    assert "fiscal_year" in schema["properties"]
    assert schema["properties"]["fiscal_year"]["type"] == "integer"
    assert "fiscal_year" in schema["required"]


def test_build_schema_with_enum():
    missing = {
        "award_type": {
            "type": "string",
            "description": "Award type",
            "enum": ["contract", "grant"],
        },
    }
    schema = build_missing_params_schema(missing)
    assert schema["properties"]["award_type"]["enum"] == ["contract", "grant"]


def test_build_schema_optional():
    missing = {
        "note": {"type": "string", "description": "Optional note", "required": False},
    }
    schema = build_missing_params_schema(missing)
    assert "note" not in schema["required"]


def test_build_message():
    missing = {
        "breakdown": {
            "type": "string",
            "description": "Category",
            "enum": ["agency", "budget_function"],
        },
    }
    msg = build_missing_params_message("query_spending", missing)
    assert "query_spending" in msg
    assert "breakdown" in msg
    assert "agency" in msg


def test_check_missing_all_provided():
    result = check_missing(
        {"breakdown": "agency"},
        QUERY_SPENDING_PARAMS,
    )
    assert result == {}


def test_check_missing_none_provided():
    result = check_missing({}, QUERY_SPENDING_PARAMS)
    assert "breakdown" in result


def test_check_missing_confirmed():
    result = check_missing({}, MANAGE_DOWNLOAD_PARAMS)
    assert "confirmed" in result

    result2 = check_missing({"confirmed": True}, MANAGE_DOWNLOAD_PARAMS)
    assert result2 == {}


def test_search_awards_keyword_sufficient():
    assert check_search_awards_params({"keyword": "cyber"}) is None


def test_search_awards_agency_sufficient():
    assert check_search_awards_params({"agency_name": "DOD"}) is None


def test_search_awards_neither_provided():
    missing = check_search_awards_params({})
    assert missing is not None
    assert "keyword" in missing
    assert "agency_name" in missing


def test_make_error_response():
    resp = make_error_response("query_spending", {
        "breakdown": QUERY_SPENDING_PARAMS["breakdown"],
    })
    assert "error" in resp
    assert "breakdown" in resp["missing_parameters"]
    assert "schema" in resp
