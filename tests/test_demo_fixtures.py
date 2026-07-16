"""Regression contracts for the redistributable three-minute demo fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from serpentguard.analysis import analyze_model
from serpentguard.geometry import GeometrySamplingConfig, sample_geometry
from serpentguard.parser import parse_bytes

DEMO_ROOT = Path("examples/demo")


@pytest.mark.parametrize(
    "fixture_name",
    [
        "01_valid_minimal.inp",
        "02_undefined_surface.inp",
        "03_contradictory_region.inp",
        "04_pwr_pin_cell.inp",
        "05_overlap_and_gap.inp",
        "06_detector_issues.inp",
        "07_ai_review.inp",
    ],
)
def test_demo_fixture_is_self_documenting(fixture_name: str) -> None:
    text = (DEMO_ROOT / fixture_name).read_text(encoding="utf-8")

    assert "% Demo purpose:" in text
    assert "% Expected findings:" in text
    assert "% Geometry settings:" in text
    assert "not a production reactor model" in text


@pytest.mark.parametrize(
    ("fixture_name", "expected_rule_ids"),
    [
        ("01_valid_minimal.inp", set()),
        ("02_undefined_surface.inp", {"SG004"}),
        ("03_contradictory_region.inp", {"SG008"}),
        ("04_pwr_pin_cell.inp", set()),
        ("05_overlap_and_gap.inp", set()),
        ("06_detector_issues.inp", {"SG021", "SG022", "SG023", "SG024"}),
        ("07_ai_review.inp", {"SG004", "SG007", "SG014"}),
    ],
)
def test_demo_fixture_findings_are_stable(
    fixture_name: str,
    expected_rule_ids: set[str],
) -> None:
    path = DEMO_ROOT / fixture_name
    parsed = parse_bytes(path.read_bytes(), file_name=path.name)
    report = analyze_model(parsed)

    assert {finding.rule_id for finding in report.findings} == expected_rule_ids


def test_demo_diagnostic_fixture_has_overlap_and_gap_candidates() -> None:
    path = DEMO_ROOT / "05_overlap_and_gap.inp"
    parsed = parse_bytes(path.read_bytes(), file_name=path.name)
    result = sample_geometry(
        parsed,
        GeometrySamplingConfig(
            xmin=-0.8,
            xmax=0.8,
            ymin=-0.8,
            ymax=0.8,
            z=0.0,
            resolution=121,
            target_universe="0",
        ),
    )

    assert result.coverage_complete
    assert result.overlap_count > 0
    assert result.undefined_count > 0
