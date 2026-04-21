import unittest

from qsense.image import resolve_detail_hint, resolve_max_long_side


class ImageFidelityTests(unittest.TestCase):
    def test_low_fidelity_uses_smaller_resize(self):
        self.assertEqual(resolve_max_long_side("low"), 1024)

    def test_standard_fidelity_matches_current_default(self):
        self.assertEqual(resolve_max_long_side("standard"), 2048)

    def test_max_fidelity_preserves_large_inputs(self):
        self.assertEqual(resolve_max_long_side("max"), 4096)

    def test_openai_detail_mapping(self):
        self.assertEqual(resolve_detail_hint("gpt-5.4", "max"), "original")
