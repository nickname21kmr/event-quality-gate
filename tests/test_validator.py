"""Validation engine regression tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from event_quality_gate.contract import ContractError, load_contract
from event_quality_gate.validator import matches_type, validate_file

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "examples" / "contracts" / "liveops-event-v1.json"


class ValidationTests(unittest.TestCase):
    def test_valid_fixture_passes(self) -> None:
        report = validate_file(
            load_contract(CONTRACT_PATH),
            ROOT / "examples" / "events" / "valid.jsonl",
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.total_records, 4)
        self.assertEqual(report.valid_records, 4)
        self.assertEqual(report.invalid_records, 0)
        self.assertEqual(report.issues, ())

    def test_invalid_fixture_covers_quality_rules(self) -> None:
        report = validate_file(
            load_contract(CONTRACT_PATH),
            ROOT / "examples" / "events" / "invalid.jsonl",
        )

        self.assertFalse(report.passed)
        self.assertEqual(report.total_records, 6)
        self.assertEqual(report.invalid_records, 6)
        self.assertEqual(
            {issue.code for issue in report.issues},
            {"minimum", "required", "unique", "allowed_values", "invalid_json", "record_type"},
        )

    def test_purchase_requires_nested_fields(self) -> None:
        report = self._validate_lines(
            [
                {
                    "event_id": "evt-purchase",
                    "event_type": "purchase",
                    "user_id": "player",
                    "occurred_at": "2026-09-01T00:00:00Z",
                    "properties": {},
                }
            ]
        )

        fields = {issue.field for issue in report.issues if issue.code == "conditional_required"}
        self.assertEqual(fields, {"properties.amount", "properties.currency"})

    def test_duplicate_reports_original_line(self) -> None:
        base = {
            "event_id": "same-id",
            "event_type": "login",
            "user_id": "player",
            "occurred_at": "2026-09-01T00:00:00Z",
        }
        report = self._validate_lines([base, dict(base)])

        duplicate = next(issue for issue in report.issues if issue.code == "unique")
        self.assertEqual(duplicate.line, 2)
        self.assertIn("line 1", duplicate.message)

    def test_boolean_is_not_a_number(self) -> None:
        self.assertFalse(matches_type(True, "integer"))
        self.assertFalse(matches_type(True, "number"))
        self.assertTrue(matches_type(True, "boolean"))

    def test_datetime_requires_date_time_separator(self) -> None:
        self.assertTrue(matches_type("2026-09-01T12:30:00Z", "datetime"))
        self.assertFalse(matches_type("2026-09-01", "datetime"))
        self.assertFalse(matches_type("yesterday", "datetime"))

    def test_contract_rejects_overlapping_fields(self) -> None:
        payload = {
            "name": "bad-contract",
            "required": {"event_id": "string"},
            "optional": {"event_id": "string"},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "both required and optional"):
                load_contract(path)

    def _validate_lines(self, records: list[dict[str, object]]):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text(
                "\n".join(json.dumps(record) for record in records) + "\n",
                encoding="utf-8",
            )
            return validate_file(load_contract(CONTRACT_PATH), path)


if __name__ == "__main__":
    unittest.main()
