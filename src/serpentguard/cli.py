"""Command-line entry point for local parsing and static analysis."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from serpentguard.analysis import analyze_model, has_unrecoverable_parse_failure
from serpentguard.models import AnalysisReport, Finding
from serpentguard.parser import parse_file

_SEVERITY_ORDER = ("ERROR", "WARNING", "REVIEW", "INFO")


def _check_input(args: argparse.Namespace) -> int:
    """Parse and analyze one local input file."""
    parsed = parse_file(args.input_file)
    report = analyze_model(parsed)

    if args.output_format == "json":
        print(report.model_dump_json(indent=2))
    else:
        _print_text_report(args.input_file, report)

    if has_unrecoverable_parse_failure(parsed):
        return 2
    if any(finding.severity == "ERROR" for finding in report.findings):
        return 1
    return 0


def _print_text_report(input_file: Path, report: AnalysisReport) -> None:
    summary = report.model_summary
    print(f"File: {input_file}")
    print(f"Surfaces: {summary['surfaces']}")
    print(f"Cells: {summary['cells']}")
    print(f"Materials: {summary['materials']}")
    print(f"Unknown cards: {summary['unknown_cards']}")
    print(f"Findings: {len(report.findings)}")

    counts = Counter(item.severity for item in report.findings)
    for severity in _SEVERITY_ORDER:
        print(f"\n{severity} ({counts[severity]})")
        for finding in report.findings:
            if finding.severity == severity:
                print(_format_finding(finding))


def _format_finding(finding: Finding) -> str:
    location = finding.file or "<unknown>"
    if finding.line is not None:
        line = str(finding.line)
        if finding.line_end is not None and finding.line_end != finding.line:
            line = f"{line}-{finding.line_end}"
        location = f"{location}:{line}"

    object_label = ""
    if finding.object_type is not None:
        object_label = f" [{finding.object_type}"
        if finding.object_name is not None:
            object_label += f":{finding.object_name}"
        object_label += "]"
    return (
        f"  {finding.rule_id} {location}{object_label} "
        f"({finding.confidence} confidence): {finding.message}"
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the SerpentGuard command-line parser."""
    parser = argparse.ArgumentParser(
        prog="serpentguard",
        description=(
            "Local deterministic preflight checks for a limited subset of "
            "Serpent input syntax."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser(
        "check",
        help="Parse and statically analyze a local input file.",
        description=(
            "Parse one local file and run deterministic symbol-table checks. "
            "Geometry, detector, and AI analysis are not performed."
        ),
    )
    check_parser.add_argument(
        "input_file",
        type=Path,
        help="Path to a local UTF-8 Serpent input file.",
    )
    check_parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Report format (default: text).",
    )
    check_parser.set_defaults(handler=_check_input)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the SerpentGuard command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
