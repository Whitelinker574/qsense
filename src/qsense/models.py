"""Model registry — loads curated model list from registry.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
import sys
from pathlib import Path

import yaml

REGISTRY_FILE = Path(__file__).parent / "registry.yaml"


@dataclass(frozen=True)
class ModelInfo:
    id: str
    name: str
    vision: bool = False
    audio: bool = False
    video: bool = False
    native_video: bool = False
    stream_only: bool = False
    video_url_passthrough: bool = False
    context_tokens: int | None = None
    max_image_size_mb: int | None = None
    max_image_resolution: str | None = None
    max_images_per_request: int | None = None
    max_audio_duration_min: int | None = None
    max_video_duration_min: int | None = None
    image_formats: tuple[str, ...] = field(default_factory=tuple)
    audio_formats: tuple[str, ...] = field(default_factory=tuple)
    video_formats: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


def _load_registry() -> list[ModelInfo]:
    try:
        raw = yaml.safe_load(REGISTRY_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[qsense] Warning: failed to load model registry: {exc}", file=sys.stderr)
        return []
    if not isinstance(raw, list):
        print("[qsense] Warning: registry.yaml is malformed (expected a list)", file=sys.stderr)
        return []
    models = []
    for e in raw:
        models.append(ModelInfo(
            id=e["id"],
            name=e.get("name", e["id"]),
            vision=e.get("vision", False),
            audio=e.get("audio", False),
            video=e.get("video", False),
            native_video=e.get("native_video", False),
            stream_only=e.get("stream_only", False),
            video_url_passthrough=e.get("video_url_passthrough", False),
            context_tokens=e.get("context_tokens"),
            max_image_size_mb=e.get("max_image_size_mb"),
            max_image_resolution=str(e["max_image_resolution"]) if e.get("max_image_resolution") else None,
            max_images_per_request=e.get("max_images_per_request"),
            max_audio_duration_min=e.get("max_audio_duration_min"),
            max_video_duration_min=e.get("max_video_duration_min"),
            image_formats=tuple(e.get("image_formats") or []),
            audio_formats=tuple(e.get("audio_formats") or []),
            video_formats=tuple(e.get("video_formats") or []),
            description=e.get("description", ""),
        ))
    return models


REGISTRY: list[ModelInfo] = _load_registry()
_INDEX: dict[str, ModelInfo] = {m.id: m for m in REGISTRY}


def get_model(model_id: str) -> ModelInfo | None:
    return _INDEX.get(model_id)


def list_models() -> list[ModelInfo]:
    return list(REGISTRY)


def is_registered(model_id: str) -> bool:
    return model_id in _INDEX


def require_registered(model_id: str, *, source: str = "model") -> str:
    if not is_registered(model_id):
        raise ValueError(
            f"{source} '{model_id}' is not in the registry. "
            "Run 'qsense models' to see available models."
        )
    return model_id
