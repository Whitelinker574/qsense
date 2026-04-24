import json
import unittest

from qsense.response import ObservationResponse
from qsense.schema import validate_json_text


class StructuredOutputTests(unittest.TestCase):
    def test_response_serializes_to_json(self):
        payload = ObservationResponse(
            model="google/gemini-3-flash-preview",
            output_format="json",
            text="ok",
            warnings=["resized target image"],
            meta={"vision_fidelity": "standard"},
        )
        data = json.loads(payload.to_json())
        self.assertEqual(data["text"], "ok")
        self.assertEqual(data["warnings"], ["resized target image"])


class SchemaValidationTests(unittest.TestCase):
    def test_valid_payload_matches_schema(self):
        schema = {
            "type": "object",
            "required": ["decision"],
            "properties": {"decision": {"type": "string"}},
        }
        data = validate_json_text('{"decision":"pass"}', schema)
        self.assertEqual(data["decision"], "pass")
