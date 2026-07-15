"""Tests for pure Streamlit presentation helpers."""

from __future__ import annotations

import json

import pytest

from serpentguard.geometry import (
    ExcludedCell,
    GeometryExclusion,
    RepresentativePoint,
)
from serpentguard.i18n import ENGLISH, JAPANESE
from serpentguard.models import Finding, SourceLocation
from serpentguard.parser import parse_text
from serpentguard.ui import (
    LOCALIZED_FINDING_RULE_IDS,
    available_rule_ids,
    filter_findings,
    findings_table_rows,
    geometry_excluded_cell_rows,
    geometry_representative_rows,
    localized_finding_message,
    localized_finding_title,
    localized_findings_table_rows,
    parsed_model_debug_payload,
    severity_counts,
    severity_display_label,
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


def test_severity_labels_are_localized_but_filters_remain_canonical() -> None:
    finding = _finding("SG004", "ERROR", line=7)

    assert severity_display_label(finding.severity, ENGLISH) == "ERROR"
    assert severity_display_label(finding.severity, JAPANESE) == "エラー"
    assert filter_findings(
        [finding],
        severities=[finding.severity],
        rule_ids=[finding.rule_id],
    ) == [finding]
    assert (
        filter_findings(
            [finding],
            severities=["エラー"],
            rule_ids=[finding.rule_id],
        )
        == []
    )


def test_japanese_findings_table_headings_and_values() -> None:
    finding = _rule_findings()["SG004"]

    rows = localized_findings_table_rows([finding], JAPANESE)

    assert list(rows[0]) == [
        "重大度",
        "ルールID",
        "ファイル",
        "行",
        "対象",
        "メッセージ",
    ]
    assert rows[0]["重大度"] == "エラー"
    assert rows[0]["ルールID"] == "SG004"
    assert rows[0]["対象"] == "Cell: fuel"
    assert "missing_surface" in rows[0]["メッセージ"]


@pytest.mark.parametrize(
    ("rule_id", "expected_fragments"),
    [
        ("SG001", ("Surfaceの重複定義", "fuelsurf", "2回")),
        ("SG002", ("Cellの重複定義", "fuelcell", "2回")),
        ("SG003", ("Materialの重複定義", "fuel", "2回")),
        ("SG004", ("未定義Surface参照", "fuel", "missing_surface")),
        ("SG005", ("未定義Material参照", "fuelcell", "missing_material")),
        ("SG006", ("未使用Surface", "spare_surface")),
        ("SG007", ("未使用Material", "spare_material")),
        ("SG008", ("Surface符号条件の矛盾", "fuelsurf", "正側条件1件")),
        ("SG009", ("領域条件の重複", "-fuelsurf", "2回")),
        ("SG010", ("過度に複雑な領域式", "参照数21", "上限20")),
        ("SG011", ("未終了のブロックコメント", "12行目")),
        ("SG014", ("未対応カード", "set")),
        ("SG015", ("パーサーリカバリ", "不正なSurfaceカード")),
    ],
)
def test_all_active_rules_have_structured_japanese_rendering(
    rule_id: str,
    expected_fragments: tuple[str, ...],
) -> None:
    finding = _rule_findings()[rule_id]

    rendered = (
        localized_finding_title(finding, JAPANESE)
        + " "
        + localized_finding_message(finding, JAPANESE)
    )

    assert "日本語訳未対応" not in rendered
    assert all(fragment in rendered for fragment in expected_fragments)


def test_localization_does_not_mutate_finding() -> None:
    finding = _rule_findings()["SG008"]
    original = finding.model_dump(mode="json")

    localized_finding_title(finding, JAPANESE)
    localized_finding_message(finding, JAPANESE)
    localized_findings_table_rows([finding], JAPANESE)

    assert finding.model_dump(mode="json") == original


def test_missing_structured_evidence_uses_visible_english_fallback() -> None:
    finding = _finding("SG004", "ERROR", line=7)

    message = localized_finding_message(finding, JAPANESE)

    assert message == "[日本語訳未対応] Message SG004"


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


def test_geometry_presentation_rows_are_bilingual_and_structured() -> None:
    point = RepresentativePoint(
        x=0.125,
        y=-0.25,
        involved_cells=("left", "right"),
    )
    excluded = ExcludedCell(
        name="unsupported",
        location=SourceLocation(
            file_name="model.inp",
            line_start=7,
            line_end=7,
        ),
        reasons=(
            GeometryExclusion(
                code="unsupported_surface_type",
                surface_name="plane",
                surface_type="px",
            ),
        ),
    )

    assert geometry_representative_rows([point], ENGLISH) == [
        {"x": "0.125", "y": "-0.25", "Involved cells": "left, right"}
    ]
    assert geometry_representative_rows([point], JAPANESE) == [
        {"x": "0.125", "y": "-0.25", "関係するCell": "left, right"}
    ]
    assert geometry_excluded_cell_rows([excluded], ENGLISH)[0] == {
        "Cell": "unsupported",
        "File": "model.inp",
        "Line": "7",
        "Reason": "Surface 'plane' uses unsupported type 'px'.",
    }
    japanese_row = geometry_excluded_cell_rows([excluded], JAPANESE)[0]
    assert japanese_row["Cell"] == "unsupported"
    assert japanese_row["ファイル"] == "model.inp"
    assert "Surface「plane」" in japanese_row["除外理由"]
    assert "px" in japanese_row["除外理由"]


def test_localized_rule_set_matches_current_analyzer_rules() -> None:
    assert LOCALIZED_FINDING_RULE_IDS == frozenset(_rule_findings())


def _rule_findings() -> dict[str, Finding]:
    common = {
        "file": "model.inp",
        "line": 8,
        "line_end": 8,
        "confidence": "high",
    }
    definitions: dict[str, dict[str, object]] = {
        "SG001": {
            "severity": "ERROR",
            "title": "Duplicate surface",
            "message": "English duplicate surface message.",
            "object_type": "surface",
            "object_name": "fuelsurf",
            "evidence": {"definition_count": 2},
        },
        "SG002": {
            "severity": "ERROR",
            "title": "Duplicate cell",
            "message": "English duplicate cell message.",
            "object_type": "cell",
            "object_name": "fuelcell",
            "evidence": {"definition_count": 2},
        },
        "SG003": {
            "severity": "ERROR",
            "title": "Duplicate material",
            "message": "English duplicate material message.",
            "object_type": "material",
            "object_name": "fuel",
            "evidence": {"definition_count": 2},
        },
        "SG004": {
            "severity": "ERROR",
            "title": "Undefined surface reference",
            "message": "English undefined surface message.",
            "object_type": "cell",
            "object_name": "fuel",
            "evidence": {"reference": "missing_surface"},
        },
        "SG005": {
            "severity": "ERROR",
            "title": "Undefined material reference",
            "message": "English undefined material message.",
            "object_type": "cell",
            "object_name": "fuelcell",
            "evidence": {"reference": "missing_material"},
        },
        "SG006": {
            "severity": "INFO",
            "title": "Unused surface",
            "message": "English unused surface message.",
            "object_type": "surface",
            "object_name": "spare_surface",
            "evidence": {},
        },
        "SG007": {
            "severity": "INFO",
            "title": "Unused material",
            "message": "English unused material message.",
            "object_type": "material",
            "object_name": "spare_material",
            "evidence": {},
        },
        "SG008": {
            "severity": "WARNING",
            "title": "Contradictory signed surface",
            "message": "English contradictory message.",
            "object_type": "cell",
            "object_name": "fuelcell",
            "evidence": {
                "surface": "fuelsurf",
                "intersection_term": 1,
                "positive_count": 1,
                "negative_count": 1,
            },
        },
        "SG009": {
            "severity": "WARNING",
            "title": "Duplicate region condition",
            "message": "English duplicate condition message.",
            "object_type": "cell",
            "object_name": "fuelcell",
            "evidence": {
                "signed_condition": "-fuelsurf",
                "occurrences": 2,
                "intersection_term": 1,
            },
        },
        "SG010": {
            "severity": "REVIEW",
            "title": "Excessively complex region expression",
            "message": "English complexity message.",
            "object_type": "cell",
            "object_name": "fuelcell",
            "evidence": {
                "exceeded_thresholds": {
                    "surface_references": {"actual": 21, "limit": 20}
                }
            },
        },
        "SG011": {
            "severity": "ERROR",
            "title": "Unterminated block comment",
            "message": "English block comment message.",
            "object_type": "comment",
            "object_name": None,
            "evidence": {"opening_line": 12},
        },
        "SG014": {
            "severity": "INFO",
            "title": "Unsupported card",
            "message": "English unsupported card message.",
            "object_type": "card",
            "object_name": "set",
            "evidence": {"keyword": "set", "token_count": 3},
        },
        "SG015": {
            "severity": "ERROR",
            "title": "Parser recovery used",
            "message": "English parser recovery message.",
            "object_type": "card",
            "object_name": "surf",
            "evidence": {"parser_code": "PARSER001", "recoverable": True},
        },
    }
    return {
        rule_id: Finding.model_validate({"rule_id": rule_id, **common, **definition})
        for rule_id, definition in definitions.items()
    }
