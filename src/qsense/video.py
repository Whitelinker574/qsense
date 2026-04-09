"""Video processing — direct passthrough and frame extraction modes."""

from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import httpx

from ._util import abort as _abort
from .audio import AudioContentPart, prepare_audio
from .image import ImageContentPart, prepare_images

SUPPORTED_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}

EXTENSION_TO_MIME: dict[str, str] = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
}

MIME_TO_EXT: dict[str, str] = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/x-matroska": ".mkv",
}

DIRECT_MAX_BYTES = 20 * 1024 * 1024  # 20 MB
DOWNLOAD_TIMEOUT = 120


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        _abort("ffmpeg is required for video processing. See https://ffmpeg.org/download.html")
    return path


def _validate_video(path: Path) -> None:
    if not path.exists():
        _abort(f"Video file not found: {path}")
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        _abort(f"Unsupported video type: {path}")


def _run_ffmpeg(args: list[str]) -> None:
    """Run ffmpeg, abort on failure."""
    try:
        subprocess.run(args, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace").strip()
        _abort(f"ffmpeg failed: {stderr[:300]}")


def _has_audio_stream(ffmpeg: str, video_path: Path) -> bool:
    """Check if video file contains an audio stream."""
    try:
        result = subprocess.run(
            [ffmpeg, "-i", str(video_path), "-hide_banner"],
            capture_output=True, text=True,
        )
        return "Audio:" in result.stderr
    except Exception:
        return False


def _infer_ext_from_url(url: str) -> str | None:
    ext = PurePosixPath(urlparse(url).path).suffix.lower()
    return ext if ext in SUPPORTED_EXTENSIONS else None


def _download_video(url: str, max_bytes: int) -> tuple[bytes, str]:
    """Stream-download a remote video. Returns (data, mime)."""
    max_mb = max_bytes // 1024 // 1024
    try:
        with httpx.Client(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()

                chunks: list[bytes] = []
                downloaded = 0
                for chunk in resp.iter_bytes(chunk_size=256 * 1024):
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        _abort(f"Video too large (>{max_mb} MB): {url}")
                    chunks.append(chunk)
    except SystemExit:
        raise
    except Exception as exc:
        _abort(f"Failed to download video: {url} ({exc})")

    raw = b"".join(chunks)
    if len(raw) == 0:
        _abort(f"Downloaded video is empty: {url}")

    # Determine MIME
    mime = content_type if content_type in MIME_TO_EXT else None
    if not mime:
        ext = _infer_ext_from_url(url)
        mime = EXTENSION_TO_MIME.get(ext, "video/mp4") if ext else "video/mp4"

    return raw, mime


def _encode_local(path: Path) -> dict:
    """Read a local video file and encode as data URL."""
    _validate_video(path)
    size = path.stat().st_size
    if size > DIRECT_MAX_BYTES:
        mb = size / 1024 / 1024
        _abort(f"Video too large for direct mode ({mb:.1f} MB, max {DIRECT_MAX_BYTES // 1024 // 1024} MB). "
               f"Use --video-extract for frame extraction.")
    mime = EXTENSION_TO_MIME[path.suffix.lower()]
    encoded = base64.b64encode(path.read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}


# ---------------------------------------------------------------------------
# Direct mode — encode whole video as data URL
# ---------------------------------------------------------------------------

def encode_video_direct(source: str, *, url_passthrough: bool = False) -> dict:
    """Encode a video as a content part.

    * Remote URL + passthrough → pass URL directly (saves bandwidth).
    * Remote URL (default) → download, encode as base64 data URL.
    * Local path → read, encode as base64 data URL.
    """
    if source.startswith(("http://", "https://")):
        if url_passthrough:
            return {"type": "image_url", "image_url": {"url": source}}
        raw, mime = _download_video(source, DIRECT_MAX_BYTES)
        encoded = base64.b64encode(raw).decode()
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}

    return _encode_local(Path(source).resolve())


# ---------------------------------------------------------------------------
# Extract mode — ffmpeg frames + audio
# ---------------------------------------------------------------------------

def _download_to_tempfile(url: str, tmpdir: Path) -> Path:
    """Download a remote video to a temp file for ffmpeg processing."""
    raw, _ = _download_video(url, DIRECT_MAX_BYTES * 5)  # 抽帧模式允许更大文件 (100MB)
    ext = _infer_ext_from_url(url) or ".mp4"
    tmp_path = tmpdir / f"remote_video{ext}"
    tmp_path.write_bytes(raw)
    return tmp_path


def extract_frames_and_audio(
    source: str,
    *,
    fps: float = 1.0,
    max_frames: int = 30,
    max_image_long_side: int | None = None,
) -> tuple[list[ImageContentPart], AudioContentPart | None]:
    """Extract video frames and audio track using ffmpeg.

    Supports both local files and remote URLs (downloaded first).
    Returns (image_content_parts, audio_content_part_or_None).
    """
    ffmpeg = _require_ffmpeg()

    with tempfile.TemporaryDirectory(prefix="qsense_") as tmpdir:
        tmp = Path(tmpdir)

        if source.startswith(("http://", "https://")):
            path = _download_to_tempfile(source, tmp)
        else:
            path = Path(source).resolve()
            _validate_video(path)

        # --- Extract frames ---
        frames_pattern = str(tmp / "frame_%04d.jpg")
        _run_ffmpeg([
            ffmpeg, "-i", str(path),
            "-vf", f"fps={fps}",
            "-q:v", "2",
            frames_pattern,
        ])

        frame_files = sorted(tmp.glob("frame_*.jpg"))
        if not frame_files:
            _abort(f"No frames extracted from video: {path}")

        if len(frame_files) > max_frames:
            step = len(frame_files) / max_frames
            frame_files = [frame_files[int(i * step)] for i in range(max_frames)]

        frame_paths = [str(f) for f in frame_files]
        if max_image_long_side:
            images = prepare_images(frame_paths, max_long_side=max_image_long_side)
        else:
            images = prepare_images(frame_paths)

        # --- Extract audio (if present) ---
        audio_part: AudioContentPart | None = None
        if _has_audio_stream(ffmpeg, path):
            audio_path = tmp / "audio.wav"
            _run_ffmpeg([
                ffmpeg, "-i", str(path),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                str(audio_path),
            ])
            if audio_path.exists() and audio_path.stat().st_size > 0:
                audio_part = prepare_audio(str(audio_path))

        return images, audio_part
