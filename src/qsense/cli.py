"""CLI entry point for qsense."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys

import click

from . import __version__
from .audio import prepare_audios
from .client import chat
from .config import (
    CONFIG_FILE,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    load_config,
    run_first_time_setup,
    show_config,
    update_config,
)
from .image import prepare_images
from .models import get_model, is_registered, list_models
from .video import encode_video_direct, extract_frames_and_audio


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="qsense")
@click.option("--prompt", default=None, help="Text prompt for the model.")
@click.option("--image", "images", multiple=True, help="Image path or URL (repeatable).")
@click.option("--audio", "audios", multiple=True, help="Audio file path or URL (repeatable).")
@click.option("--video", "videos", multiple=True, help="Video file path or URL (repeatable).")
@click.option("--video-extract", is_flag=True, default=False,
              help="Use frame extraction mode instead of direct passthrough (requires ffmpeg).")
@click.option("--video-passthrough", is_flag=True, default=False,
              help="Force URL passthrough for remote videos (skip download, save bandwidth).")
@click.option("--fps", default=1.0, type=click.FloatRange(min=0.1), help="Frame extraction rate (default: 1). Only with --video-extract.")
@click.option("--max-frames", default=30, type=click.IntRange(min=1), help="Max frames to extract (default: 30). Only with --video-extract.")
@click.option("--model", default=None, help="Override the default model.")
@click.option("--timeout", default=None, type=int, help="Request timeout in seconds.")
@click.option("--max-size", default=None, type=int, help="Max image longest side in pixels (default: 2048).")
@click.pass_context
def main(
    ctx: click.Context,
    prompt: str | None,
    images: tuple[str, ...],
    audios: tuple[str, ...],
    videos: tuple[str, ...],
    video_extract: bool,
    video_passthrough: bool,
    fps: float,
    max_frames: int,
    model: str | None,
    timeout: int | None,
    max_size: int | None,
) -> None:
    """Minimal CLI multimodal understanding tool."""
    if ctx.invoked_subcommand is not None:
        return

    if not prompt or not prompt.strip():
        print("[qsense] --prompt is required.", file=sys.stderr)
        sys.exit(1)

    if not images and not audios and not videos:
        print("[qsense] At least one --image, --audio, or --video is required.", file=sys.stderr)
        sys.exit(1)

    cfg = load_config(model=model, timeout=timeout)

    # --- Validate model ---
    if not is_registered(cfg.model):
        click.echo(
            f"[qsense] Warning: model '{cfg.model}' is not in the registry. "
            f"Run 'qsense models' to see available models.",
            err=True,
        )

    # --- Prepare images ---
    image_kwargs = {"max_long_side": max_size} if max_size else {}
    image_content = prepare_images(images, **image_kwargs) if images else []

    # --- Prepare audio ---
    audio_content = prepare_audios(audios) if audios else []

    # --- Prepare video ---
    extras: list[dict] = []

    # Determine URL passthrough: CLI flag > registry > default (download)
    model_info = get_model(cfg.model)
    use_passthrough = video_passthrough or (model_info.video_url_passthrough if model_info else False)

    for video_src in videos:
        if video_extract:
            frames, audio_part = extract_frames_and_audio(
                video_src,
                fps=fps,
                max_frames=max_frames,
                max_image_long_side=max_size,
            )
            image_content.extend(frames)
            if audio_part:
                audio_content.append(audio_part)
        else:
            extras.append(encode_video_direct(video_src, url_passthrough=use_passthrough))

    answer = chat(
        cfg,
        prompt,
        images=image_content or None,
        audios=audio_content or None,
        extras=extras or None,
    )
    print(answer)


@main.command()
@click.option("--model", default=None, help="Set default model.")
@click.option("--base-url", default=None, help="Set API base URL.")
@click.option("--api-key", default=None, help="Set API key.")
def config(model: str | None, base_url: str | None, api_key: str | None) -> None:
    """Show or update persistent configuration (~/.qsense/.env)."""
    if model is None and base_url is None and api_key is None:
        # No flags → show current config
        current = show_config()
        click.echo(f"  api_key:  {current['api_key']}")
        click.echo(f"  base_url: {current['base_url']}")
        click.echo(f"  model:    {current['model']}")
        return

    update_config(api_key=api_key, base_url=base_url, model=model)

    updated = []
    if api_key is not None:
        updated.append("api_key")
    if base_url is not None:
        updated.append(f"base_url={base_url}")
    if model is not None:
        updated.append(f"model={model}")
    click.echo(f"[qsense] Updated: {', '.join(updated)}")


@main.command()
@click.option("--api-key", default=None, help="API key (skip interactive prompt).")
@click.option("--base-url", default=None, help=f"API base URL (default: {DEFAULT_BASE_URL}).")
@click.option("--model", default=None, help=f"Default model (default: {DEFAULT_MODEL}).")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing config.")
def init(api_key: str | None, base_url: str | None, model: str | None, force: bool) -> None:
    """Initialize configuration (interactive or via flags).

    \b
    Examples:
      qsense init                                    # interactive
      qsense init --api-key sk-xxx                   # non-interactive, defaults for rest
      qsense init --api-key sk-xxx --model gpt-5.4   # full non-interactive
    """
    if CONFIG_FILE.exists() and not force:
        current = show_config()
        click.echo(f"[qsense] Config already exists ({CONFIG_FILE}):")
        click.echo(f"  api_key:  {current['api_key']}")
        click.echo(f"  base_url: {current['base_url']}")
        click.echo(f"  model:    {current['model']}")
        click.echo()
        click.echo("Run with --force to overwrite, or use 'qsense config' to update individual fields.")
        _check_ffmpeg()
        return

    if api_key:
        # Non-interactive: use flags + defaults
        update_config(
            api_key=api_key,
            base_url=base_url or DEFAULT_BASE_URL,
            model=model or DEFAULT_MODEL,
        )
        click.echo(f"[qsense] Config saved to {CONFIG_FILE}")
        final = show_config()
        click.echo(f"  api_key:  {final['api_key']}")
        click.echo(f"  base_url: {final['base_url']}")
        click.echo(f"  model:    {final['model']}")
    else:
        # Interactive
        run_first_time_setup()

    # ffmpeg check
    _check_ffmpeg()


def _check_ffmpeg() -> None:
    """Check ffmpeg availability and offer to install."""
    if shutil.which("ffmpeg"):
        click.echo(f"[qsense] ffmpeg: found ({shutil.which('ffmpeg')})")
        return

    click.echo("[qsense] ffmpeg: not found (needed for --video-extract)")

    os_name = platform.system()

    # macOS + Homebrew
    if os_name == "Darwin" and shutil.which("brew"):
        if click.confirm("  Install ffmpeg via Homebrew?", default=True):
            _run_install(["brew", "install", "ffmpeg"], "brew install ffmpeg")
            return

    # Linux + apt
    if os_name == "Linux" and shutil.which("apt"):
        if click.confirm("  Install ffmpeg via apt?", default=True):
            _run_install(["sudo", "apt", "install", "-y", "ffmpeg"], "sudo apt install ffmpeg")
            return

    # Windows + winget
    if os_name == "Windows" and shutil.which("winget"):
        if click.confirm("  Install ffmpeg via winget?", default=True):
            _run_install(["winget", "install", "Gyan.FFmpeg"], "winget install Gyan.FFmpeg")
            return

    # Windows + choco
    if os_name == "Windows" and shutil.which("choco"):
        if click.confirm("  Install ffmpeg via Chocolatey?", default=True):
            _run_install(["choco", "install", "ffmpeg", "-y"], "choco install ffmpeg -y")
            return

    # Windows + scoop
    if os_name == "Windows" and shutil.which("scoop"):
        if click.confirm("  Install ffmpeg via Scoop?", default=True):
            _run_install(["scoop", "install", "ffmpeg"], "scoop install ffmpeg")
            return

    # Fallback: manual instructions
    click.echo("  Install manually:")
    if os_name == "Darwin":
        click.echo("    brew install ffmpeg")
    elif os_name == "Linux":
        click.echo("    sudo apt install ffmpeg  # Debian/Ubuntu")
        click.echo("    sudo dnf install ffmpeg  # Fedora")
    elif os_name == "Windows":
        click.echo("    winget install Gyan.FFmpeg")
        click.echo("    # or: choco install ffmpeg")
        click.echo("    # or: scoop install ffmpeg")
    else:
        click.echo("    https://ffmpeg.org/download.html")


def _run_install(cmd: list[str], fallback_hint: str) -> None:
    """Run an install command, show fallback on failure."""
    click.echo(f"  Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        click.echo("[qsense] ffmpeg installed.")
    except subprocess.CalledProcessError:
        click.echo(f"[qsense] Installation failed. Try manually: {fallback_hint}", err=True)


def _format_tokens(n: int | None) -> str:
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    if n >= 1000:
        return f"{n // 1000}K"
    return str(n)


@main.command()
@click.option("--detail", is_flag=True, default=False, help="Show detailed limits for each model.")
def models(detail: bool) -> None:
    """List available multimodal models."""
    current = show_config()
    default_model = current["model"]

    for m in list_models():
        caps = []
        if m.vision:
            caps.append("vision")
        if m.audio:
            caps.append("audio")
        if m.video:
            tag = "video(native)" if m.native_video else "video(extract)"
            caps.append(tag)

        marker = " *" if m.id == default_model else ""
        click.echo(f"  {m.id}{marker}")
        click.echo(f"    {m.name} | {', '.join(caps)} | ctx {_format_tokens(m.context_tokens)}")
        if m.description:
            click.echo(f"    {m.description}")

        if detail:
            if m.vision:
                parts = []
                if m.max_image_size_mb:
                    parts.append(f"max {m.max_image_size_mb}MB")
                if m.max_image_resolution:
                    parts.append(f"max {m.max_image_resolution}")
                if m.max_images_per_request:
                    parts.append(f"max {m.max_images_per_request}/req")
                if m.image_formats:
                    parts.append(", ".join(m.image_formats))
                click.echo(f"    image: {' | '.join(parts)}")
            if m.audio:
                parts = []
                if m.max_audio_duration_min:
                    parts.append(f"max {m.max_audio_duration_min}min")
                if m.audio_formats:
                    parts.append(", ".join(m.audio_formats))
                click.echo(f"    audio: {' | '.join(parts)}")
            if m.video:
                parts = []
                if m.native_video:
                    parts.append("native")
                else:
                    parts.append("extract only")
                if m.max_video_duration_min:
                    parts.append(f"max {m.max_video_duration_min}min")
                if m.video_formats:
                    parts.append(", ".join(m.video_formats))
                click.echo(f"    video: {' | '.join(parts)}")

        click.echo()
