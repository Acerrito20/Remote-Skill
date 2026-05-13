"""CDG Windows Agent — FastMCP server entry point.

Transport selection:
    CDG_TRANSPORT=stdio   (default) — for Claude Desktop on the same machine
    CDG_TRANSPORT=tcp     — for cross-session use (agent in RDP, client in console)
"""

import os
import sys

# Guardrail must be installed before any tool module is imported.
from server import guardrail

guardrail.install()

from mcp.server.fastmcp import FastMCP

from skills import actions, browser, dialogs, discovery, lifecycle, safety, sessions, waits

mcp = FastMCP("cdg-windows-agent")

# Register all skill modules.
for module in (discovery, actions, lifecycle, waits, dialogs, sessions, browser, safety):
    module.register(mcp)


def main() -> None:
    transport = os.environ.get("CDG_TRANSPORT", "stdio").lower()
    if transport == "tcp":
        from server import transport_tcp
        transport_tcp.run(mcp)
    else:
        from server import transport_stdio
        transport_stdio.run(mcp)


if __name__ == "__main__":
    main()
