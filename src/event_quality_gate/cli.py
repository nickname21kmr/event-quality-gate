"""Command-line interface and exit-code contract."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from event_quality_gate import __version__
from event_quality_gate.contract import ContractError, load_contract
from event_quality_gate.reporting import render_report
from event_quality_gate.validator import validate_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="event-quality-gate",
        description="Validate JSONL events against an executable data contract.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    validate = subparsers.add_parser("validate", help="Validate one JSONL input file.")
    validate.add_argument("--contract", required=True, help="Path to a version 1 JSON contract.")
    validate.add_argument("--input", required=True, help="Path to a JSONL event file.")
    validate.add_argument(
        "--format",
        choices=("text", "json", "markdown", "junit"),
        default="text",
        dest="output_format",
        help="Report format (default: text).",
    )
    validate.add_argument("--output", help="Optional report output path; stdout when omitted.")
    validate.add_argument(
        "--max-issues",
        type=_positive_integer,
        default=100,
        help="Maximum issue details to display (default: 100).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "validate":
        parser.print_help(sys.stderr)
        return 2

    try:
        contract = load_contract(args.contract)
        report = validate_file(contract, args.input)
        rendered = render_report(
            report,
            output_format=args.output_format,
            max_issues=args.max_issues,
        )
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
            print(f"Wrote {args.output_format} report to {output_path}")
        else:
            print(rendered, end="")
        return 0 if report.passed else 1
    except (ContractError, OSError) as exc:
        print(f"event-quality-gate: {exc}", file=sys.stderr)
        return 2


def entrypoint() -> None:
    raise SystemExit(main())


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed
