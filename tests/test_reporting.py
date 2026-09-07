"""Report renderer regression tests."""

from __future__ import annotations

import unittest
from pathlib import Path
from xml.etree import ElementTree

from event_quality_gate.contract import load_contract
from event_quality_gate.models import ValidationIssue, ValidationReport
from event_quality_gate.reporting import render_report
from event_quality_gate.validator import validate_file

ROOT = Path(__file__).resolve().parents[1]
ROOT_CONTRACT = ROOT / "examples" / "contracts" / "liveops-event-v1.json"
VALID_INPUT = ROOT / "examples" / "events" / "valid.jsonl"
INVALID_INPUT = ROOT / "examples" / "events" / "invalid.jsonl"


class JunitReportTests(unittest.TestCase):
    def test_passing_input_produces_valid_zero_failure_suite(self) -> None:
        report = validate_file(load_contract(ROOT_CONTRACT), VALID_INPUT)

        suite = ElementTree.fromstring(render_report(report, output_format="junit"))

        self.assertEqual(suite.tag, "testsuite")
        self.assertEqual(suite.attrib["tests"], "1")
        self.assertEqual(suite.attrib["failures"], "0")
        self.assertEqual(len(suite.findall("testcase")), 1)
        self.assertEqual(suite.findall(".//failure"), [])

    def test_invalid_records_become_failed_testcases(self) -> None:
        report = validate_file(load_contract(ROOT_CONTRACT), INVALID_INPUT)

        suite = ElementTree.fromstring(render_report(report, output_format="junit"))

        failures = suite.findall("testcase/failure")
        self.assertEqual(suite.attrib["tests"], "6")
        self.assertEqual(suite.attrib["failures"], "6")
        self.assertEqual(len(failures), 6)
        self.assertTrue(
            all(failure.attrib["type"] == "data_contract_violation" for failure in failures)
        )

    def test_xml_characters_are_escaped_and_round_trip(self) -> None:
        issue = ValidationIssue(
            line=1,
            code="invalid<&code",
            field='properties.<amount>&"',
            message='Expected <number> & received "text".',
        )
        report = ValidationReport(
            contract_name='contract<&"',
            source='events<&".jsonl',
            total_records=1,
            valid_records=0,
            invalid_records=1,
            issues=(issue,),
        )

        suite = ElementTree.fromstring(render_report(report, output_format="junit"))
        failure = suite.find("testcase/failure")

        self.assertEqual(suite.attrib["name"], 'contract<&"')
        self.assertIsNotNone(failure)
        self.assertIn(issue.code, failure.text or "")
        self.assertIn(issue.field or "", failure.text or "")
        self.assertIn(issue.message, failure.text or "")

    def test_issue_truncation_preserves_failed_record_count(self) -> None:
        issues = (
            ValidationIssue(line=1, code="required", field="a", message="Missing a."),
            ValidationIssue(line=1, code="required", field="b", message="Missing b."),
            ValidationIssue(line=2, code="required", field="c", message="Missing c."),
        )
        report = ValidationReport(
            contract_name="truncation",
            source="events.jsonl",
            total_records=2,
            valid_records=0,
            invalid_records=2,
            issues=issues,
        )

        suite = ElementTree.fromstring(render_report(report, output_format="junit", max_issues=1))
        failures = suite.findall("testcase/failure")
        properties = {
            item.attrib["name"]: item.attrib["value"]
            for item in suite.findall("properties/property")
        }

        self.assertEqual(len(failures), 2)
        self.assertEqual(properties["total_issues"], "3")
        self.assertEqual(properties["displayed_issues"], "1")
        self.assertIn("omitted", failures[1].text or "")


if __name__ == "__main__":
    unittest.main()
