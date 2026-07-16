"""Privacy and allowlist tests for the optional AI review payload."""

from __future__ import annotations

import json
import socket

import pytest
from pydantic import ValidationError

from serpentguard.ai_payload import (
    AIReviewPayload,
    PayloadPrivacyError,
    assert_payload_privacy,
    build_ai_review_payload,
    sanitize_analysis_purpose,
)
from serpentguard.analysis import analyze_model
from serpentguard.geometry import GeometrySamplingConfig, sample_geometry
from serpentguard.parser import parse_text
from serpentguard.ui import ai_generation_requested


def _payload_for(
    text: str,
    *,
    file_name: str = "model.inp",
    purpose: str = "Review deterministic preflight findings.",
):
    parsed = parse_text(text, file_name=file_name)
    report = analyze_model(parsed)
    return build_ai_review_payload(
        analysis_purpose=purpose,
        report=report,
        parsed_model=parsed,
    )


def test_payload_is_versioned_and_forbids_unexpected_fields() -> None:
    payload = _payload_for("surf boundary sqc 0 0 1\n")

    assert payload.schema_version == "1.0"
    with pytest.raises(ValidationError):
        AIReviewPayload.model_validate(
            {**payload.model_dump(mode="python"), "raw_text": "forbidden"}
        )


def test_raw_input_comments_and_material_composition_are_not_copied() -> None:
    raw_input = (
        "% PRIVATE_COMMENT_MARKER\n"
        "surf private_boundary sqc 0 0 10\n"
        "cell core 0 private_fuel -private_boundary\n"
        "cell exterior 0 outside private_boundary\n"
        "mat private_fuel -10\n"
        "99999.09c -1.0 /* PRIVATE_BLOCK_COMMENT */\n"
    )
    payload = _payload_for(raw_input)
    serialized = payload.model_dump_json()

    assert "PRIVATE_COMMENT_MARKER" not in serialized
    assert "PRIVATE_BLOCK_COMMENT" not in serialized
    assert "99999.09c" not in serialized
    assert "composition" not in serialized
    assert "raw_text" not in serialized
    assert "region_expression" not in serialized


def test_absolute_paths_are_reduced_or_redacted() -> None:
    private_path = r"C:\Users\researcher\private project\model.inp"
    parsed = parse_text("surf unused cyl 0 0 1\n", file_name=private_path)
    report = analyze_model(parsed)
    report.findings[0].evidence["local_path"] = private_path
    report.findings[0].message = f"Review {private_path} before proceeding."

    payload = build_ai_review_payload(
        analysis_purpose=f"Inspect {private_path}",
        report=report,
        parsed_model=parsed,
    )
    serialized = payload.model_dump_json()

    assert r"C:\Users" not in serialized
    assert "researcher" not in serialized
    assert "private project" not in serialized
    assert payload.findings.items[0].source_file == "model.inp"
    assert "redacted absolute path" in serialized


def test_secret_values_and_unexpected_sensitive_evidence_fields_are_removed() -> None:
    api_key = "sk-proj-abcdefghijklmnopqrstuv"
    parsed = parse_text("surf unused cyl 0 0 1\n", file_name="model.inp")
    report = analyze_model(parsed)
    finding = report.findings[0]
    finding.message = f"OPENAI_API_KEY={api_key}"
    finding.evidence.update(
        {
            "raw_text": "surf private cyl 0 0 99",
            "raw_text_excerpt": "cell private 0 void -99",
            "composition": {"99999.09c": -1.0},
            "comments": "% unpublished comment",
            "api_key": api_key,
            "client_secret": "unprefixed-private-value",
            "safe_count": 3,
        }
    )

    payload = build_ai_review_payload(
        analysis_purpose=f"Use API_KEY={api_key}",
        report=report,
        parsed_model=parsed,
    )
    serialized = payload.model_dump_json()

    assert api_key not in serialized
    assert "sk-proj" not in serialized
    assert "99999.09c" not in serialized
    assert "unpublished comment" not in serialized
    assert "unprefixed-private-value" not in serialized
    assert "raw_text" not in serialized
    assert "composition" not in serialized
    assert "api_key" not in serialized.lower()
    assert payload.findings.items[0].evidence["safe_count"] == 3
    assert (
        not {
            "raw_text",
            "raw_text_excerpt",
            "composition",
            "comments",
            "api_key",
            "client_secret",
        }
        & payload.findings.items[0].evidence.keys()
    )


def test_source_like_analysis_purpose_and_comments_are_omitted() -> None:
    source_purpose = (
        "% full source comment\n"
        "mat fuel -10\n"
        "92235.09c -1.0\n"
        "/* another source comment */\n"
    )

    assert sanitize_analysis_purpose(source_purpose) == (
        "[omitted possible Serpent input]"
    )
    assert sanitize_analysis_purpose("Review bins % PRIVATE_INLINE_COMMENT") == (
        "Review bins"
    )


