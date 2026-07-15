"""Offline unit tests for the first deterministic parser milestone."""

from pathlib import Path

import pytest

from serpentguard.cli import main
from serpentguard.parser import parse_bytes, parse_file, parse_text

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_valid_minimal_fixture() -> None:
    result = parse_file(EXAMPLES / "valid_minimal.inp")

    assert len(result.surfaces) == 2
    assert len(result.cells) == 3
    assert len(result.materials) == 2
    assert result.unknown_cards == []
    assert result.diagnostics == []
    assert result.cells[1].signed_surface_references == ["fuelsurf", "-outersurf"]
    assert result.cells[1].referenced_surfaces == ["fuelsurf", "outersurf"]


@pytest.mark.parametrize(
    ("fixture_name", "surface_count"),
    [
        ("duplicate_surface.inp", 3),
        ("undefined_surface.inp", 1),
        ("contradictory_cell.inp", 2),
    ],
)
def test_semantic_fixtures_parse_without_running_semantic_rules(
    fixture_name: str,
    surface_count: int,
) -> None:
    result = parse_file(EXAMPLES / fixture_name)

    assert len(result.surfaces) == surface_count
    assert len(result.cells) == 2
    assert len(result.materials) == 1
    assert result.diagnostics == []


def test_comments_do_not_create_cards_or_change_locations() -> None:
    result = parse_text(
        "% surf fake cyl 0 0 1\n"
        "/* mat fake -1\n"
        "1001.09c -1 */\n"
        "surf real cyl 0 0 1 % cell fake 0 void -real\n"
        "cell actual 0 void -real\n",
        file_name="comments.inp",
    )

    assert [surface.name for surface in result.surfaces] == ["real"]
    assert [cell.name for cell in result.cells] == ["actual"]
    assert result.surfaces[0].location.line_start == 4
    assert result.cells[0].location.line_start == 5


def test_malformed_numeric_surface_is_retained_and_diagnosed() -> None:
    result = parse_text("surf bad cyl zero 0 1\n", file_name="numeric.inp")

    assert result.surfaces == []
    assert [card.keyword for card in result.unknown_cards] == ["surf"]
    assert result.diagnostics[0].code == "PARSER001"
    assert result.diagnostics[0].severity == "ERROR"
    assert result.diagnostics[0].location.line_start == 1


def test_malformed_material_fraction_reports_component_line() -> None:
    result = parse_text(
        "mat fuel -1\n1001.09c not-a-number\n",
        file_name="material.inp",
    )

    assert result.materials == []
    assert [card.keyword for card in result.unknown_cards] == ["mat"]
    assert result.diagnostics[0].code == "PARSER003"
    assert result.diagnostics[0].location.line_start == 2
    assert "not-a-number" not in result.diagnostics[0].message


def test_unknown_card_is_retained_with_info_diagnostic() -> None:
    result = parse_file(EXAMPLES / "unknown_card.inp")

    assert [card.keyword for card in result.unknown_cards] == ["set"]
    assert result.unknown_cards[0].tokens == ["set", "bc", "2"]
    assert result.unknown_cards[0].location.line_start == 15
    assert result.diagnostics[0].code == "SG014"
    assert result.diagnostics[0].severity == "INFO"


def test_source_locations_cover_single_and_multiline_cards() -> None:
    result = parse_file(EXAMPLES / "valid_minimal.inp")

    assert result.surfaces[0].location.line_start == 8
    assert result.surfaces[0].location.line_end == 8
    assert result.cells[0].location.line_start == 11
    assert result.materials[0].location.line_start == 15
    assert result.materials[0].location.line_end == 18
    assert result.materials[0].location.file_name.endswith("valid_minimal.inp")


def test_keywords_inside_other_cards_and_comments_are_not_definitions() -> None:
    result = parse_text(
        "set title surf fake cell fake mat fake\n"
        "% surf commented cyl 0 0 1\n"
        "mat real -1\n"
        "1001.09c -1\n",
        file_name="boundaries.inp",
    )

    assert result.surfaces == []
    assert result.cells == []
    assert [material.name for material in result.materials] == ["real"]
    assert [card.keyword for card in result.unknown_cards] == ["set"]


def test_include_is_not_opened() -> None:
    result = parse_text('include "missing.inp"\n', file_name="main.inp")

    assert result.source_files == ["main.inp"]
    assert [card.keyword for card in result.unknown_cards] == ["include"]
    assert result.diagnostics[0].code == "SG014"
    assert "not opened" in result.diagnostics[0].message


def test_uploaded_bytes_are_decoded_as_utf8() -> None:
    valid = parse_bytes(b"surf s cyl 0 0 1\n", file_name="upload.inp")
    invalid = parse_bytes(b"\xff\xfe", file_name="invalid.inp")

    assert [surface.name for surface in valid.surfaces] == ["s"]
    assert valid.source_files == ["upload.inp"]
    assert invalid.surfaces == []
    assert invalid.diagnostics[0].code == "PARSER_ENCODING"
    assert invalid.diagnostics[0].location.file_name == "invalid.inp"


def test_cli_check_prints_counts_without_raw_input(
    capsys: pytest.CaptureFixture[str],
) -> None:
    return_code = main(["check", str(EXAMPLES / "valid_minimal.inp")])

    output = capsys.readouterr().out
    assert return_code == 0
    assert "Surfaces: 2" in output
    assert "Cells: 3" in output
    assert "Materials: 2" in output
    assert "Unknown cards: 0" in output
    assert "92235.09c" not in output


def test_exact_documented_material_rgb_triplet_is_retained() -> None:
    model = parse_text(
        "mat fuel -10.0 rgb 220 55 35\n92235.09c -1.0\n",
        file_name="rgb.inp",
    )
    assert model.materials[0].rgb == (220, 55, 35)
    assert not model.diagnostics


@pytest.mark.parametrize("rgb", ["1.0 2 3", "256 2 3", "1 2"])
def test_invalid_or_incomplete_material_rgb_is_not_fabricated(rgb: str) -> None:
    model = parse_text(
        f"mat fuel -10.0 rgb {rgb}\n92235.09c -1.0\n",
        file_name="rgb.inp",
    )
    assert not model.materials
    assert model.unknown_cards
