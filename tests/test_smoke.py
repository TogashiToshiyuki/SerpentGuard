"""Foundation smoke tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from serpentguard import __version__


def test_package_imports() -> None:
    assert __version__ == "0.1.0"


def test_streamlit_page_waits_for_explicit_run() -> None:
    app = AppTest.from_file("app.py").run()

    assert not app.exception
    assert [title.value for title in app.title] == ["SerpentGuard"]
    assert len(app.warning) == 1
    assert "limited syntax subset" in app.warning[0].value
    assert [item.value for item in app.subheader] == [
        "1. Upload Serpent input",
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
    assert "Geometry checking is not implemented in this milestone." in info_messages
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
