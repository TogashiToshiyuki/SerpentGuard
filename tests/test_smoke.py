"""Foundation smoke tests."""

from __future__ import annotations

import subprocess
import sys

import pytest
from streamlit.testing.v1 import AppTest

from serpentguard import __version__


def test_package_imports() -> None:
    assert __version__ == "0.1.0"


def test_streamlit_foundation_page() -> None:
    app = AppTest.from_file("app.py").run()

    assert not app.exception
    assert [title.value for title in app.title] == ["SerpentGuard"]
    assert len(app.warning) == 1
    assert "no checks are implemented yet" in app.warning[0].value
    assert [
        (uploader.label, uploader.disabled) for uploader in app.get("file_uploader")
    ] == [("Serpent input file", True)]
    assert [(button.label, button.disabled) for button in app.button] == [
        ("Run check", True)
    ]


@pytest.mark.parametrize(
    ("arguments", "expected_text"),
    [
        (["--help"], "Local deterministic preflight checks"),
        (["check", "--help"], "No Serpent input is processed"),
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
