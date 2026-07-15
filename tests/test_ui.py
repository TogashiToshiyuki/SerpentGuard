"""Tests for pure Streamlit presentation helpers."""

from __future__ import annotations

import json

from serpentguard.models import Finding
from serpentguard.parser import parse_text
from serpentguard.ui import (
    available_rule_ids,
    filter_findings,
    findings_table_rows,
    parsed_model_debug_payload,
    severity_counts,
)


def _finding(
    rule_id: str,
    severity: str,
    *,
    line: int,
    line_end: int | None = None,
) -> Finding:
    return Finding.model_validate(
        {
            "rule_id": rule_id,
            "severity": severity,
            "title": f"Title {rule_id}",
            "message": f"Message {rule_id}",
            "file": "model.inp",
            "line": line,
            "line_end": line_end or line,
            "object_type": "cell",
            "object_name": "fuel",
            "evidence": {"example": rule_id},
            "confidence": "high",
        }
    )


def test_finding_filters_counts_and_table_rows() -> None:
    findings = [
        _finding("SG004", "ERROR", line=7),
        _finding("SG010", "REVIEW", line=9, line_end=11),
    ]

    assert severity_counts(findings) == {
        "ERROR": 1,
        "WARNING": 0,
        "REVIEW": 1,
        "INFO": 0,
    }
    assert available_rule_ids(findings) == ["SG004", "SG010"]
    assert filter_findings(
        findings,
        severities=["REVIEW"],
        rule_ids=["SG004", "SG010"],
    ) == [findings[1]]
    assert findings_table_rows(findings) == [
        {
            "Severity": "ERROR",
            "Rule ID": "SG004",
            "File": "model.inp",
            "Line": "7",
            "Object": "cell: fuel",
            "Message": "Message SG004",
        },
        {
            "Severity": "REVIEW",
            "Rule ID": "SG010",
            "File": "model.inp",
            "Line": "9-11",
            "Object": "cell: fuel",
            "Message": "Message SG010",
        },
    ]


def test_parsed_model_debug_payload_omits_raw_card_text() -> None:
    parsed = parse_text(
        "surf secret_surface cyl 0 0 1\ncell fuel 0 void -secret_surface\n",
        file_name="private.inp",
    )

    payload = parsed_model_debug_payload(parsed)
    serialized = json.dumps(payload)

    assert payload["source_files"] == ["private.inp"]
    assert payload["surfaces"][0]["name"] == "secret_surface"
    assert "raw_text" not in serialized
    assert "surf secret_surface cyl 0 0 1" not in serialized
