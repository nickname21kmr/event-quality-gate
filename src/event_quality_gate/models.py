"""Immutable result models used by validation and reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One contract violation associated with a source line."""

    line: int
    code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "line": self.line,
            "code": self.code,
            "field": self.field,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Aggregate validation outcome for one JSONL source."""

    contract_name: str
    source: str
    total_records: int
    valid_records: int
    invalid_records: int
    issues: tuple[ValidationIssue, ...]

    @property
    def passed(self) -> bool:
        return self.invalid_records == 0

    def to_dict(self, *, max_issues: int | None = None) -> dict[str, Any]:
        visible = self.issues if max_issues is None else self.issues[:max_issues]
        return {
            "contract": self.contract_name,
            "source": self.source,
            "status": "passed" if self.passed else "failed",
            "summary": {
                "total_records": self.total_records,
                "valid_records": self.valid_records,
                "invalid_records": self.invalid_records,
                "total_issues": len(self.issues),
                "displayed_issues": len(visible),
            },
            "issues": [issue.to_dict() for issue in visible],
        }
