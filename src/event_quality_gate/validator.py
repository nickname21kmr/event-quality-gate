"""Streaming JSONL validation engine."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from event_quality_gate.contract import Contract
from event_quality_gate.models import ValidationIssue, ValidationReport

_MISSING = object()


def validate_file(contract: Contract, input_path: str | Path) -> ValidationReport:
    """Validate a JSONL file without retaining its records in memory."""
    source_path = Path(input_path)
    issues: list[ValidationIssue] = []
    invalid_lines: set[int] = set()
    seen: dict[str, dict[str, int]] = {field: {} for field in contract.unique}
    total_records = 0

    with source_path.open("r", encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            if not raw_line.strip():
                continue
            total_records += 1
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                issues.append(
                    ValidationIssue(
                        line=line_number,
                        code="invalid_json",
                        message=f"Invalid JSON: {exc.msg}.",
                    )
                )
                invalid_lines.add(line_number)
                continue

            if not isinstance(record, dict):
                issues.append(
                    ValidationIssue(
                        line=line_number,
                        code="record_type",
                        message="Each JSONL record must be an object.",
                    )
                )
                invalid_lines.add(line_number)
                continue

            record_issues = validate_record(
                contract,
                record,
                line_number=line_number,
                seen=seen,
            )
            if record_issues:
                invalid_lines.add(line_number)
                issues.extend(record_issues)

    invalid_records = len(invalid_lines)
    return ValidationReport(
        contract_name=contract.name,
        source=str(source_path),
        total_records=total_records,
        valid_records=total_records - invalid_records,
        invalid_records=invalid_records,
        issues=tuple(issues),
    )


def validate_record(
    contract: Contract,
    record: dict[str, Any],
    *,
    line_number: int,
    seen: dict[str, dict[str, int]] | None = None,
) -> list[ValidationIssue]:
    """Validate one decoded event against a contract."""
    issues: list[ValidationIssue] = []
    uniqueness = seen if seen is not None else {field: {} for field in contract.unique}

    for field, type_name in contract.required.items():
        value = get_path(record, field)
        if value is _MISSING:
            issues.append(_issue(line_number, "required", field, "Required field is missing."))
        elif not matches_type(value, type_name):
            issues.append(_type_issue(line_number, field, type_name, value))

    for field, type_name in contract.optional.items():
        value = get_path(record, field)
        if value is not _MISSING and not matches_type(value, type_name):
            issues.append(_type_issue(line_number, field, type_name, value))

    for field, allowed in contract.allowed_values.items():
        value = get_path(record, field)
        if value is not _MISSING and value not in allowed:
            issues.append(
                _issue(
                    line_number,
                    "allowed_values",
                    field,
                    f"Value {value!r} is not one of {list(allowed)!r}.",
                )
            )

    for field in contract.unique:
        value = get_path(record, field)
        if value is _MISSING:
            continue
        marker = json.dumps(value, ensure_ascii=False, sort_keys=True)
        first_line = uniqueness.setdefault(field, {}).get(marker)
        if first_line is not None:
            issues.append(
                _issue(
                    line_number,
                    "unique",
                    field,
                    f"Duplicate value first seen on line {first_line}.",
                )
            )
        else:
            uniqueness[field][marker] = line_number

    for constraint in contract.constraints:
        when = constraint["when"]
        if get_path(record, when["field"]) != when["equals"]:
            continue
        issues.extend(_validate_constraint(record, constraint, line_number=line_number))

    return issues


def get_path(record: dict[str, Any], field_path: str) -> Any:
    """Resolve a dot-separated field path from nested dictionaries."""
    value: Any = record
    for part in field_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return _MISSING
        value = value[part]
    return value


def matches_type(value: Any, type_name: str) -> bool:
    """Apply JSON-oriented types while excluding bool from numeric types."""
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "datetime":
        return isinstance(value, str) and _is_iso_datetime(value)
    return False


def _is_iso_datetime(value: str) -> bool:
    try:
        parsed = value[:-1] + "+00:00" if value.endswith("Z") else value
        datetime.fromisoformat(parsed)
    except ValueError:
        return False
    return "T" in value


def _validate_constraint(
    record: dict[str, Any],
    constraint: dict[str, Any],
    *,
    line_number: int,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in constraint["require"]:
        if get_path(record, field) is _MISSING:
            issues.append(
                _issue(
                    line_number,
                    "conditional_required",
                    field,
                    "Field is required by condition.",
                )
            )

    for field, type_name in constraint["types"].items():
        value = get_path(record, field)
        if value is not _MISSING and not matches_type(value, type_name):
            issues.append(_type_issue(line_number, field, type_name, value))

    for field, minimum in constraint["minimum"].items():
        value = get_path(record, field)
        if _is_number(value) and value < minimum:
            issues.append(
                _issue(line_number, "minimum", field, f"Value {value!r} is below {minimum!r}.")
            )

    for field, maximum in constraint["maximum"].items():
        value = get_path(record, field)
        if _is_number(value) and value > maximum:
            issues.append(
                _issue(line_number, "maximum", field, f"Value {value!r} is above {maximum!r}.")
            )
    return issues


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _type_issue(line: int, field: str, expected: str, value: Any) -> ValidationIssue:
    return _issue(
        line,
        "type",
        field,
        f"Expected {expected}, received {type(value).__name__}.",
    )


def _issue(line: int, code: str, field: str, message: str) -> ValidationIssue:
    return ValidationIssue(line=line, code=code, field=field, message=message)
