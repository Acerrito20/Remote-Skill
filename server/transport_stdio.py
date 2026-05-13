"""stdio transport — for local Claude Desktop on the same machine."""

from mcp.server.fastmcp import FastMCP


def run(mcp: FastMCP) -> None:
    mcp.run()  # defaults to stdio