def test_long_object_names_are_bounded_without_mutating_the_parsed_model() -> None:
    long_name = "detector_" + "x" * 200
    parsed = parse_text(f"det {long_name}\n", file_name="model.inp")
    report = analyze_model(parsed)

    payload = build_ai_review_payload(
        analysis_purpose="Review detector metadata.",
        report=report,
        parsed_model=parsed,
    )

    assert parsed.detectors[0].name == long_name
    assert len(payload.detector_metadata.items[0].name) == 96
    assert payload.detector_metadata.items[0].name.endswith("…")


def test_builder_includes_only_the_explicitly_selected_findings() -> None:
    parsed = parse_text(
        "surf first cyl 0 0 1\nsurf second cyl 0 0 2\n",
        file_name="model.inp",
    )
    report = analyze_model(parsed)
    selected = [report.findings[1]]

    payload = build_ai_review_payload(
        analysis_purpose="Review one selected finding.",
        report=report,
        parsed_model=parsed,
        selected_findings=selected,
    )

    assert payload.findings.selected_count == 1
    assert payload.findings.included_count == 1
    assert payload.findings.items[0].object_name == selected[0].object_name


def test_geometry_payload_contains_statistics_but_not_grids_or_coordinates() -> None:
    parsed = parse_text(
        "surf boundary sqc 0 0 1\n"
        "cell domain 0 void -boundary\n"
        "cell exterior 0 outside boundary\n",
        file_name="geometry.inp",
    )
    report = analyze_model(parsed)
    geometry = sample_geometry(
        parsed,
        GeometrySamplingConfig(
            xmin=-1,
            xmax=1,
            ymin=-1,
            ymax=1,
            z=0,
            resolution=20,
            target_universe="0",
        ),
    )

    payload = build_ai_review_payload(
        analysis_purpose="Review geometry statistics.",
        report=report,
        parsed_model=parsed,
        geometry_result=geometry,
    )
    serialized = payload.model_dump_json()

    assert payload.geometry_statistics is not None
    assert payload.geometry_statistics.total_points == 400
    assert payload.geometry_statistics.selected_universe == "0"
    assert "classifications" not in serialized
    assert "category_grid" not in serialized
    assert "x_coordinates" not in serialized
    assert "representative" not in serialized
    assert "included_cells" not in serialized


def test_detector_metadata_is_limited_to_selected_structured_fields() -> None:
    parsed = parse_text(
        "ene groups 3 10 1e-9 10\n"
        "det flux n de groups dx -1 1 10 dy -2 2 20 dr -1 void\n",
        file_name="detectors.inp",
    )
    report = analyze_model(parsed)

    payload = build_ai_review_payload(
        analysis_purpose="Review detector bins.",
        report=report,
        parsed_model=parsed,
    )
    item = payload.detector_metadata.items[0]
    serialized = payload.model_dump_json()

    assert item.name == "flux"
    assert item.particle == "n"
    assert item.energy_grid_references == ["groups"]
    assert [(axis.axis, axis.bin_count) for axis in item.mesh_axes] == [
        ("x", 10),
        ("y", 20),
    ]
    assert item.unsupported_option_names == ["dr"]
    assert "tokens" not in serialized
    assert "raw_text" not in serialized


def test_builder_does_not_require_or_attempt_network_access(monkeypatch) -> None:
    def fail_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", fail_network)

    payload = _payload_for("surf unused cyl 0 0 1\n")

    assert payload.object_counts.surfaces == 1


def test_generation_gate_requires_explicit_button_press_and_consent() -> None:
    assert not ai_generation_requested(
        button_pressed=False,
        consent_confirmed=True,
        payload_available=True,
    )
    assert not ai_generation_requested(
        button_pressed=True,
        consent_confirmed=False,
        payload_available=True,
    )
    assert not ai_generation_requested(
        button_pressed=True,
        consent_confirmed=True,
        payload_available=False,
    )
    assert ai_generation_requested(
        button_pressed=True,
        consent_confirmed=True,
        payload_available=True,
    )


def test_defense_in_depth_audit_rejects_manually_injected_private_data() -> None:
    payload = _payload_for("surf unused cyl 0 0 1\n")
    unsafe = payload.model_copy(update={"analysis_purpose": r"C:\private\model.inp"})

    with pytest.raises(PayloadPrivacyError, match="Absolute path"):
        assert_payload_privacy(unsafe)


def test_payload_serializes_as_json_without_material_or_source_models() -> None:
    payload = _payload_for("surf unused cyl 0 0 1\n")
    decoded = json.loads(payload.model_dump_json())

    assert set(decoded) == {
        "schema_version",
        "analysis_purpose",
        "object_counts",
        "findings",
        "geometry_statistics",
        "detector_metadata",
        "limitations",
    }
