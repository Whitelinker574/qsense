"""Audio normalization — validate, download if remote, encode to input_audio.

OpenAI's chat completions API has no ``audio_url`` type (unlike ``image_url``).
All audio must be base64-encoded inline via the ``input_audio`` content part.
Remote URLs are downloaded client-side before encoding.

Standard ``input_audio`` format supports wav and mp3.  Gemini's OpenAI-compatible
endpoint additionally accepts flac, ogg, aac — we allow the broader set here.
"""

from __future__ import annotations

import base64
from pathlib import Path, PurePosixPath
from typing import TypedDict
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

DOWNLOAD_TIMEOUT = 60
DOWNLOAD_MAX_BYTES = 20 * 1024 * 1024  # 20 MB (Gemini inline limit)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class InputAudio(TypedDict):
    data: str
    format: str


class AudioContentPart(TypedDict):
    type: str
    input_audio: InputAudio


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _to_content_part(raw: bytes, fmt: str) -> AudioContentPart:
    encoded = base64.b64encode(raw).decode()
    return {"type": "input_audio", "input_audio": {"data": encoded, "format": fmt}}


def _infer_format_from_url(url: str) -> str | None:
    ext = PurePosixPath(urlparse(url).path).suffix.lower()
    return EXTENSION_TO_FORMAT.get(ext)


def _download_and_encode(url: str) -> AudioContentPart:
    """Download a remote audio file with size limit, detect format, base64-encode."""
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

    fmt = MIME_TO_FORMAT.get(content_type) or _infer_format_from_url(url)
    if not fmt:
        _abort(f"Cannot determine audio format for {url} (Content-Type: {content_type})")

    return _to_content_part(raw, fmt)


def _load_and_encode(path: Path) -> AudioContentPart:
    """Read a local audio file, validate, base64-encode."""
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        _abort(f"Unsupported audio type: {path}")

    fmt = EXTENSION_TO_FORMAT[ext]

    try:
        raw = path.read_bytes()
    except Exception as exc:
        _abort(f"Cannot read audio {path}: {exc}")

    if len(raw) == 0:
        _abort(f"Audio file is empty: {path}")

    return _to_content_part(raw, fmt)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prepare_audio(source: str) -> AudioContentPart:
    """Turn one ``--audio`` argument into an ``input_audio`` content part.

    * Remote URL → download → detect format → base64-encode.
    * Local path → validate extension → base64-encode.

    There is no ``audio_url`` type in the OpenAI API, so all audio must be
    inlined as base64 regardless of source.
    """
    if source.startswith(("http://", "https://")):
        return _download_and_encode(source)

    path = Path(source).resolve()
    if not path.exists():
        _abort(f"Audio file not found: {path}")

    return _load_and_encode(path)


def prepare_audios(sources: tuple[str, ...] | list[str]) -> list[AudioContentPart]:
    """Prepare multiple audio sources, preserving order."""
    return [prepare_audio(s) for s in sources]
