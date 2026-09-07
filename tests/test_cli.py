"""CLI behavior and exit-code tests."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from event_quality_gate.cli import main

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "examples" / "contracts" / "liveops-event-v1.json"
VALID = ROOT / "examples" / "events" / "valid.jsonl"
INVALID = ROOT / "examples" / "events" / "invalid.jsonl"


class CliTests(unittest.TestCase):
    def test_valid_input_returns_zero_and_json(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = main(
                [
                    "validate",
                    "--contract",
                    str(CONTRACT),
                    "--input",
                    str(VALID),
                    "--format",
                    "json",
                ]
            )

        self.assertEqual(result, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["summary"]["total_records"], 4)

    def test_invalid_input_returns_one_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "reports" / "invalid.md"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(
                    [
                        "validate",
                        "--contract",
                        str(CONTRACT),
                        "--input",
                        str(INVALID),
                        "--format",
                        "markdown",
                        "--output",
                        str(output),
                        "--max-issues",
                        "2",
                    ]
                )

            self.assertEqual(result, 1)
            report = output.read_text(encoding="utf-8")
            self.assertIn("**Status:** FAIL", report)
            self.assertIn("Truncated:", report)

    def test_missing_file_returns_configuration_error(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main(
                [
                    "validate",
                    "--contract",
                    str(CONTRACT),
                    "--input",
                    "missing.jsonl",
                ]
            )

        self.assertEqual(result, 2)
        self.assertIn("missing.jsonl", stderr.getvalue())

    def test_junit_report_is_written_for_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "reports" / "invalid.xml"
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "validate",
                        "--contract",
                        str(CONTRACT),
                        "--input",
                        str(INVALID),
                        "--format",
                        "junit",
                        "--output",
                        str(output),
                    ]
                )

            suite = ElementTree.parse(output).getroot()
            self.assertEqual(result, 1)
            self.assertEqual(suite.attrib["tests"], "6")
            self.assertEqual(suite.attrib["failures"], "6")


if __name__ == "__main__":
    unittest.main()
