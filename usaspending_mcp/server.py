"""Entry point — transport detection and MCP server setup."""

import argparse
import os
import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "USASpending",
    instructions=(
        "MCP server for querying US federal spending data from "
        "api.usaspending.gov. Covers awards, agencies, recipients, "
        "spending breakdowns, disaster funding, federal accounts, "
        "and bulk downloads."
    ),
    json_response=True,
)

# Import tool modules so they register with @mcp.tool()
import usaspending_mcp.tools.registry  # noqa: F401


def _detect_transport() -> str:
    """Detect transport mode from args, env, or stdin state."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--transport", choices=["stdio", "http"], default=None)
    parser.add_argument("--port", type=int, default=None)
    args, _ = parser.parse_known_args()

    # Explicit flag takes priority
    if args.transport:
        return args.transport

    # Environment variable override
    env_transport = os.environ.get("USASPENDING_MCP_TRANSPORT", "").lower()
    if env_transport in ("http", "stdio"):
        return env_transport

    # If stdin is a TTY (interactive), we can't do STDIO transport
    if sys.stdin.isatty():
        print(
            "Usage: usaspending-mcp [--transport stdio|http] [--port PORT]\n"
            "  STDIO mode: pipe input or use --transport stdio\n"
            "  HTTP mode:  --transport http [--port 8765]",
            file=sys.stderr,
        )
        sys.exit(1)

    # Piped stdin → default to STDIO
    return "stdio"


def _get_port() -> int:
    """Get HTTP port from args or env."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--port", type=int, default=None)
    args, _ = parser.parse_known_args()
    if args.port:
        return args.port
    return int(os.environ.get("USASPENDING_MCP_PORT", "8765"))


def main_stdio():
    """Entry point for STDIO transport."""
    mcp.run(transport="stdio")


def main_http():
    """Entry point for HTTP transport."""
    port = _get_port()
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)


def main():
    """Auto-detect transport and run."""
    transport = _detect_transport()
    if transport == "http":
        main_http()
    else:
        main_stdio()


if __name__ == "__main__":
    main()
