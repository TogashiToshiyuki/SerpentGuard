"""Pure presentation helpers shared by the local Streamlit interface and tests."""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection
from typing import Any

from serpentguard.models import DiagnosticSeverity, Finding, ParsedModel

SEVERITY_ORDER: tuple[DiagnosticSeverity, ...] = (
    "ERROR",
    "WARNING",
    "REVIEW",
    "INFO",
)


def severity_counts(findings: list[Finding]) -> dict[DiagnosticSeverity, int]:
    """Return a stable four-severity summary, including zero counts."""
    counts = Counter(finding.severity for finding in findings)
    return {severity: counts[severity] for severity in SEVERITY_ORDER}


def available_rule_ids(findings: list[Finding]) -> list[str]:
    """Return sorted unique rule IDs for filter controls."""
    return sorted({finding.rule_id for finding in findings})


def filter_findings(
    findings: list[Finding],
    *,
    severities: Collection[str],
    rule_ids: Collection[str],
) -> list[Finding]:
    """Apply conjunctive severity and rule filters without changing finding order."""
    severity_filter = set(severities)
    rule_filter = set(rule_ids)
    return [
        finding
        for finding in findings
        if finding.severity in severity_filter and finding.rule_id in rule_filter
    ]


def findings_table_rows(findings: list[Finding]) -> list[dict[str, str]]:
    """Flatten structured findings into the required display-table columns."""
    rows: list[dict[str, str]] = []
    for finding in findings:
        rows.append(
            {
                "Severity": finding.severity,
                "Rule ID": finding.rule_id,
                "File": finding.file or "",
                "Line": _format_line(finding.line, finding.line_end),
                "Object": _format_object(finding.object_type, finding.object_name),
                "Message": finding.message,
            }
        )
    return rows


def parsed_model_debug_payload(model: ParsedModel) -> dict[str, Any]:
    """Create parsed-model JSON data while omitting raw card text fields."""
    payload = model.model_dump(mode="json")
    redacted = _remove_raw_text(payload)
    if not isinstance(redacted, dict):
        raise TypeError("Parsed model payload must be a dictionary")
    return redacted


def _format_line(line: int | None, line_end: int | None) -> str:
    if line is None:
        return ""
    if line_end is not None and line_end != line:
        return f"{line}-{line_end}"
    return str(line)


def _format_object(object_type: str | None, object_name: str | None) -> str:
    if object_type is None:
        return object_name or ""
    if object_name is None:
        return object_type
    return f"{object_type}: {object_name}"


def _remove_raw_text(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _remove_raw_text(item)
            for key, item in value.items()
            if key != "raw_text"
        }
    if isinstance(value, list):
        return [_remove_raw_text(item) for item in value]
    return value
