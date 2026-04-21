"""Structured response envelope for qsense outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json


@dataclass
class ObservationResponse:
    model: str
    output_format: str
    text: str
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    data: dict | list | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)
