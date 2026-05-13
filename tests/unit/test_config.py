"""Unit tests for the config loader."""

import textwrap
from pathlib import Path

import pytest

from core.config import Config, load


@pytest.fixture
def config_dir(tmp_path):
    """Minimal config directory with a default.toml."""
    default_toml = tmp_path / "default.toml"
    default_toml.write_text(textwrap.dedent("""
        [server]
        transport = "stdio"
        session_id = "test-session"

        [timeouts]
        connect_seconds = 7.0
        action_seconds = 12.0
        wait_seconds = 20.0

        [retry]
        max_attempts = 5
        base_delay_seconds = 0.2

        [handle_cache]
        ttl_seconds = 120.0

        [audit]
        enabled = true
        path = "logs/test-audit.jsonl"

        [engines]
        default = "pywinauto"

        [dialog_rules]
        save_changes = { title_re = ".*Save.*", class_name = "#32770", action = "click_button", target = "Don't Save" }
    """))
    return tmp_path


def test_loads_server_config(config_dir):
    cfg = load(config_dir)
    assert cfg.server.transport == "stdio"
    assert cfg.server.session_id == "test-session"


def test_loads_timeouts(config_dir):
    cfg = load(config_dir)
    assert cfg.timeouts.connect_seconds == 7.0
    assert cfg.timeouts.action_seconds == 12.0
    assert cfg.timeouts.wait_seconds == 20.0


def test_loads_retry(config_dir):
    cfg = load(config_dir)
    assert cfg.retry.max_attempts == 5
    assert cfg.retry.base_delay_seconds == 0.2


def test_loads_handle_cache(config_dir):
    cfg = load(config_dir)
    assert cfg.handle_cache.ttl_seconds == 120.0


def test_loads_dialog_rules(config_dir):
    cfg = load(config_dir)
    assert "save_changes" in cfg.dialog_rules
    rule = cfg.dialog_rules["save_changes"]
    assert rule.title_re == ".*Save.*"
    assert rule.target == "Don't Save"


def test_app_override_from_toml_file(config_dir):
    overrides_dir = config_dir / "app_overrides"
    overrides_dir.mkdir()
    (overrides_dir / "slack.toml").write_text(textwrap.dedent("""
        [app]
        executable = "slack.exe"
        engine = "playwright"
        cdp_port = 9222
    """))
    cfg = load(config_dir)
    assert cfg.engine_for("slack.exe") == "playwright"
    assert cfg.engine_for("notepad.exe") == "pywinauto"


def test_engine_for_unknown_returns_default(config_dir):
    cfg = load(config_dir)
    assert cfg.engine_for("unknown_app.exe") == "pywinauto"


def test_cdp_url_for_playwright_app(config_dir):
    overrides_dir = config_dir / "app_overrides"
    overrides_dir.mkdir()
    (overrides_dir / "slack.toml").write_text(textwrap.dedent("""
        [app]
        executable = "slack.exe"
        engine = "playwright"
        cdp_port = 9333
    """))
    cfg = load(config_dir)
    assert cfg.cdp_url_for("slack.exe") == "http://localhost:9333"


def test_override_for_returns_none_for_unknown(config_dir):
    cfg = load(config_dir)
    assert cfg.override_for("mystery.exe") is None


def test_missing_config_dir_returns_defaults():
    cfg = load(Path("/nonexistent/path/that/does/not/exist"))
    assert isinstance(cfg, Config)
    assert cfg.server.transport == "stdio"
    assert cfg.default_engine == "pywinauto"


def test_multiple_app_overrides(config_dir):
    overrides_dir = config_dir / "app_overrides"
    overrides_dir.mkdir()
    (overrides_dir / "slack.toml").write_text("[app]\nexecutable=\"slack.exe\"\nengine=\"playwright\"\n")
    (overrides_dir / "legacy.toml").write_text("[app]\nexecutable=\"legacy.exe\"\nengine=\"autohotkey\"\n")
    cfg = load(config_dir)
    assert cfg.engine_for("slack.exe") == "playwright"
    assert cfg.engine_for("legacy.exe") == "autohotkey"
    assert len(cfg.app_overrides) == 2
