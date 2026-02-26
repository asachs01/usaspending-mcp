"""Builds elicitation schemas for missing parameters.

The elicitor inspects which parameters were provided vs required, and
generates a JSON Schema describing what's needed. This is used either
for MCP elicitation (when client supports it) or for generating clear
error messages listing what's missing.
"""

from __future__ import annotations

from typing import Any


def build_missing_params_schema(
    missing: dict[str, dict],
) -> dict:
    """Build a JSON Schema for missing parameters.

    Args:
        missing: Map of param_name -> {type, description, [enum]}
            Example: {"fiscal_year": {"type": "integer", "description": "..."}}

    Returns:
        JSON Schema dict suitable for elicitation/create requestedSchema.
        Only primitive types (string, integer, number, boolean) are used
        per MCP elicitation spec constraints.
    """
    properties = {}
    required = []

    for name, spec in missing.items():
        prop: dict[str, Any] = {
            "type": spec.get("type", "string"),
            "description": spec.get("description", f"Please provide {name}"),
        }
        if "enum" in spec:
            prop["enum"] = spec["enum"]
        if "default" in spec:
            prop["default"] = spec["default"]
        properties[name] = prop
        if spec.get("required", True):
            required.append(name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def build_missing_params_message(
    tool_name: str,
    missing: dict[str, dict],
) -> str:
    """Build a human-readable message about missing parameters.

    Used as fallback when elicitation is not available.
    """
    lines = [f"Missing required parameters for {tool_name}:"]
    for name, spec in missing.items():
        desc = spec.get("description", "")
        type_str = spec.get("type", "string")
        enum_str = ""
        if "enum" in spec:
            enum_str = f" (one of: {', '.join(str(v) for v in spec['enum'])})"
        lines.append(f"  - {name} ({type_str}){enum_str}: {desc}")
    return "\n".join(lines)
