"""Event Quality Gate public package interface."""

from event_quality_gate.contract import Contract, ContractError, load_contract
from event_quality_gate.models import ValidationIssue, ValidationReport
from event_quality_gate.validator import validate_file

__all__ = [
    "Contract",
    "ContractError",
    "ValidationIssue",
    "ValidationReport",
    "load_contract",
    "validate_file",
]

__version__ = "0.1.0"
