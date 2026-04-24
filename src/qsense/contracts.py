"""Request contracts for review-oriented qsense invocations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InputRole(str, Enum):
    TARGET = "target"
    REFERENCE = "reference"
    CONTEXT = "context"
    SPEC = "spec"


@dataclass(frozen=True)
class ObservationRequest:
    prompt: str
    inputs: list[dict]
    output_format: str
    vision_fidelity: str

    def __post_init__(self) -> None:
        targets = [item for item in self.inputs if item["role"] == InputRole.TARGET]
        if len(targets) > 1:
            raise ValueError("Only one target input is allowed per request.")

    def by_role(self, role: InputRole) -> list[dict]:
        return [item for item in self.inputs if item["role"] == role]

    def primary_target(self) -> dict | None:
        items = self.by_role(InputRole.TARGET)
        return items[0] if items else None

    def render_instruction_prefix(self) -> str:
        parts: list[str] = []
        if self.primary_target():
            parts.append("TARGET INPUT: evaluate this as the main artifact.")
        if self.by_role(InputRole.REFERENCE):
            parts.append("REFERENCE INPUTS: use these only for comparison and consistency checks.")
        if self.by_role(InputRole.SPEC):
            parts.append("SPEC INPUTS: treat these as review criteria, not as observed facts.")
        if self.by_role(InputRole.CONTEXT):
            parts.append("CONTEXT INPUTS: use these as supporting context only.")
        return "\n".join(parts)

    def render_text_payload(self) -> str:
        sections: list[str] = []
        for role in (InputRole.SPEC, InputRole.CONTEXT):
            items = [item for item in self.by_role(role) if item.get("kind") == "text"]
            if not items:
                continue
            header = f"{role.value.upper()} TEXT INPUTS:"
            body = "\n".join(
                f"- [{idx}] {item['value']}" for idx, item in enumerate(items, start=1)
            )
            sections.append(f"{header}\n{body}")
        return "\n\n".join(sections)
