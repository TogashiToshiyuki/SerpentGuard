"""Rule-by-rule tests for deterministic static analysis."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from serpentguard.analysis import AnalysisConfig, SymbolTable, analyze_model
from serpentguard.cli import main
from serpentguard.models import Finding
from serpentguard.parser import parse_file, parse_text

EXAMPLES = Path(__file__).parent.parent / "examples"


def _analyze(text: str, *, config: AnalysisConfig | None = None):
    return analyze_model(parse_text(text, file_name="rules.inp"), config=config)


def _rule_ids(text: str, *, config: AnalysisConfig | None = None) -> list[str]:
    return [item.rule_id for item in _analyze(text, config=config).findings]


def test_sg001_duplicate_surface_and_symbol_table() -> None:
    parsed = parse_file(EXAMPLES / "duplicate_surface.inp")
    symbols = SymbolTable.from_model(parsed)
    report = analyze_model(parsed)

    assert len(symbols.surfaces["fuelsurf"]) == 2
    assert [item.rule_id for item in report.findings] == ["SG001"]
    finding = report.findings[0]
    assert finding.severity == "ERROR"
    assert finding.object_type == "surface"
    assert finding.object_name == "fuelsurf"
    assert finding.evidence["definition_count"] == 2


def test_sg002_duplicate_cell() -> None:
    rules = _rule_ids(
        "surf s cyl 0 0 1\ncell c 0 m -s\ncell c 0 m -s\nmat m -1\n1001.09c -1\n"
    )

    assert rules == ["SG002"]


def test_sg003_duplicate_material() -> None:
    rules = _rule_ids(
        "surf s cyl 0 0 1\n"
        "cell c 0 m -s\n"
        "mat m -1\n"
        "1001.09c -1\n"
        "mat m -2\n"
        "1001.09c -1\n"
    )

    assert rules == ["SG003"]


def test_sg004_undefined_surface_has_structured_evidence() -> None:
    report = analyze_model(parse_file(EXAMPLES / "undefined_surface.inp"))

    assert [item.rule_id for item in report.findings] == ["SG004"]
    finding = report.findings[0]
    assert finding.title == "Undefined surface reference"
    assert finding.file is not None and finding.file.endswith("undefined_surface.inp")
    assert finding.line == 7
    assert finding.object_type == "cell"
    assert finding.object_name == "fuelcell"
    assert finding.evidence["reference"] == "missingsurf"
    assert finding.confidence == "high"


def test_sg005_undefined_material() -> None:
    report = _analyze("surf s cyl 0 0 1\ncell c 0 missing -s\n")

    assert [item.rule_id for item in report.findings] == ["SG005"]
    assert report.findings[0].severity == "ERROR"
    assert report.findings[0].evidence["reference"] == "missing"


def test_sg006_unused_surface_is_info() -> None:
    report = _analyze(
        "surf used cyl 0 0 1\n"
        "surf spare cyl 0 0 2\n"
        "cell c 0 m -used\n"
        "mat m -1\n"
        "1001.09c -1\n"
    )

    assert [item.rule_id for item in report.findings] == ["SG006"]
    assert report.findings[0].severity == "INFO"
    assert report.findings[0].object_name == "spare"


def test_sg007_unused_material_is_info() -> None:
    report = _analyze(
        "surf s cyl 0 0 1\n"
        "cell c 0 m -s\n"
        "mat m -1\n"
        "1001.09c -1\n"
        "mat spare -1\n"
        "1001.09c -1\n"
    )

    assert [item.rule_id for item in report.findings] == ["SG007"]
    assert report.findings[0].severity == "INFO"
    assert report.findings[0].object_name == "spare"


def test_sg008_contradictory_signed_surface() -> None:
    report = analyze_model(parse_file(EXAMPLES / "contradictory_cell.inp"))

    assert [item.rule_id for item in report.findings] == ["SG008"]
    finding = report.findings[0]
    assert finding.severity == "WARNING"
    assert finding.evidence["intersection_term"] == 1
    assert finding.evidence["positive_count"] == 1
    assert finding.evidence["negative_count"] == 1


def test_sg009_duplicate_signed_condition() -> None:
    report = _analyze("surf s cyl 0 0 1\ncell c 0 m -s -s\nmat m -1\n1001.09c -1\n")

    assert [item.rule_id for item in report.findings] == ["SG009"]
    assert report.findings[0].severity == "WARNING"
    assert report.findings[0].evidence["signed_condition"] == "-s"


def test_sg010_configured_complexity_threshold_is_review() -> None:
    report = _analyze(
        "surf s1 cyl 0 0 1\n"
        "surf s2 cyl 0 0 2\n"
        "surf s3 cyl 0 0 3\n"
        "cell c 0 m -s1 -s2 -s3\n"
        "mat m -1\n"
        "1001.09c -1\n",
        config=AnalysisConfig(max_region_references=2),
    )

    assert [item.rule_id for item in report.findings] == ["SG010"]
    finding = report.findings[0]
    assert finding.severity == "REVIEW"
    assert finding.evidence["exceeded_thresholds"] == {
        "surface_references": {"actual": 3, "limit": 2}
    }

    union_report = _analyze(
        "surf s cyl 0 0 1\ncell c 0 m -s:s:-s\nmat m -1\n1001.09c -1\n",
        config=AnalysisConfig(max_union_operators=1),
    )
    union_finding = next(
        item for item in union_report.findings if item.rule_id == "SG010"
    )
    assert union_finding.evidence["exceeded_thresholds"] == {
        "union_operators": {"actual": 2, "limit": 1}
    }


def test_union_terms_are_analyzed_independently() -> None:
    report = _analyze(
        "surf s cyl 0 0 1\n"
        "surf t cyl 0 0 2\n"
        "cell separated 0 m -s:s\n"
        "cell contradictory 0 m -t t : s\n"
        "mat m -1\n"
        "1001.09c -1\n"
    )

    contradictions = [item for item in report.findings if item.rule_id == "SG008"]
    duplicates = [item for item in report.findings if item.rule_id == "SG009"]
    assert len(contradictions) == 1
    assert contradictions[0].object_name == "contradictory"
    assert contradictions[0].evidence["intersection_term"] == 1
    assert duplicates == []


def test_sg011_unterminated_block_comment_is_integrated() -> None:
    report = _analyze(
        "surf s cyl 0 0 1\ncell c 0 m -s\nmat m -1\n1001.09c -1\n/* unfinished\n"
    )

    assert [item.rule_id for item in report.findings] == ["SG011"]
    assert report.findings[0].severity == "ERROR"
    assert report.findings[0].line == 5


def test_sg014_unsupported_card_is_integrated() -> None:
    report = analyze_model(parse_file(EXAMPLES / "unknown_card.inp"))

    assert [item.rule_id for item in report.findings] == ["SG014"]
    finding = report.findings[0]
    assert finding.severity == "INFO"
    assert finding.object_name == "set"
    assert finding.evidence["token_count"] == 3


def test_sg015_parser_recovery_is_integrated_without_raw_value() -> None:
    report = _analyze("surf broken cyl not-a-number 0 1\n")

    assert [item.rule_id for item in report.findings] == ["SG015"]
    finding = report.findings[0]
    assert finding.severity == "ERROR"
    assert finding.evidence == {"parser_code": "PARSER001", "recoverable": True}
    assert "not-a-number" not in finding.message


def test_finding_rejects_unknown_severity() -> None:
    with pytest.raises(ValidationError):
        Finding(
            rule_id="TEST",
            severity="CRITICAL",  # type: ignore[arg-type]
            title="Invalid",
            message="Invalid severity",
            evidence={},
            confidence="high",
        )


def test_cli_exit_codes_and_grouped_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["check", str(EXAMPLES / "valid_minimal.inp")]) == 0
    clean_output = capsys.readouterr().out
    assert "ERROR (0)" in clean_output

    assert main(["check", str(EXAMPLES / "duplicate_surface.inp")]) == 1
    error_output = capsys.readouterr().out
    assert "ERROR (1)" in error_output
    assert "SG001" in error_output

    missing = tmp_path / "missing.inp"
    assert main(["check", str(missing)]) == 2
    failure_output = capsys.readouterr().out
    assert "SG015" in failure_output


def test_cli_json_report_is_structured_and_has_no_raw_input(
    capsys: pytest.CaptureFixture[str],
) -> None:
    return_code = main(
        ["check", str(EXAMPLES / "unknown_card.inp"), "--format", "json"]
    )

    payload = json.loads(capsys.readouterr().out)
    assert return_code == 0
    assert payload["model_summary"]["unknown_cards"] == 1
    assert payload["findings"][0]["rule_id"] == "SG014"
    assert payload["findings"][0]["file"].endswith("unknown_card.inp")
    assert "set bc 2" not in json.dumps(payload)
