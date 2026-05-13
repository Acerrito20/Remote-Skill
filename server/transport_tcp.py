"""SSE/TCP transport — for cross-session use (agent in RDP, client in console)."""

import os

from mcp.server.fastmcp import FastMCP


def run(mcp: FastMCP) -> None:
    host = os.environ.get("CDG_HOST", "127.0.0.1")
    port = int(os.environ.get("CDG_PORT", "8765"))
    mcp.run(transport="sse", host=host, port=port)
