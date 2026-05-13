# CDG Windows Agent Framework

An MCP server that lets Claude (or any MCP client) control Windows desktop
applications in the background — without interfering with the operator's active
session. Every action routes through UIA patterns or Win32 messages targeted at
specific HWNDs. Global mouse/keyboard input is structurally impossible at
runtime.

---

## Requirements

- Windows 10/11 (for the agent session; development tooling runs on any OS)
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

Optional, for specific engine fallbacks:
- Tesseract OCR (`tesseract` binary in PATH)
- WinAppDriver.exe (for `winappdriver` engine)
- FlaUI DLLs in `engines/flaui_dlls/` (for `flaui` engine)

---

## Quickstart

```bash
# 1. Clone and install
git clone https://github.com/Acerrito20/Remote-Skill
cd Remote-Skill
uv venv && uv pip install -e ".[dev]"

# 2. Run unit tests (no Windows required)
pytest tests/unit/ -v

# 3. Start the MCP server (stdio, for Claude Desktop on the same machine)
python server/main.py

# 4. Or TCP/SSE transport (for cross-session use)
CDG_TRANSPORT=tcp python server/main.py
```

---

## Windows setup

Run these PowerShell scripts **once** on the target Windows machine, in order:

```powershell
# Create the 'agent' Windows user
.\scripts\setup_agent_user.ps1

# Install OpenSSH server with key auth
.\scripts\setup_openssh.ps1

# Enable RDP Wrapper (concurrent sessions)
.\scripts\enable_rdpwrap.ps1

# Install a virtual display driver
.\scripts\install_virtual_display.ps1

# Register the MCP server as an NSSM service (run as agent user, NOT LocalSystem)
.\scripts\install_service.ps1

# Suppress toasts / focus-assist in the agent session
.\scripts\disable_notifications.ps1
```

After setup, SSH into the `agent` session from your dev machine and confirm
`python --version` works. The NSSM service should then start automatically on
boot.

---

## Claude Desktop integration

Copy `scripts/client_configs/claude_desktop.json` into your Claude Desktop MCP
configuration. For Claude Code use `scripts/client_configs/claude_code.json`.

Both configs point at `server/main.py` via stdio transport. Adjust the
`python` path if needed.

---

## Configuration

All defaults live in `config/default.toml`. Per-app engine overrides live in
`config/app_overrides/<app>.toml`:

```toml
# config/app_overrides/slack.toml
engine = "playwright"
cdp_port = 9222
```

Engine options: `pywinauto` (default), `playwright`, `autohotkey`, `flaui`,
`winappdriver`, `tesseract` (OCR only).

No code changes needed to support a new application — add a one-line TOML
override file.

---

## Tool reference

53 MCP tools across 8 skill modules:

| Module | Tools |
|---|---|
| `discovery` | `list_windows`, `list_processes`, `connect_app`, `get_tree`, `find_element`, `inspect_element`, `find_by_path` |
| `actions` | `invoke`, `set_text`, `get_text`, `select_combo_item`, `toggle_checkbox`, `set_checkbox`, `expand/collapse_tree_node`, `scroll_into_view`, `menu_select`, `background_click`, `background_type`, `send_raw_message`, `virtual_drag`, `drag_screen` |
| `lifecycle` | `start_app`, `kill_app`, `restart_app`, `wait_for_app`, `get_app_state`, `list_app_windows` |
| `waits` | `wait_for`, `wait_for_idle`, `wait_for_window`, `poll_until` |
| `dialogs` | `dismiss_dialog`, `register_dialog_rule`, `list_modal_dialogs`, `screenshot_window` |
| `sessions` | `list_sessions`, `get_session_info`, `lock_session`, `attach_virtual_display` |
| `browser` | `browser_open`, `browser_navigate`, `browser_query`, `browser_click`, `browser_fill`, `browser_eval_js`, `browser_screenshot` |
| `safety` | `assert_background_safe`, `get_audit_log`, `dry_run`, `get_guardrail_status`, `panic_stop`, `clear_stop` |

Plus `ping` (health check) registered directly in `server/main.py`.

---

## Background-safe guarantee

The guardrail (`server/guardrail.py`) patches pywinauto's `BaseWrapper` at
startup. These methods raise `RuntimeError` immediately if called:

```
click_input  double_click_input  right_click_input  move_mouse_input
drag_mouse_input  press_mouse_input  release_mouse_input  type_keys  set_focus
```

`virtual_drag` and `drag_screen` use `SendInput` as a last resort for
GPU-accelerated apps (CapCut, DaVinci Resolve). This is safe because the
server runs inside the isolated `agent` RDP session — `SendInput` there moves
the agent's virtual cursor on the virtual display only and never affects the
operator's real cursor.

---

## Testing

```bash
# Unit tests — run on any OS, no Windows required
pytest tests/unit/ -v

# Integration tests — Windows only, skipped automatically on Linux/macOS
pytest tests/integration/ -v

# Lint + format
ruff check .
ruff format .
```

Unit tests cover all 53 tools via mocks. Integration tests spawn real Notepad
and Calculator processes and verify end-to-end behaviour.

---

## Architecture overview

```
server/main.py          — FastMCP entry; guardrail installed before any import
server/guardrail.py     — patches banned methods at startup

skills/                 — MCP @tool() functions
core/                   — config, handle cache, middleware, audit, retry, selector
engines/                — thin adapters: pywinauto, win32, playwright, ahk, flaui, etc.
config/                 — default.toml + per-app overrides
scripts/                — Windows setup PowerShell scripts
tests/unit/             — cross-platform unit tests (~100 test functions)
tests/integration/      — Windows-only integration tests
```

See [CLAUDE.md](CLAUDE.md) for the full architecture reference.
