# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this project is

**CDG Windows Agent Framework** — an MCP server that lets Claude (or any MCP client) control
Windows desktop applications in the background, without interfering with the user's active session.

The core contract: **every action routes through UIA patterns or Win32 messages targeted at specific
HWNDs — never through global mouse/keyboard input.** The guardrail enforces this at startup by
patching pywinauto's `BaseWrapper` to make focus-stealing methods structurally impossible.

The server runs inside an isolated Windows user session (`agent` user, accessed over RDP while the
operator's own session stays live on the console). A virtual display driver gives that session a
stable monitor even with no physical display attached.

---

## Build and test commands

```bash
# Install dependencies (Python 3.12+, uv recommended)
uv venv
uv pip install -e ".[dev]"

# Run all unit tests (no Windows required)
pytest tests/unit/ -v

# Run a single test file
pytest tests/unit/test_config.py

# Run integration tests (Windows only — skipped automatically on Linux/macOS)
pytest tests/integration/

# Lint + format
ruff check .
ruff format .

# Start the MCP server (stdio transport, for Claude Desktop on same machine)
python server/main.py

# Start with TCP/SSE transport (for cross-session use)
CDG_TRANSPORT=tcp python server/main.py

# Install pre-commit hooks (dev machines)
pre-commit install
```

---

## Architecture

### Layer summary

```
Layer 0: Windows host setup (OpenSSH, RDP Wrapper, virtual display, agent user, NSSM service)
Layer 1: Dev tooling (VS Code Remote-SSH, Python 3.12, uv, pytest)
Layer 2: UI automation engines (pywinauto, pywin32, comtypes, FlaUI, AutoHotkey, Playwright, Tesseract)
Layer 3: Inspection tools (Inspect.exe, FlaUInspect, Spy++, AccEvent) — dev-only, not runtime deps
Layer 4: MCP tool surface — skills/ modules
Layer 5: Cross-cutting infrastructure — core/ modules
Layer 6: Transport (stdio for local, SSE/TCP for cross-session)
Layer 7: Client integration (Claude Desktop, Claude Code, custom orchestrator)
```

### Build order (incremental, each step is independently testable)

1. Layer 0 + Layer 1 → SSH from VS Code into an `agent` session, `python --version` works.
2. `skills/discovery.py` + `skills/actions.py` on plain pywinauto → script opens Notepad, types without focus theft.
3. `server/guardrail.py` install → any `click_input()` call raises immediately.
4. `server/main.py` + Claude Desktop stdio config → Claude opens Notepad, cursor untouched.
5. `skills/lifecycle.py`, `skills/waits.py`, `skills/dialogs.py` → survives unexpected "Save changes?" dialogs.
6. TCP transport + `skills/sessions.py` → agent in one Windows session, client in another.
7. `skills/browser.py` → Playwright bridge for Electron apps (Slack, VS Code, Notion).
8. `core/audit.py` + `skills/safety.py` → production safety, hourly unattended operation.
9. Engine fallbacks (`engines/flaui_adapter.py`, `engines/autohotkey_adapter.py`) → only when a specific app forces them.

### Module map

```
server/
  main.py               — FastMCP entry; guardrail installed before any tool registers
  guardrail.py          — patches BaseWrapper banned methods at startup
  transport_stdio.py    — stdio (local)
  transport_tcp.py      — SSE/TCP (cross-session); CDG_HOST, CDG_PORT env vars

skills/                 — MCP @tool() functions; each module has register(mcp) called from main
  discovery.py          — list_windows, list_processes, connect_app, get_tree, find_element, inspect_element, find_by_path
  actions.py            — invoke, set_text, get_text, select_combo_item, toggle_checkbox, set_checkbox,
                          expand/collapse_tree_node, scroll_into_view, menu_select, background_click,
                          background_type, send_raw_message
  lifecycle.py          — start_app, kill_app, restart_app, wait_for_app, get_app_state, list_app_windows
  waits.py              — wait_for, wait_for_idle, wait_for_window, poll_until
  dialogs.py            — dismiss_dialog, register_dialog_rule, list_modal_dialogs, screenshot_window;
                          background watcher thread auto-dismisses matched dialogs
  sessions.py           — list_sessions, get_session_info, lock_session, attach_virtual_display
  browser.py            — browser_open, browser_navigate, browser_query, browser_click, browser_fill,
                          browser_eval_js, browser_screenshot (Playwright CDP bridge)
  safety.py             — assert_background_safe, get_audit_log, dry_run, get_guardrail_status, panic_stop

core/
  config.py             — CFG singleton: reads default.toml + app_overrides/*.toml; engine_for(), override_for(), cdp_url_for()
  handle_cache.py       — HandleCache: opaque string handles → live COM wrappers; TTL from CFG; auto-purge daemon
  middleware.py         — install_audit_middleware(): wraps every registered tool with timing + AUDIT.record()
  selector.py           — "Window[title~='Notepad'] > Edit[auto_id='15']" parser + pywinauto resolver
  retry.py              — @with_retry decorator with exponential backoff
  audit.py              — append-only JSON Lines audit log; AUDIT singleton
  com_threading.py      — @com_thread / @com_thread_async: CoInitialize per thread
  logging.py            — structlog JSON Lines to stderr

engines/                — low-level adapters; skills/ picks the right one per app via config
  pywinauto_adapter.py  — primary (UIA + Win32 backends)
  win32_adapter.py      — raw user32/SendMessage/PostMessage
  playwright_adapter.py — CDP connect for Electron apps
  autohotkey_adapter.py — AHK v2 subprocess wrapper for legacy apps
  flaui_adapter.py      — .NET bridge via pythonnet for WPF edge cases

config/
  default.toml          — server, timeouts, retry, handle_cache, audit, engine, dialog_rules defaults
  app_overrides/        — per-app engine selection (slack.toml → playwright, legacy-erp.toml → autohotkey)

scripts/
  setup_agent_user.ps1        — create 'agent' Windows user
  enable_rdpwrap.ps1          — install RDP Wrapper for concurrent sessions
  install_virtual_display.ps1 — virtual monitor driver (IddSampleDriver / usbmmidd / Parsec)
  install_service.ps1         — NSSM service install (must run as agent user, not LocalSystem)
  disable_notifications.ps1   — suppress toasts, focus-assist, game bar (run as agent user)
  client_configs/             — ready-to-use Claude Desktop + Claude Code MCP JSON configs
```

---

## Critical constraints

### The background-safe rule (never break this)

**Banned methods** — the guardrail raises `RuntimeError` if any of these are called after `guardrail.install()`:

```
click_input  double_click_input  right_click_input  move_mouse_input
drag_mouse_input  press_mouse_input  release_mouse_input  type_keys  set_focus
```

**Allowed alternatives:**
- Click/activate → `elem.invoke()` (UIA InvokePattern)
- Type text → `elem.set_edit_text()` or `PostMessage(WM_CHAR)`
- Click in client area → `PostMessage(WM_LBUTTONDOWN/UP, MAKELONG(x, y))`
- Menu item → `win.menu_select("File", "Save As")` or `WM_COMMAND`
- Checkbox → `elem.toggle()` / `elem.get_toggle_state()`

### Element handles vs COM pointers

COM pointers never cross the MCP JSON-RPC boundary. Every tool returns an opaque handle string
(`el_a1b2c3d4`). The `HandleCache` maps handles → live wrappers with a 5-minute TTL.
A stale handle returns `{"error": "stale_handle"}` — the agent must re-discover the element.

### Engine selection is config, not code

Adding support for a new app is a one-line change in `config/app_overrides/<app>.toml` —
no code change needed. `CFG.engine_for(executable)` resolves the engine at runtime.
`connect_app` and `start_app` both call `CFG.override_for()` automatically.

For Electron apps (`engine = "playwright"`), `start_app` injects
`--remote-debugging-port=<port>` automatically and returns the CDP URL to pass to `browser_open`.

### NSSM service must run as `agent` user — not LocalSystem

`LocalSystem` runs in Session 0, which has no interactive desktop. UIA returns nothing there.
The NSSM `ObjectName` must be `.\agent` with the agent user's password.

### No time.sleep() in tool bodies

Use `wait_for`, `wait_for_idle`, `wait_for_window`, or `poll_until`. Races against the UI thread
are the single biggest source of flaky automation.

### Audit log from day one

`core/audit.py` AUDIT singleton is always active. Never disable it. Never rotate or delete
`logs/audit.jsonl`. It is the forensic record of every unattended action.

---

## Adding a new skill

1. Add `@mcp.tool()` decorated function inside the appropriate `skills/*.py` module's `register(mcp)` function.
2. Return `{"error": "..."}` on failure, never raise — the MCP boundary expects a dict.
3. Annotate all parameters; FastMCP generates the tool schema from type hints.
4. For any new background action, verify it isn't in `BANNED_METHODS` and add a unit test.

## Adding a new engine

1. Create `engines/<name>_adapter.py` with `connect()` / `launch()` functions.
2. Add an entry to `config/app_overrides/<app>.toml` with `engine = "<name>"`.
3. Handle the new engine name in `connect_app` / `start_app` if it needs special startup logic (e.g. the CDP port injection for playwright).

---

## Test framework

Unit tests (`tests/unit/`) run on any OS — no Windows required. They mock pywinauto.

Integration tests (`tests/integration/`) require Windows + real apps. They are marked with
`@pytest.mark.skipif(platform.system() != "Windows", ...)` and skipped automatically on Linux/macOS.

Test utilities for spawning real apps:

```python
@pytest.fixture
def notepad_pid():
    proc = subprocess.Popen(["notepad.exe"])
    time.sleep(0.8)
    yield proc.pid
    try:
        proc.kill()
        proc.wait(timeout=3)
    except Exception:
        pass
```

Always kill spawned processes in fixture teardown — even on test failure.
