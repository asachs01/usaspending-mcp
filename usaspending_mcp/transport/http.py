"""Streamable HTTP + SSE transport handler.

FastMCP handles the heavy lifting (Starlette app, SSE, session management).
This module provides configuration and any custom middleware.
"""

from __future__ import annotations

import os


def get_http_config() -> dict:
    """Get HTTP transport configuration from env."""
    return {
        "host": os.environ.get("USASPENDING_MCP_HOST", "0.0.0.0"),
        "port": int(os.environ.get("USASPENDING_MCP_PORT", "8765")),
    }
