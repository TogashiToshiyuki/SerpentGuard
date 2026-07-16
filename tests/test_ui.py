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
from serpentguard.references import UploadedSourceBundle
from serpentguard.ui import (
    LOCALIZED_FINDING_RULE_IDS,
    available_rule_ids,
    external_reference_table_rows,
    filter_findings,
    findings_table_rows,
    geometry_excluded_cell_rows,
    geometry_representative_rows,
    localized_finding_message,
    localized_finding_title,
    localized_findings_table_rows,
    localized_reference_diagnostic_message,
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


def test_external_reference_rows_are_bilingual_and_keep_canonical_report() -> None:
    bundle = UploadedSourceBundle(
        main_name="main.inp",
        main_content=b'pbed bed bg "data.dat"\n',
        supporting_files=[("data.dat", b"0 0 0 1 pebble\n")],
    )
    report = bundle.resolve_pbed()
    original = report.model_dump(mode="json")

    english = external_reference_table_rows(report, ENGLISH)
    japanese = external_reference_table_rows(report, JAPANESE)

    assert english == [
        {
            "Source file": "main.inp",
            "Reference type": "PBED",
            "Relative target": "data.dat",
            "Resolution status": "Resolved",
            "File size (bytes)": "15",
            "Record count": "1",
        }
    ]
    assert list(japanese[0]) == [
        "参照元ファイル",
        "参照形式",
        "相対参照先",
        "解決状態",
        "ファイルサイズ（byte）",
        "レコード数",
    ]
    assert japanese[0]["解決状態"] == "解決済み"
    assert report.model_dump(mode="json") == original


def test_reference_diagnostic_message_is_localized_without_raw_path() -> None:
    report = UploadedSourceBundle(
        main_name="main.inp",
        main_content=b'pbed bed bg "missing.dat"\n',
        supporting_files=[],
    ).resolve_pbed()
    diagnostic = report.references[0].diagnostics[0]

    assert localized_reference_diagnostic_message(diagnostic, ENGLISH) == (
        "The referenced PBED file is not present in the allowed set."
    )
    assert localized_reference_diagnostic_message(diagnostic, JAPANESE) == (
        "参照されたPBEDファイルが許可されたファイル集合にありません。"
    )


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

    duplicate = ExcludedCell(
        name="repeated",
        location=SourceLocation(
            file_name="model.inp",
            line_start=9,
            line_end=9,
        ),
        reasons=(GeometryExclusion(code="duplicate_cell_name", duplicate_count=2),),
        universe="0",
    )
    english_duplicate = geometry_excluded_cell_rows([duplicate], ENGLISH)[0]
    japanese_duplicate = geometry_excluded_cell_rows([duplicate], JAPANESE)[0]
    assert "Cell name 'repeated' has 2 definitions" in english_duplicate["Reason"]
    assert "Cell名「repeated」が2回定義" in japanese_duplicate["除外理由"]


def test_localized_rule_set_matches_current_analyzer_rules() -> None:
    expected = set(_rule_findings()) | set(_detector_rule_findings())
    assert LOCALIZED_FINDING_RULE_IDS == frozenset(expected)


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


@pytest.mark.parametrize(
    ("rule_id", "title_fragment", "message_fragment"),
    [
        ("SG021", "Detectorの重複定義", "2回"),
        ("SG022", "未定義Energy grid参照", "missing_grid"),
        ("SG023", "正でないビン数", "-1"),
        ("SG024", "無効なビン範囲", "最大値1.0"),
        ("SG025", "極端に多いDetectorビン", "1000001"),
        ("SG026", "Detector範囲が体系境界外", "remote"),
        ("SG027", "未対応Detectorオプション", "dr"),
    ],
)
def test_detector_findings_have_structured_japanese_rendering(
    rule_id: str,
    title_fragment: str,
    message_fragment: str,
) -> None:
    finding = _detector_rule_findings()[rule_id]
    rendered = (
        localized_finding_title(finding, JAPANESE)
        + " "
        + localized_finding_message(finding, JAPANESE)
    )

    assert title_fragment in rendered
    assert message_fragment in rendered
    assert "日本語訳未対応" not in rendered


def _detector_rule_findings() -> dict[str, Finding]:
    common = {
        "file": "detectors.inp",
        "line": 4,
        "line_end": 4,
        "confidence": "high",
    }
    definitions = {
        "SG021": {
            "severity": "ERROR",
            "title": "Duplicate detector",
            "message": "English duplicate message.",
            "object_type": "detector",
            "object_name": "score",
            "evidence": {"definition_count": 2},
        },
        "SG022": {
            "severity": "ERROR",
            "title": "Undefined detector energy-grid reference",
            "message": "English reference message.",
            "object_type": "detector",
            "object_name": "spectrum",
            "evidence": {"reference": "missing_grid"},
        },
        "SG023": {
            "severity": "ERROR",
            "title": "Non-positive bin count",
            "message": "English bin count message.",
            "object_type": "detector",
            "object_name": "mesh",
            "evidence": {"option": "dx", "bin_count": -1},
        },
        "SG024": {
            "severity": "ERROR",
            "title": "Invalid bin range",
            "message": "English bounds message.",
            "object_type": "detector",
            "object_name": "mesh",
            "evidence": {"option": "dy", "minimum": 2.0, "maximum": 1.0},
        },
        "SG025": {
            "severity": "REVIEW",
            "title": "Extreme detector bin count",
            "message": "English total message.",
            "object_type": "detector",
            "object_name": "large",
            "evidence": {"total_bin_count": 1000001, "threshold": 1000000},
        },
        "SG026": {
            "severity": "REVIEW",
            "title": "Detector extent outside available geometry bounds",
            "message": "English extent message.",
            "object_type": "detector",
            "object_name": "remote",
            "evidence": {},
        },
        "SG027": {
            "severity": "INFO",
            "title": "Unsupported detector option",
            "message": "English option message.",
            "object_type": "detector",
            "object_name": "score",
            "evidence": {"option": "dr"},
        },
    }
    return {
        rule_id: Finding.model_validate({"rule_id": rule_id, **common, **definition})
        for rule_id, definition in definitions.items()
    }
