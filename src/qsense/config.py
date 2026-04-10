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
DEFAULT_IMAGE_MODEL = "google/gemini-3-flash-preview"
DEFAULT_AUDIO_MODEL = "google/gemini-3-flash-preview"
DEFAULT_VIDEO_MODEL = "google/gemini-3-flash-preview"
DEFAULT_TIMEOUT = 60

# Config keys for per-modality models
_MODALITY_KEYS = {
    "image": "QSENSE_IMAGE_MODEL",
    "audio": "QSENSE_AUDIO_MODEL",
    "video": "QSENSE_VIDEO_MODEL",
}
_MODALITY_DEFAULTS = {
    "image": DEFAULT_IMAGE_MODEL,
    "audio": DEFAULT_AUDIO_MODEL,
    "video": DEFAULT_VIDEO_MODEL,
}


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
    # Per-modality models (only write if set)
    for key in ("QSENSE_IMAGE_MODEL", "QSENSE_AUDIO_MODEL", "QSENSE_VIDEO_MODEL"):
        if values.get(key):
            lines.append(f"{key}={_sanitize(values[key])}")
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
    result = {
        "api_key": _mask(stored.get("QSENSE_API_KEY", "")),
        "base_url": stored.get("QSENSE_BASE_URL", DEFAULT_BASE_URL),
        "model": stored.get("QSENSE_MODEL", DEFAULT_MODEL),
    }
    for modality, key in _MODALITY_KEYS.items():
        val = stored.get(key)
        if val:
            result[f"{modality}_model"] = val
    return result


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return value[:6] + "..." + value[-4:]


def update_config(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    image_model: str | None = None,
    audio_model: str | None = None,
    video_model: str | None = None,
) -> None:
    """Update specific fields in ``~/.qsense/.env``, keeping others intact."""
    stored = _load_config_file()

    if api_key is not None:
        stored["QSENSE_API_KEY"] = api_key
    if base_url is not None:
        stored["QSENSE_BASE_URL"] = base_url
    if model is not None:
        stored["QSENSE_MODEL"] = model
    if image_model is not None:
        stored["QSENSE_IMAGE_MODEL"] = image_model
    if audio_model is not None:
        stored["QSENSE_AUDIO_MODEL"] = audio_model
    if video_model is not None:
        stored["QSENSE_VIDEO_MODEL"] = video_model

    _write_config(stored)


def resolve_model(
    *,
    cli_model: str | None = None,
    has_image: bool = False,
    has_audio: bool = False,
    has_video: bool = False,
) -> str:
    """Pick the right model based on input modalities.

    Priority:
      1. --model CLI flag (explicit override)
      2. Single modality → per-modality default
      3. Mixed modalities → QSENSE_MODEL global default
    """
    if cli_model:
        return cli_model

    stored = _load_config_file()
    modality_count = sum([has_image, has_audio, has_video])

    # Single modality: use modality-specific model if configured
    if modality_count == 1:
        if has_image:
            m = os.environ.get("QSENSE_IMAGE_MODEL") or stored.get("QSENSE_IMAGE_MODEL")
            if m:
                return m
        elif has_audio:
            m = os.environ.get("QSENSE_AUDIO_MODEL") or stored.get("QSENSE_AUDIO_MODEL")
            if m:
                return m
        elif has_video:
            m = os.environ.get("QSENSE_VIDEO_MODEL") or stored.get("QSENSE_VIDEO_MODEL")
            if m:
                return m

    # Mixed modalities or no modality-specific config: global default
    return (
        os.environ.get("QSENSE_MODEL")
        or stored.get("QSENSE_MODEL")
        or DEFAULT_MODEL
    )


def load_config(
    *,
    model: str | None = None,
    timeout: int | None = None,
    has_image: bool = False,
    has_audio: bool = False,
    has_video: bool = False,
) -> Config:
    """Build a Config with priority: CLI flags > modality default > env > file."""
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
    resolved_model = resolve_model(
        cli_model=model,
        has_image=has_image,
        has_audio=has_audio,
        has_video=has_video,
    )
    resolved_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT

    return Config(
        api_key=api_key,
        base_url=resolved_base_url,
        model=resolved_model,
        timeout=resolved_timeout,
    )
