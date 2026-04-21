"""Optional JSON schema validation helpers."""

from __future__ import annotations

import json

try:
    from jsonschema import validate as _jsonschema_validate
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal local environments
    _jsonschema_validate = None


def _fallback_validate(instance: dict, schema: dict) -> None:
    if schema.get("type") == "object" and not isinstance(instance, dict):
        raise ValueError("JSON payload must be an object.")
    for key in schema.get("required", []):
        if key not in instance:
            raise ValueError(f"Missing required property: {key}")
    for key, rules in schema.get("properties", {}).items():
        if key not in instance:
            continue
        value = instance[key]
        expected_type = rules.get("type")
        if expected_type == "string" and not isinstance(value, str):
            raise ValueError(f"Property '{key}' must be a string.")
        if expected_type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"Property '{key}' must be a boolean.")
        if expected_type == "object" and not isinstance(value, dict):
            raise ValueError(f"Property '{key}' must be an object.")
        if expected_type == "array" and not isinstance(value, list):
            raise ValueError(f"Property '{key}' must be an array.")


def validate_json_text(text: str, schema: dict) -> dict:
    data = json.loads(text)
    if _jsonschema_validate is not None:
        _jsonschema_validate(instance=data, schema=schema)
    else:
        _fallback_validate(data, schema)
    return data
