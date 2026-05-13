"""Session / display skills — manage which Windows session the agent operates against."""

from __future__ import annotations

from core.handle_cache import HANDLES


def register(mcp) -> None:

    @mcp.tool()
    def list_sessions() -> list[dict]:
        """List all active Windows logon sessions (RDP + console)."""
        try:
            import subprocess
            out = subprocess.check_output(
                ["query", "session"], stderr=subprocess.STDOUT, text=True
            )
            lines = [l for l in out.splitlines() if l.strip()]
            sessions = []
            for line in lines[1:]:  # skip header
                parts = line.split()
                if len(parts) >= 2:
                    sessions.append({
                        "name": parts[0].lstrip(">"),
                        "id": parts[1] if len(parts) > 1 else "",
                        "state": parts[2] if len(parts) > 2 else "",
                        "raw": line.strip(),
                    })
            return sessions
        except Exception as exc:
            return [{"error": str(exc)}]

    @mcp.tool()
    def get_session_info() -> dict:
        """Get the current session's resolution, DPI, and basic state."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            width = user32.GetSystemMetrics(0)   # SM_CXSCREEN
            height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            return {"resolution": f"{width}x{height}"}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def lock_session() -> dict:
        """Lock the current workstation (agent session only — never user's session)."""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def attach_virtual_display(width: int = 1920, height: int = 1080) -> dict:
        """Attempt to activate a virtual display adapter.

        Requires a virtual display driver (IddSampleDriver, usbmmidd, or Parsec)
        to be installed. This tool signals intent; actual driver activation varies
        by driver — see scripts/install_virtual_display.ps1.
        """
        return {
            "note": (
                "Virtual display attachment requires an installed driver. "
                f"Requested: {width}x{height}. "
                "Run scripts/install_virtual_display.ps1 on the target machine first."
            )
        }
