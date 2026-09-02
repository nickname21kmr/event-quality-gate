"""Load and validate versioned JSON data contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_TYPES = frozenset(
    {"string", "integer", "number", "boolean", "object", "array", "datetime"}
)


class ContractError(ValueError):
    """Raised when a contract cannot be parsed or is internally inconsistent."""


@dataclass(frozen=True, slots=True)
class Contract:
    """Validated contract configuration."""

    name: str
    required: dict[str, str]
    optional: dict[str, str]
    unique: tuple[str, ...]
    allowed_values: dict[str, tuple[Any, ...]]
    constraints: tuple[dict[str, Any], ...]
    version: int = 1


def load_contract(path: str | Path) -> Contract:
    """Read a JSON contract and reject unsupported or ambiguous definitions."""
    contract_path = Path(path)
    try:
        payload = json.loads(contract_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"Contract is not valid JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ContractError("Contract root must be a JSON object.")

    version = payload.get("contract_version", 1)
    if version != 1:
        raise ContractError(f"Unsupported contract_version {version!r}; expected 1.")

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ContractError("Contract 'name' must be a non-empty string.")

    required = _field_types(payload.get("required", {}), section="required")
    optional = _field_types(payload.get("optional", {}), section="optional")
    overlap = sorted(set(required) & set(optional))
    if overlap:
        raise ContractError(f"Fields cannot be both required and optional: {', '.join(overlap)}")

    unique_raw = payload.get("unique", [])
    if not isinstance(unique_raw, list) or not all(
        isinstance(field, str) and field for field in unique_raw
    ):
        raise ContractError("Contract 'unique' must be a list of non-empty field paths.")

    allowed_raw = payload.get("allowed_values", {})
    if not isinstance(allowed_raw, dict):
        raise ContractError("Contract 'allowed_values' must be an object.")
    allowed_values: dict[str, tuple[Any, ...]] = {}
    for field, values in allowed_raw.items():
        if not isinstance(field, str) or not field or not isinstance(values, list) or not values:
            raise ContractError("Each allowed_values entry needs a field path and non-empty list.")
        allowed_values[field] = tuple(values)

    constraints_raw = payload.get("constraints", [])
    if not isinstance(constraints_raw, list):
        raise ContractError("Contract 'constraints' must be a list.")
    constraints = tuple(
        _validate_constraint(value, index=index)
        for index, value in enumerate(constraints_raw, start=1)
    )

    return Contract(
        name=name.strip(),
        required=required,
        optional=optional,
        unique=tuple(unique_raw),
        allowed_values=allowed_values,
        constraints=constraints,
        version=version,
    )


def _field_types(value: Any, *, section: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ContractError(f"Contract '{section}' must be an object.")
    result: dict[str, str] = {}
    for field, type_name in value.items():
        if not isinstance(field, str) or not field:
            raise ContractError(f"Contract '{section}' contains an invalid field path.")
        if type_name not in SUPPORTED_TYPES:
            raise ContractError(
                f"Field '{field}' uses unsupported type {type_name!r}; "
                f"choose from {', '.join(sorted(SUPPORTED_TYPES))}."
            )
        result[field] = type_name
    return result


def _validate_constraint(value: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"Constraint {index} must be an object.")

    when = value.get("when")
    if not isinstance(when, dict) or not isinstance(when.get("field"), str) or "equals" not in when:
        raise ContractError(f"Constraint {index} needs when.field and when.equals.")

    require = value.get("require", [])
    if not isinstance(require, list) or not all(
        isinstance(field, str) and field for field in require
    ):
        raise ContractError(f"Constraint {index} 'require' must be a list of field paths.")

    types = _field_types(value.get("types", {}), section=f"constraints[{index}].types")
    for bounds_name in ("minimum", "maximum"):
        bounds = value.get(bounds_name, {})
        if not isinstance(bounds, dict) or not all(
            isinstance(field, str)
            and field
            and isinstance(bound, (int, float))
            and not isinstance(bound, bool)
            for field, bound in bounds.items()
        ):
            raise ContractError(
                f"Constraint {index} '{bounds_name}' must map field paths to numbers."
            )

    return {
        "when": {"field": when["field"], "equals": when["equals"]},
        "require": tuple(require),
        "types": types,
        "minimum": dict(value.get("minimum", {})),
        "maximum": dict(value.get("maximum", {})),
    }
