import unittest

from qsense.contracts import InputRole, ObservationRequest


class ObservationRequestTests(unittest.TestCase):
    def test_single_target_and_multiple_references(self):
        req = ObservationRequest(
            prompt="Review the target image against the references.",
            inputs=[
                {"role": InputRole.TARGET, "kind": "image", "value": "target.png"},
                {"role": InputRole.REFERENCE, "kind": "image", "value": "ref_a.png"},
                {"role": InputRole.REFERENCE, "kind": "image", "value": "ref_b.png"},
            ],
            output_format="text",
            vision_fidelity="standard",
        )
        self.assertEqual(req.primary_target()["value"], "target.png")
        self.assertEqual(len(req.by_role(InputRole.REFERENCE)), 2)

    def test_reject_multiple_targets(self):
        with self.assertRaises(ValueError):
            ObservationRequest(
                prompt="bad",
                inputs=[
                    {"role": InputRole.TARGET, "kind": "image", "value": "a.png"},
                    {"role": InputRole.TARGET, "kind": "image", "value": "b.png"},
                ],
                output_format="text",
                vision_fidelity="standard",
            )


class PromptAssemblyTests(unittest.TestCase):
    def test_role_headers_are_emitted_in_stable_order(self):
        req = ObservationRequest(
            prompt="Compare target with reference.",
            inputs=[
                {"role": InputRole.REFERENCE, "kind": "image", "value": "ref.png"},
                {"role": InputRole.TARGET, "kind": "image", "value": "target.png"},
                {"role": InputRole.SPEC, "kind": "text", "value": "The left icon must remain blue."},
            ],
            output_format="json",
            vision_fidelity="max",
        )
        rendered = req.render_instruction_prefix()
        self.assertIn("TARGET INPUT", rendered)
        self.assertIn("REFERENCE INPUTS", rendered)
        self.assertIn("SPEC INPUTS", rendered)
