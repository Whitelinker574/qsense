"""Video processing — direct passthrough and frame extraction modes.

Frame extraction has two backends:
  1. ffmpeg (preferred) — fast, extracts audio track too
  2. imageio (fallback) — pure Python, no audio, but always available
"""

from __future__ import annotations

import base64
import shutil
import subprocess
import sys
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

def _has_ffmpeg() -> str | None:
    """Return ffmpeg path if available, None otherwise."""
    return shutil.which("ffmpeg")


def _validate_video(path: Path) -> None:
    if not path.exists():
        _abort(f"Video file not found: {path}")
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        _abort(f"Unsupported video type: {path}")


def _run_ffmpeg(args: list[str]) -> None:
    try:
        subprocess.run(args, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace").strip()
        _abort(f"ffmpeg failed: {stderr[:300]}")


def _has_audio_stream(ffmpeg: str, video_path: Path) -> bool:
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

    mime = content_type if content_type in MIME_TO_EXT else None
    if not mime:
        ext = _infer_ext_from_url(url)
        mime = EXTENSION_TO_MIME.get(ext, "video/mp4") if ext else "video/mp4"

    return raw, mime


def _download_to_tempfile(url: str, tmpdir: Path, max_bytes: int) -> Path:
    """Download a remote video to a temp file."""
    raw, _ = _download_video(url, max_bytes)
    ext = _infer_ext_from_url(url) or ".mp4"
    tmp_path = tmpdir / f"remote_video{ext}"
    tmp_path.write_bytes(raw)
    return tmp_path


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
# Direct mode
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
# Extract mode — ffmpeg (preferred) or imageio fallback
# ---------------------------------------------------------------------------

def _extract_with_ffmpeg(
    ffmpeg: str,
    path: Path,
    tmp: Path,
    fps: float,
    max_frames: int,
    max_image_long_side: int | None,
) -> tuple[list[ImageContentPart], AudioContentPart | None]:
    """Extract frames + audio using ffmpeg."""
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
    images = prepare_images(frame_paths, max_long_side=max_image_long_side) if max_image_long_side else prepare_images(frame_paths)

    # Extract audio if present
    audio_part: AudioContentPart | None = None
    if _has_audio_stream(ffmpeg, path):
        audio_path = tmp / "audio.wav"
        _run_ffmpeg([
            ffmpeg, "-i", str(path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(audio_path),
        ])
        if audio_path.exists() and audio_path.stat().st_size > 0:
            audio_part = prepare_audio(str(audio_path))

    return images, audio_part


def _extract_with_imageio(
    path: Path,
    tmp: Path,
    fps: float,
    max_frames: int,
    max_image_long_side: int | None,
) -> tuple[list[ImageContentPart], None]:
    """Extract frames using imageio (pure Python fallback, no audio)."""
    try:
        import imageio.v3 as iio
    except ImportError:
        _abort(
            "Neither ffmpeg nor imageio is available for frame extraction.\n"
            "  Install ffmpeg: qsense init (will guide you)\n"
            "  Or install imageio: pip install imageio[ffmpeg]"
        )

    print("[qsense] ffmpeg not found, using imageio fallback (no audio extraction)", file=sys.stderr)

    try:
        frames_raw = iio.imread(str(path), plugin="pyav")
    except Exception:
        try:
            frames_raw = iio.imread(str(path))
        except Exception as exc:
            _abort(f"Cannot read video {path}: {exc}")

    total_frames = len(frames_raw)
    if total_frames == 0:
        _abort(f"No frames found in video: {path}")

    # Calculate which frames to sample based on fps
    # Assume ~30fps source if we can't determine
    try:
        meta = iio.immeta(str(path), plugin="pyav")
        source_fps = meta.get("fps", 30)
    except Exception:
        source_fps = 30

    frame_interval = max(1, int(source_fps / fps))
    sampled_indices = list(range(0, total_frames, frame_interval))

    if len(sampled_indices) > max_frames:
        step = len(sampled_indices) / max_frames
        sampled_indices = [sampled_indices[int(i * step)] for i in range(max_frames)]

    # Save sampled frames as JPEG
    from PIL import Image

    frame_paths: list[str] = []
    for i, idx in enumerate(sampled_indices):
        frame_path = tmp / f"frame_{i:04d}.jpg"
        img = Image.fromarray(frames_raw[idx])
        img.save(str(frame_path), format="JPEG", quality=85)
        frame_paths.append(str(frame_path))

    images = prepare_images(frame_paths, max_long_side=max_image_long_side) if max_image_long_side else prepare_images(frame_paths)
    return images, None


def extract_frames_and_audio(
    source: str,
    *,
    fps: float = 1.0,
    max_frames: int = 30,
    max_image_long_side: int | None = None,
) -> tuple[list[ImageContentPart], AudioContentPart | None]:
    """Extract video frames and optionally audio track.

    Uses ffmpeg if available (frames + audio). Falls back to imageio
    for pure Python frame extraction (no audio).

    Supports both local files and remote URLs.
    """
    with tempfile.TemporaryDirectory(prefix="qsense_") as tmpdir:
        tmp = Path(tmpdir)

        # Resolve source to local path
        if source.startswith(("http://", "https://")):
            path = _download_to_tempfile(source, tmp, DIRECT_MAX_BYTES * 5)
        else:
            path = Path(source).resolve()
            _validate_video(path)

        # Try ffmpeg first, fall back to imageio
        ffmpeg = _has_ffmpeg()
        if ffmpeg:
            return _extract_with_ffmpeg(ffmpeg, path, tmp, fps, max_frames, max_image_long_side)
        else:
            return _extract_with_imageio(path, tmp, fps, max_frames, max_image_long_side)
