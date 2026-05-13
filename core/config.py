"""Runtime configuration loader.

Reads config/default.toml then merges all config/app_overrides/*.toml files.
Exposes a typed Config dataclass and a module-level singleton loaded at import time.

Usage:
    from core.config import CFG

    engine = CFG.engine_for("slack.exe")      # -> "playwright"
    cdp_url = CFG.cdp_url_for("slack.exe")    # -> "http://localhost:9222"
    timeout = CFG.timeouts.connect_seconds    # -> 5.0
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            tomllib = None  # type: ignore[assignment]


_CONFIG_DIR = Path(__file__).parent.parent / "config"


@dataclass
class TimeoutsConfig:
    connect_seconds: float = 5.0
    action_seconds: float = 10.0
    wait_seconds: float = 15.0


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 0.1


@dataclass
class HandleCacheConfig:
    ttl_seconds: float = 300.0


@dataclass
class AuditConfig:
    enabled: bool = True
    path: str = "logs/audit.jsonl"


@dataclass
class ServerConfig:
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8765
    session_id: str = "agent-session"


@dataclass
class AppOverride:
    executable: str = ""
    engine: str = "pywinauto"
    backend: str = "uia"
    cdp_port: int = 9222
    cdp_url: str = ""
    script_dir: str = ""

    def effective_cdp_url(self) -> str:
        return self.cdp_url or f"http://localhost:{self.cdp_port}"


@dataclass
class DialogRule:
    title_re: str = ""
    class_name: str = "#32770"
    action: str = "click_button"
    target: str = "OK"


@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    timeouts: TimeoutsConfig = field(default_factory=TimeoutsConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    handle_cache: HandleCacheConfig = field(default_factory=HandleCacheConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    default_engine: str = "pywinauto"
    app_overrides: dict[str, AppOverride] = field(default_factory=dict)
    dialog_rules: dict[str, DialogRule] = field(default_factory=dict)

    def engine_for(self, executable: str) -> str:
        """Return the engine name for a given executable basename."""
        key = Path(executable).name.lower()
        override = self.app_overrides.get(key)
        return override.engine if override else self.default_engine

    def override_for(self, executable: str) -> AppOverride | None:
        """Return the full AppOverride for an executable, or None."""
        key = Path(executable).name.lower()
        return self.app_overrides.get(key)

    def cdp_url_for(self, executable: str) -> str:
        """Return the CDP URL for an Electron app, or the default."""
        override = self.override_for(executable)
        if override and override.engine == "playwright":
            return override.effective_cdp_url()
        return "http://localhost:9222"


def _load_toml(path: Path) -> dict:
    if tomllib is None:
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def _parse_app_override(data: dict, executable: str = "") -> AppOverride:
    return AppOverride(
        executable=data.get("executable", executable),
        engine=data.get("engine", "pywinauto"),
        backend=data.get("backend", "uia"),
        cdp_port=int(data.get("cdp_port", 9222)),
        cdp_url=data.get("cdp_url", ""),
        script_dir=data.get("script_dir", ""),
    )


def _parse_dialog_rule(data: dict) -> DialogRule:
    return DialogRule(
        title_re=data.get("title_re", ""),
        class_name=data.get("class_name", "#32770"),
        action=data.get("action", "click_button"),
        target=data.get("target", "OK"),
    )


def load(config_dir: Path = _CONFIG_DIR) -> Config:
    """Load default.toml then merge all app_overrides/*.toml files."""
    defaults_path = config_dir / "default.toml"
    raw = _load_toml(defaults_path)

    # Server
    srv = raw.get("server", {})
    server = ServerConfig(
        transport=srv.get("transport", "stdio"),
        host=srv.get("host", "127.0.0.1"),
        port=int(srv.get("port", 8765)),
        session_id=srv.get("session_id", "agent-session"),
    )

    # Timeouts
    t = raw.get("timeouts", {})
    timeouts = TimeoutsConfig(
        connect_seconds=float(t.get("connect_seconds", 5.0)),
        action_seconds=float(t.get("action_seconds", 10.0)),
        wait_seconds=float(t.get("wait_seconds", 15.0)),
    )

    # Retry
    r = raw.get("retry", {})
    retry = RetryConfig(
        max_attempts=int(r.get("max_attempts", 3)),
        base_delay_seconds=float(r.get("base_delay_seconds", 0.1)),
    )

    # Handle cache
    hc = raw.get("handle_cache", {})
    handle_cache = HandleCacheConfig(
        ttl_seconds=float(hc.get("ttl_seconds", 300.0)),
    )

    # Audit
    a = raw.get("audit", {})
    audit = AuditConfig(
        enabled=bool(a.get("enabled", True)),
        path=a.get("path", "logs/audit.jsonl"),
    )

    # Default engine
    engines_raw = raw.get("engines", {})
    default_engine = engines_raw.get("default", "pywinauto")

    # Dialog rules from default.toml
    dialog_rules: dict[str, DialogRule] = {}
    for name, rule_data in raw.get("dialog_rules", {}).items():
        if isinstance(rule_data, dict):
            dialog_rules[name] = _parse_dialog_rule(rule_data)

    # App overrides from default.toml [apps.<exe>] sections
    app_overrides: dict[str, AppOverride] = {}
    for exe, override_data in raw.get("apps", {}).items():
        if isinstance(override_data, dict):
            app_overrides[exe.lower()] = _parse_app_override(override_data, exe)

    # Merge per-app TOML files from app_overrides/
    overrides_dir = config_dir / "app_overrides"
    if overrides_dir.exists():
        for toml_file in sorted(overrides_dir.glob("*.toml")):
            app_raw = _load_toml(toml_file)
            app_data = app_raw.get("app", {})
            exe = app_data.get("executable", toml_file.stem).lower()
            if not exe:
                continue
            app_overrides[exe] = _parse_app_override(app_data, exe)
            # Dialog rules defined inside an app override file
            for name, rule_data in app_raw.get("dialog_rules", {}).items():
                if isinstance(rule_data, dict):
                    dialog_rules[name] = _parse_dialog_rule(rule_data)

    return Config(
        server=server,
        timeouts=timeouts,
        retry=retry,
        handle_cache=handle_cache,
        audit=audit,
        default_engine=default_engine,
        app_overrides=app_overrides,
        dialog_rules=dialog_rules,
    )


# Module-level singleton — loaded once at import time.
CFG: Config = load()
