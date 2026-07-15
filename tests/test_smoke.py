"""Foundation smoke tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from serpentguard import __version__
from serpentguard.i18n import LANGUAGE_SESSION_KEY
from serpentguard.references import ExternalResolutionReport


def test_package_imports() -> None:
    assert __version__ == "0.1.0"


def test_streamlit_page_waits_for_explicit_run() -> None:
    app = AppTest.from_file("app.py").run()

    assert not app.exception
    assert [(item.label, item.value) for item in app.selectbox] == [("Language", "en")]
    assert app.selectbox[0].options == ["English", "日本語"]
    assert [title.value for title in app.title] == ["SerpentGuard"]
    assert len(app.warning) == 1
    assert "limited syntax subset" in app.warning[0].value
    assert [(item.label, item.value) for item in app.radio] == [
        ("Input mode", "uploaded_bundle")
    ]
    assert [item.value for item in app.subheader] == [
        "1. Select input source",
        "2. Analysis purpose",
        "3. Run check",
        "4. Summary counts",
        "5. Findings table",
        "6. Geometry plot",
        "7. AI explanation",
    ]
    assert [
        (uploader.label, uploader.disabled) for uploader in app.get("file_uploader")
    ] == [
        ("Main input file", False),
        ("Supporting files (optional)", False),
    ]
    assert app.get("file_uploader")[1].accept_multiple_files
    assert [(item.label, item.value) for item in app.text_area] == [
        ("Purpose (optional)", "")
    ]
    assert [(button.label, button.disabled) for button in app.button] == [
        ("Run check", True)
    ]
    info_messages = [item.value for item in app.info]
    assert any("Analysis is local" in message for message in info_messages)
    assert (
        "Run the deterministic input check before configuring geometry sampling."
        in info_messages
    )
    assert (
        "AI review is optional and has not been enabled in this milestone."
        in info_messages
    )
    assert len(app.get("metric")) == 0
    assert len(app.get("dataframe")) == 0


def test_streamlit_runs_parser_and_rule_engine_after_button_press() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    fixture = Path("examples/duplicate_surface.inp").read_bytes()

    app.get("file_uploader")[0].upload("duplicate_surface.inp", fixture).run()
    assert not app.button[0].disabled
    assert len(app.get("metric")) == 0

    app.button[0].click().run()

    assert not app.exception
    metrics = {item.label: item.value for item in app.get("metric")}
    assert metrics == {
        "Surfaces": "3",
        "Cells": "2",
        "Materials": "1",
        "Unknown cards": "0",
        "ERROR": "1",
        "WARNING": "0",
        "REVIEW": "0",
        "INFO": "0",
    }
    assert [(item.label, item.value) for item in app.multiselect] == [
        ("Severity", ["ERROR", "WARNING", "REVIEW", "INFO"]),
        ("Rule ID", ["SG001"]),
    ]
    assert len(app.get("dataframe")) == 1
    assert [item.label for item in app.expander] == [
        "Evidence 1: SG001 — fuelsurf",
        "Parsed model JSON (debugging)",
    ]


def test_streamlit_geometry_requires_explicit_form_submission() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    fixture = Path("examples/valid_minimal.inp").read_bytes()
    app.get("file_uploader")[0].upload("valid_minimal.inp", fixture).run()
    app.button[0].click().run()

    assert [(item.label, item.value) for item in app.selectbox] == [
        ("Language", "en"),
        ("Universe", "0"),
    ]
    z_inputs = [item for item in app.number_input if item.label == "z coordinate"]
    assert len(z_inputs) == 1
    assert z_inputs[0].disabled
    geometry_buttons = [
        button
        for button in app.button
        if button.label == "Confirm range and sample geometry"
    ]
    assert len(geometry_buttons) == 1
    assert "serpentguard_geometry_result" not in app.session_state

    geometry_buttons[0].click().run()

    geometry_result = app.session_state["serpentguard_geometry_result"]
    assert geometry_result.config.z == 0.0
    assert geometry_result.config.resolution == 100
    assert geometry_result.selected_universe == "0"
    assert geometry_result.coverage_complete
    assert geometry_result.undefined_detection_enabled
    assert geometry_result.overlap_count == 0
    assert geometry_result.undefined_count == 0
    metrics = {item.label: item.value for item in app.get("metric")}
    assert metrics["Overlap candidates"] == "0"
    assert metrics["Undefined candidates"] == "0"
    assert metrics["Normal points"] == "10000"

    run_button = next(button for button in app.button if button.label == "Run check")
    run_button.click().run()
    assert "serpentguard_geometry_result" not in app.session_state


def test_streamlit_uses_deterministic_nonzero_universe_default_and_selection() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    fixture = (
        b"surf circle cyl 0 0 1\n"
        b"cell local_seven 7 void -circle\n"
        b"cell local_eight 8 void -circle\n"
    )
    app.get("file_uploader")[0].upload("universe.inp", fixture).run()
    app.button[0].click().run()

    universe_selector = next(item for item in app.selectbox if item.label == "Universe")
    assert universe_selector.options == ["7", "8"]
    assert universe_selector.value == "7"
    assert any(
        "Universe 0 was not found" in item.value and "universe '7'" in item.value
        for item in app.info
    )

    universe_selector.set_value("8").run()
    geometry_button = next(
        button
        for button in app.button
        if button.label == "Confirm range and sample geometry"
    )
    geometry_button.click().run()
    geometry_result = app.session_state["serpentguard_geometry_result"]
    assert geometry_result.selected_universe == "8"
    assert geometry_result.included_cells == ("local_eight",)


def test_streamlit_resolves_uploaded_pbed_and_renders_explicit_slice() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    fixture_root = Path("tests/fixtures/pbed/valid")
    app.get("file_uploader")[0].upload(
        "main.inp", (fixture_root / "main.inp").read_bytes()
    ).run()
    app.get("file_uploader")[1].upload(
        "placements.dat", (fixture_root / "placements.dat").read_bytes()
    ).run()

    run_button = next(button for button in app.button if button.label == "Run check")
    run_button.click().run()

    assert not app.exception
    reference_report = app.session_state["serpentguard_external_reference_result"]
    assert isinstance(reference_report, ExternalResolutionReport)
    assert reference_report.references[0].status == "resolved"
    assert reference_report.references[0].record_count == 3
    assert reference_report.unused_supporting_files == ()
    assert any(item.label == "Resolved PBED target" for item in app.selectbox)

    slice_button = next(
        button for button in app.button if button.label == "Render PBED placement slice"
    )
    slice_button.click().run()

    slice_state = app.session_state["serpentguard_pbed_slice_result"]
    assert slice_state["result"].total_placement_count == 3
    assert slice_state["result"].intersecting_placement_count == 1
    report_before = reference_report.model_dump(mode="json")
    slice_before = slice_state["result"].model_dump(mode="json")

    app.selectbox[0].set_value("ja").run()

    report_after = app.session_state["serpentguard_external_reference_result"]
    slice_after = app.session_state["serpentguard_pbed_slice_result"]["result"]
    assert report_after.model_dump(mode="json") == report_before
    assert slice_after.model_dump(mode="json") == slice_before
    assert app.get("file_uploader")[0].value is not None
    assert app.get("file_uploader")[1].value is not None


def test_streamlit_local_project_requires_supporting_file_authorization(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    main = root / "main.inp"
    data = root / "data.dat"
    main.write_text('pbed bed bg "data.dat"\n', encoding="utf-8")
    data.write_text("0 0 0 1 pebble\n", encoding="utf-8")
    app = AppTest.from_file("app.py", default_timeout=30).run()

    app.radio[0].set_value("local_project").run()
    main_field = next(
        item for item in app.text_input if item.label == "Main local input path"
    )
    root_field = next(
        item for item in app.text_input if item.label == "Authorized local root"
    )
    main_field.set_value(str(main)).run()
    root_field.set_value(str(root)).run()
    next(button for button in app.button if button.label == "Run check").click().run()

    preview = app.session_state["serpentguard_external_reference_result"]
    assert preview.references[0].status == "pending_authorization"
    assert preview.references[0].pbed_data is None
    assert str(root) not in preview.model_dump_json()

    authorize = next(
        button
        for button in app.button
        if button.label == "Authorize and read supporting PBED files"
    )
    authorize.click().run()

    resolved = app.session_state["serpentguard_external_reference_result"]
    assert resolved.references[0].status == "resolved"
    assert resolved.references[0].record_count == 1


def test_language_switch_preserves_upload_result_and_canonical_filters() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    fixture = Path("examples/duplicate_surface.inp").read_bytes()
    app.get("file_uploader")[0].upload("duplicate_surface.inp", fixture).run()
    app.button[0].click().run()
    app.multiselect[0].set_value(["ERROR"]).run()

    geometry_button = next(
        button
        for button in app.button
        if button.label == "Confirm range and sample geometry"
    )
    geometry_button.click().run()

    result_before = app.session_state["serpentguard_analysis_result"]
    parsed_before = result_before["parsed"].model_dump(mode="json")
    report_before = result_before["report"].model_dump(mode="json")
    geometry_before = app.session_state["serpentguard_geometry_result"]
    classifications_before = geometry_before.classifications.copy()
    match_counts_before = geometry_before.match_counts.copy()

    app.selectbox[0].set_value("ja").run()

    result_after = app.session_state["serpentguard_analysis_result"]
    assert app.session_state[LANGUAGE_SESSION_KEY] == "ja"
    assert app.get("file_uploader")[0].value is not None
    assert result_after["parsed"].model_dump(mode="json") == parsed_before
    assert result_after["report"].model_dump(mode="json") == report_before
    geometry_after = app.session_state["serpentguard_geometry_result"]
    assert geometry_after.selected_universe == geometry_before.selected_universe
    assert geometry_after.coverage_complete == geometry_before.coverage_complete
    assert geometry_after.config == geometry_before.config
    assert np.array_equal(geometry_after.classifications, classifications_before)
    assert np.array_equal(geometry_after.match_counts, match_counts_before)
    assert [item.value for item in app.multiselect] == [["ERROR"], ["SG001"]]
    assert app.selectbox[1].label == "Universe"
    assert app.selectbox[1].value == "0"
    warning_messages = [item.value for item in app.warning]
    assert any("選択したUniverseは不完全" in item for item in warning_messages)
    assert any("未定義領域の検出を無効" in item for item in warning_messages)
    assert [item.value for item in app.subheader] == [
        "1. 入力元の選択",
        "2. 解析目的",
        "3. 検査を実行",
        "4. 集計",
        "5. 検出事項一覧",
        "6. 幾何形状プロット",
        "7. AIによる説明",
    ]
    metrics = {item.label: item.value for item in app.get("metric")}
    assert metrics["Surface"] == "3"
    assert metrics["エラー"] == "1"
    assert [(item.label, item.value) for item in app.multiselect] == [
        ("重大度", ["ERROR"]),
        ("ルールID", ["SG001"]),
    ]
    assert [item.label for item in app.expander] == [
        "根拠情報 1：SG001 — fuelsurf",
        "解析済みモデルJSON（デバッグ用）",
    ]


@pytest.mark.parametrize(
    ("arguments", "expected_text"),
    [
        (["--help"], "Local deterministic preflight checks"),
        (["check", "--help"], "deterministic symbol-table checks"),
    ],
)
def test_cli_help(arguments: list[str], expected_text: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "serpentguard.cli", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    normalized_stdout = " ".join(completed.stdout.split())
    assert expected_text in normalized_stdout
    assert completed.stderr == ""
