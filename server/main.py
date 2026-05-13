"""CDG Windows Agent — FastMCP server entry point.

Transport selection:
    CDG_TRANSPORT=stdio   (default) — for Claude Desktop on the same machine
    CDG_TRANSPORT=tcp     — for cross-session use (agent in RDP, client in console)

Startup sequence (order matters):
    1. guardrail.install()           — patch banned methods before ANY tool import
    2. load CFG                      — TOML config drives everything below
    3. configure HANDLES TTL         — from config.handle_cache.ttl_seconds
    4. register all skill modules
    5. seed dialog rules from config — so auto-dismiss runs without a tool call
    6. install audit middleware       — wraps every registered tool with timing + logging
    7. start handle-cache purge loop — background daemon thread
    8. run transport
"""

import os
import threading
import time

from server import guardrail

guardrail.install()

from mcp.server.fastmcp import FastMCP

from core.config import CFG
from core.handle_cache import HANDLES
from core.logging import log
from core.middleware import install_audit_middleware
from skills import actions, browser, dialogs, discovery, lifecycle, safety, sessions, waits

# Apply TTL from config to the global handle cache.
HANDLES._ttl = CFG.handle_cache.ttl_seconds

mcp = FastMCP("cdg-windows-agent")

# Register all skill modules.
for module in (discovery, actions, lifecycle, waits, dialogs, sessions, browser, safety):
    module.register(mcp)


@mcp.tool()
def ping() -> dict:
    """Health check — verifies the server is alive and returns session info."""
    return {
        "ok": True,
        "session_id": CFG.server.session_id,
        "transport": CFG.server.transport,
        "default_engine": CFG.default_engine,
        "app_overrides": list(CFG.app_overrides.keys()),
        "handle_cache_size": len(HANDLES),
    }


def _seed_dialog_rules() -> None:
    """Register config-driven dialog rules into the background watcher."""
    from skills.dialogs import _RULES, _RULES_LOCK, _ensure_watcher

    rules_to_add = []
    for name, rule in CFG.dialog_rules.items():
        rules_to_add.append({
            "match": {
                "title_re": rule.title_re,
                "class_name": rule.class_name,
            },
            "action": rule.action,
            "target": rule.target,
        })
    if rules_to_add:
        with _RULES_LOCK:
            _RULES.extend(rules_to_add)
        _ensure_watcher()
        log.info("dialog_rules_seeded", count=len(rules_to_add))


def _start_cache_purge_loop(interval: float = 60.0) -> None:
    """Daemon thread that purges expired handle-cache entries every `interval` seconds."""
    def loop():
        while True:
            time.sleep(interval)
            purged = HANDLES.purge_expired()
            if purged:
                log.debug("handle_cache_purge", purged=purged, remaining=len(HANDLES))

    t = threading.Thread(target=loop, daemon=True, name="handle-cache-purge")
    t.start()


def main() -> None:
    _seed_dialog_rules()
    install_audit_middleware(mcp)
    _start_cache_purge_loop()

    log.info(
        "server_starting",
        transport=CFG.server.transport,
        default_engine=CFG.default_engine,
        app_overrides=list(CFG.app_overrides.keys()),
        dialog_rules=list(CFG.dialog_rules.keys()),
    )

    transport = os.environ.get("CDG_TRANSPORT", CFG.server.transport).lower()
    if transport == "tcp":
        from server import transport_tcp
        transport_tcp.run(mcp)
    else:
        from server import transport_stdio
        transport_stdio.run(mcp)


if __name__ == "__main__":
    main()
