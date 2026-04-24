import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from click.testing import CliRunner

from qsense.cli import main
from qsense.config import load_config, update_config


class ConfigModelValidationTests(unittest.TestCase):
    def test_update_config_rejects_unregistered_model(self):
        with patch("qsense.config._load_config_file", return_value={}):
            with self.assertRaisesRegex(ValueError, "not in the registry"):
                update_config(model="google/gemini-2.5-flash")

    def test_load_config_rejects_unregistered_default_model(self):
        stderr = io.StringIO()
        with patch(
            "qsense.config._load_config_file",
            return_value={
                "QSENSE_API_KEY": "sk-test",
                "QSENSE_MODEL": "google/gemini-2.5-flash",
            },
        ):
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as ctx:
                    load_config(has_image=True)
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("not in the registry", stderr.getvalue())


class CliModelValidationTests(unittest.TestCase):
    def test_main_rejects_unregistered_cli_model(self):
        runner = CliRunner()
        with patch("qsense.cli.chat") as chat_mock:
            result = runner.invoke(
                main,
                [
                    "--prompt",
                    "describe this image",
                    "--image",
                    "https://example.com/test.png",
                    "--model",
                    "google/gemini-2.5-flash",
                ],
                env={"QSENSE_API_KEY": "sk-test"},
            )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("not in the registry", result.output)
        chat_mock.assert_not_called()
