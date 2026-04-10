"""Audio normalization — validate, download if remote, encode for API.

Two encoding formats are supported:
  1. data URL via image_url field (default) — ``data:audio/wav;base64,...``
     Broader compatibility: works with proxies that don't handle input_audio.
  2. input_audio (OpenAI standard) — ``{"type":"input_audio","input_audio":{...}}``
     Stricter but official format. Some proxies fail to forward this.

Default is data URL because it works with more proxies and models.
"""

from __future__ import annotations

import base64
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import httpx

from ._util import abort as _abort

# ---------------------------------------------------------------------------
# Supported formats
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".webm"}

EXTENSION_TO_FORMAT: dict[str, str] = {
    ".mp3": "mp3",
    ".wav": "wav",
    ".flac": "flac",
    ".ogg": "ogg",
    ".m4a": "m4a",
    ".aac": "aac",
    ".webm": "webm",
}

EXTENSION_TO_MIME: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".webm": "audio/webm",
}

MIME_TO_FORMAT: dict[str, str] = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/aac": "aac",
    "audio/webm": "webm",
}

MIME_TO_EXT: dict[str, str] = {v: k for k, v in EXTENSION_TO_MIME.items()}

DOWNLOAD_TIMEOUT = 60
DOWNLOAD_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------------------
# Types (kept for compatibility, actual return is dict)
# ---------------------------------------------------------------------------

# AudioContentPart can be either:
#   {"type": "image_url", "image_url": {"url": "data:audio/wav;base64,..."}}
#   {"type": "input_audio", "input_audio": {"data": "...", "format": "wav"}}
AudioContentPart = dict


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _to_data_url_part(raw: bytes, mime: str) -> dict:
    """Encode as data URL in image_url field (default, best compatibility)."""
    encoded = base64.b64encode(raw).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}


def _to_input_audio_part(raw: bytes, fmt: str) -> dict:
    """Encode as OpenAI input_audio format."""
    encoded = base64.b64encode(raw).decode()
    return {"type": "input_audio", "input_audio": {"data": encoded, "format": fmt}}


def _infer_format_from_url(url: str) -> str | None:
    ext = PurePosixPath(urlparse(url).path).suffix.lower()
    return EXTENSION_TO_FORMAT.get(ext)


def _infer_mime_from_url(url: str) -> str | None:
    ext = PurePosixPath(urlparse(url).path).suffix.lower()
    return EXTENSION_TO_MIME.get(ext)


def _download_and_encode(url: str) -> dict:
    """Download a remote audio file with size limit, detect format, encode."""
    max_mb = DOWNLOAD_MAX_BYTES // 1024 // 1024
    try:
        with httpx.Client(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()

                chunks: list[bytes] = []
                downloaded = 0
                for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                    downloaded += len(chunk)
                    if downloaded > DOWNLOAD_MAX_BYTES:
                        _abort(f"Audio too large (>{max_mb} MB): {url}")
                    chunks.append(chunk)
    except SystemExit:
        raise
    except Exception as exc:
        _abort(f"Failed to download audio: {url} ({exc})")

    raw = b"".join(chunks)
    if len(raw) == 0:
        _abort(f"Downloaded audio is empty: {url}")

    # Determine MIME for data URL
    mime = content_type if content_type in MIME_TO_FORMAT else None
    if not mime:
        mime = _infer_mime_from_url(url)
    if not mime:
        _abort(f"Cannot determine audio format for {url} (Content-Type: {content_type})")

    return _to_data_url_part(raw, mime)


def _load_and_encode(path: Path) -> dict:
    """Read a local audio file, validate, encode."""
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        _abort(f"Unsupported audio type: {path}")

    try:
        raw = path.read_bytes()
    except Exception as exc:
        _abort(f"Cannot read audio {path}: {exc}")

    if len(raw) == 0:
        _abort(f"Audio file is empty: {path}")

    mime = EXTENSION_TO_MIME[ext]
    return _to_data_url_part(raw, mime)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prepare_audio(source: str) -> dict:
    """Turn one ``--audio`` argument into an API content part.

    Uses data URL via image_url field (``data:audio/wav;base64,...``) for
    best proxy compatibility. Remote URLs are downloaded first.
    """
    if source.startswith(("http://", "https://")):
        return _download_and_encode(source)

    path = Path(source).resolve()
    if not path.exists():
        _abort(f"Audio file not found: {path}")

    return _load_and_encode(path)


def prepare_audios(sources: tuple[str, ...] | list[str]) -> list[dict]:
    """Prepare multiple audio sources, preserving order."""
    return [prepare_audio(s) for s in sources]
