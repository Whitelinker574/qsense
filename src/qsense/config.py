"""Configuration loading and first-run interactive setup."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

CONFIG_DIR = Path.home() / ".qsense"
CONFIG_FILE = CONFIG_DIR / ".env"

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "google/gemini-3-flash-preview"
DEFAULT_TIMEOUT = 60


@dataclass
class Config:
    api_key: str
    base_url: str
    model: str
    timeout: int


def _load_config_file() -> dict[str, str]:
    """Read key-value pairs from ``~/.qsense/.env``."""
    if CONFIG_FILE.exists():
        return dotenv_values(CONFIG_FILE)
    return {}


def _sanitize(value: str) -> str:
    """Strip newlines and carriage returns to prevent .env injection."""
    return value.replace("\n", "").replace("\r", "")


def _write_config(values: dict[str, str]) -> None:
    """Write config values to ~/.qsense/.env with restricted permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(0o700)
    lines = [
        f"QSENSE_API_KEY={_sanitize(values.get('QSENSE_API_KEY', ''))}",
        f"QSENSE_BASE_URL={_sanitize(values.get('QSENSE_BASE_URL', DEFAULT_BASE_URL))}",
        f"QSENSE_MODEL={_sanitize(values.get('QSENSE_MODEL', DEFAULT_MODEL))}",
    ]
    CONFIG_FILE.write_text("\n".join(lines) + "\n")
    CONFIG_FILE.chmod(0o600)


def _ask(label: str, default: str | None = None) -> str:
    """Prompt the user for a value, with optional pre-filled default."""
    try:
        if default:
            raw = input(f"{label} [{default}]: ").strip()
            return raw or default
        while True:
            raw = input(f"{label}: ").strip()
            if raw:
                return raw
            print("[qsense] This field is required.", file=sys.stderr)
    except (EOFError, KeyboardInterrupt):
        print("\n[qsense] Setup cancelled.", file=sys.stderr)
        sys.exit(1)


def run_first_time_setup() -> dict[str, str]:
    """Guide a first-time user through interactive configuration."""
    print("[qsense] First-run setup — your answers will be saved to ~/.qsense/.env")
    api_key = _ask("API key")
    base_url = _ask("Base URL", DEFAULT_BASE_URL)
    model = _ask("Default model", DEFAULT_MODEL)

    values = {"QSENSE_API_KEY": api_key, "QSENSE_BASE_URL": base_url, "QSENSE_MODEL": model}
    _write_config(values)
    print(f"[qsense] Configuration saved to {CONFIG_FILE}")
    return values


def show_config() -> dict[str, str]:
    """Return the current persisted configuration as a dict."""
    stored = _load_config_file()
    return {
        "api_key": _mask(stored.get("QSENSE_API_KEY", "")),
        "base_url": stored.get("QSENSE_BASE_URL", DEFAULT_BASE_URL),
        "model": stored.get("QSENSE_MODEL", DEFAULT_MODEL),
    }


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return value[:6] + "..." + value[-4:]


def update_config(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> None:
    """Update specific fields in ``~/.qsense/.env``, keeping others intact."""
    stored = _load_config_file()

    if api_key is not None:
        stored["QSENSE_API_KEY"] = api_key
    if base_url is not None:
        stored["QSENSE_BASE_URL"] = base_url
    if model is not None:
        stored["QSENSE_MODEL"] = model

    _write_config(stored)


def load_config(
    *,
    model: str | None = None,
    timeout: int | None = None,
) -> Config:
    """Build a Config with priority: CLI flags > env vars > config file."""
    stored = _load_config_file()

    api_key = os.environ.get("QSENSE_API_KEY") or stored.get("QSENSE_API_KEY")

    if not api_key:
        if sys.stdin.isatty():
            stored = run_first_time_setup()
            api_key = stored["QSENSE_API_KEY"]
        else:
            print(
                "[qsense] Missing API key. Run 'qsense init' to configure, "
                "or: qsense init --api-key sk-xxx",
                file=sys.stderr,
            )
            sys.exit(1)

    resolved_base_url = (
        os.environ.get("QSENSE_BASE_URL")
        or stored.get("QSENSE_BASE_URL")
        or DEFAULT_BASE_URL
    )
    resolved_model = (
        model
        or os.environ.get("QSENSE_MODEL")
        or stored.get("QSENSE_MODEL")
        or DEFAULT_MODEL
    )
    resolved_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT

    return Config(
        api_key=api_key,
        base_url=resolved_base_url,
        model=resolved_model,
        timeout=resolved_timeout,
    )
