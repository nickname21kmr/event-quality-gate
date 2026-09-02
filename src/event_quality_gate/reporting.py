"""Deterministic report renderers."""

from __future__ import annotations

import json

from event_quality_gate.models import ValidationReport


def render_report(
    report: ValidationReport,
    *,
    output_format: str,
    max_issues: int = 100,
) -> str:
    """Render a report in a supported human- or machine-readable format."""
    if output_format == "json":
        return json.dumps(
            report.to_dict(max_issues=max_issues),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    if output_format == "markdown":
        return _render_markdown(report, max_issues=max_issues)
    if output_format == "text":
        return _render_text(report, max_issues=max_issues)
    raise ValueError(f"Unsupported report format: {output_format}")


def _render_text(report: ValidationReport, *, max_issues: int) -> str:
    lines = [
        f"Event Quality Gate: {'PASS' if report.passed else 'FAIL'}",
        f"Contract: {report.contract_name}",
        f"Source: {report.source}",
        (
            "Records: "
            f"{report.total_records} total, {report.valid_records} valid, "
            f"{report.invalid_records} invalid"
        ),
        f"Issues: {len(report.issues)}",
    ]
    for issue in report.issues[:max_issues]:
        field = f" [{issue.field}]" if issue.field else ""
        lines.append(f"- line {issue.line} {issue.code}{field}: {issue.message}")
    if len(report.issues) > max_issues:
        lines.append(f"- ... {len(report.issues) - max_issues} more issue(s) not displayed")
    return "\n".join(lines) + "\n"


def _render_markdown(report: ValidationReport, *, max_issues: int) -> str:
    lines = [
        "# Event Quality Report",
        "",
        f"- **Status:** {'PASS' if report.passed else 'FAIL'}",
        f"- **Contract:** `{_escape(report.contract_name)}`",
        f"- **Source:** `{_escape(report.source)}`",
        (
            f"- **Records:** {report.total_records} total / {report.valid_records} valid / "
            f"{report.invalid_records} invalid"
        ),
        f"- **Issues:** {len(report.issues)}",
        "",
    ]
    if report.issues:
        lines.extend(
            [
                "| Line | Code | Field | Message |",
                "| ---: | --- | --- | --- |",
            ]
        )
        for issue in report.issues[:max_issues]:
            lines.append(
                f"| {issue.line} | `{_escape(issue.code)}` | "
                f"`{_escape(issue.field or '-')}` | {_escape(issue.message)} |"
            )
        if len(report.issues) > max_issues:
            lines.extend(
                [
                    "",
                    (
                        f"_Truncated: {len(report.issues) - max_issues} additional issue(s) "
                        "not displayed._"
                    ),
                ]
            )
    else:
        lines.append("No contract violations found.")
    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
