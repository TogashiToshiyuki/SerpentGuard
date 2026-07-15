"""Analytically simple tests for the deliberately limited geometry sampler."""

from __future__ import annotations

import numpy as np
import pytest
from matplotlib.font_manager import FontProperties

from serpentguard.geometry import (
    GeometryConfigError,
    GeometrySamplingConfig,
    GeometryUniverseError,
    GeometryWorkloadError,
    PointClassification,
    available_universes,
    default_target_universe,
    sample_geometry,
)
from serpentguard.geometry_plot import (
    PlotFontSelection,
    close_figure,
    create_diagnostic_figure,
    create_geometry_view_figure,
    select_plot_font,
)
from serpentguard.parser import parse_text


def _sample(
    text: str,
    *,
    bounds: tuple[float, float, float, float] = (-1.4, 1.4, -1.4, 1.4),
    resolution: int = 25,
    tolerance: float = 1.0e-9,
    target_universe: str = "0",
    z: float = 0.0,
    max_workload: int = 50_000_000,
):
    xmin, xmax, ymin, ymax = bounds
    model = parse_text(text, file_name="geometry.inp")
    config = GeometrySamplingConfig(
        xmin=xmin,
        xmax=xmax,
        ymin=ymin,
        ymax=ymax,
        z=z,
        resolution=resolution,
        target_universe=target_universe,
        boundary_tolerance=tolerance,
        max_workload=max_workload,
    )
    return sample_geometry(model, config)


def test_non_overlapping_concentric_regions_partition_the_slice() -> None:
    result = _sample(
        """\
surf inner cyl 0 0 0.5
surf outer sqc 0 0 1.0
cell core 0 void -inner
cell shell 0 void inner -outer
cell exterior 0 outside outer
""",
        resolution=24,
    )

    assert result.selected_universe == "0"
    assert result.coverage_complete
    assert result.undefined_detection_enabled
    assert result.supported_cell_count == 3
    assert result.excluded_cell_count == 0
    assert result.included_cells == ("core", "shell", "exterior")
    assert not result.excluded_cells
    assert result.overlap_count == 0
    assert result.undefined_count == 0
    assert result.indeterminate_count == 0
    assert result.normal_count == result.total_points


def test_deliberate_overlap_reports_coordinates_and_involved_cells() -> None:
    result = _sample(
        """\
surf left cyl -0.35 0 0.8
surf right cyl 0.35 0 0.8
cell left_cell 0 void -left
cell right_cell 0 void -right
""",
        resolution=31,
    )

    assert result.overlap_count > 0
    representative = result.overlap_representatives[0]
    assert set(representative.involved_cells) == {"left_cell", "right_cell"}
    assert result.classifications.shape == (31, 31)


def test_complete_supported_geometry_detects_deliberate_gap() -> None:
    result = _sample(
        """\
surf inner cyl 0 0 0.55
surf outer cyl 0 0 0.85
cell inside 0 void -inner
cell outside 0 outside outer
""",
        resolution=30,
    )

    assert result.coverage_complete
    assert result.undefined_detection_enabled
    assert result.undefined_count > 0
    assert result.undefined_representatives
    assert result.undefined_representatives[0].involved_cells == ()


def test_cell_with_unsupported_surface_is_excluded_not_guessed() -> None:
    result = _sample(
        """\
surf plane px 0 0 0
cell unsupported 0 void -plane
""",
        resolution=10,
    )

    assert result.included_cells == ()
    assert not result.coverage_complete
    assert not result.undefined_detection_enabled
    assert result.supported_cell_count == 0
    assert result.excluded_cell_count == 1
    exclusion = result.excluded_cells[0]
    assert exclusion.name == "unsupported"
    assert exclusion.universe == "0"
    assert exclusion.reasons[0].code == "unsupported_surface_type"
    assert exclusion.reasons[0].surface_name == "plane"
    assert result.indeterminate_count == result.total_points
    assert result.incomplete_domain_count == result.total_points
    assert result.undefined_count == 0


def test_mixed_unsupported_cell_cannot_create_false_undefined_candidates() -> None:
    result = _sample(
        """\
surf supported cyl 0 0 0.5
surf plane px 0 0 0
cell supported_cell 0 void -supported
cell unsupported_cell 0 void -plane
""",
        resolution=20,
    )

    assert result.supported_cell_count == 1
    assert result.excluded_cell_count == 1
    assert not result.coverage_complete
    assert not result.undefined_detection_enabled
    assert result.normal_count == 0
    assert result.incomplete_count == result.total_points
    assert result.undefined_count == 0
    assert result.incomplete_domain_count > 0
    assert result.indeterminate_count >= result.incomplete_domain_count


def test_cells_in_different_universes_are_sampled_independently() -> None:
    text = """\
surf circle cyl 0 0 1
cell local_zero 0 void -circle
cell local_one 1 void -circle
"""

    universe_zero = _sample(text, target_universe="0", resolution=15)
    universe_one = _sample(text, target_universe="1", resolution=15)

    assert universe_zero.included_cells == ("local_zero",)
    assert universe_one.included_cells == ("local_one",)
    assert universe_zero.overlap_count == 0
    assert universe_one.overlap_count == 0
    assert np.array_equal(
        universe_zero.classifications,
        universe_one.classifications,
    )


def test_universe_zero_is_preferred_then_first_choice_is_deterministic() -> None:
    with_zero = parse_text(
        """\
surf circle cyl 0 0 1
cell second 2 void -circle
cell zero 0 void -circle
"""
    )
    without_zero = parse_text(
        """\
surf circle cyl 0 0 1
cell zebra z void -circle
cell alpha a void -circle
"""
    )

    assert available_universes(with_zero) == ("0", "2")
    assert default_target_universe(with_zero) == "0"
    assert available_universes(without_zero) == ("a", "z")
    assert default_target_universe(without_zero) == "a"


def test_duplicate_cell_definitions_in_selected_universe_are_excluded() -> None:
    result = _sample(
        """\
surf circle cyl 0 0 1
cell duplicate 0 void -circle
cell duplicate 0 void -circle
""",
        resolution=12,
    )

    assert result.included_cells == ()
    assert result.supported_cell_count == 0
    assert result.excluded_cell_count == 2
    assert not result.coverage_complete
    assert result.overlap_count == 0
    assert all(
        exclusion.reasons[0].code == "duplicate_cell_name"
        and exclusion.reasons[0].duplicate_count == 2
        for exclusion in result.excluded_cells
    )


def test_duplicate_cell_names_in_other_universes_are_not_local_duplicates() -> None:
    text = """\
surf circle cyl 0 0 1
cell repeated 0 void -circle
cell repeated 1 void -circle
"""

    universe_zero = _sample(text, target_universe="0", resolution=12)
    universe_one = _sample(text, target_universe="1", resolution=12)

    assert universe_zero.included_cells == ("repeated",)
    assert universe_one.included_cells == ("repeated",)
    assert universe_zero.coverage_complete
    assert universe_one.coverage_complete
    assert not universe_zero.excluded_cells
    assert not universe_one.excluded_cells


def test_current_surface_subset_is_invariant_in_z() -> None:
    text = """\
surf circle cyl 0 0 0.5
surf square sqc 0 0 1
cell inside 0 void -circle
cell shell 0 void circle -square
cell outside 0 outside square
"""
    lower = _sample(text, z=-100.0, resolution=18)
    upper = _sample(text, z=100.0, resolution=18)

    assert lower.config.z == -100.0
    assert upper.config.z == 100.0
    assert np.array_equal(lower.classifications, upper.classifications)
    assert np.array_equal(lower.match_counts, upper.match_counts)


def test_invalid_target_universe_is_rejected() -> None:
    model = parse_text(
        "surf circle cyl 0 0 1\ncell inside 0 void -circle\n",
        file_name="geometry.inp",
    )
    config = GeometrySamplingConfig(
        xmin=-1.0,
        xmax=1.0,
        ymin=-1.0,
        ymax=1.0,
        z=0.0,
        resolution=10,
        target_universe="missing",
    )

    with pytest.raises(GeometryUniverseError, match="target universe") as captured:
        sample_geometry(model, config)

    assert captured.value.available_universes == ("0",)


def test_workload_limit_is_enforced_before_sampling() -> None:
    with pytest.raises(GeometryWorkloadError) as captured:
        _sample(
            "surf circle cyl 0 0 1\ncell inside 0 void -circle\n",
            resolution=10,
            max_workload=199,
        )

    assert captured.value.estimate.grid_point_count == 100
    assert captured.value.estimate.evaluated_cell_count == 1
    assert captured.value.estimate.signed_reference_count == 1
    assert captured.value.estimate.estimated_operations == 200
    assert captured.value.limit == 199


def test_boundary_tolerance_controls_indeterminate_band() -> None:
    text = "surf circle cyl 0 0 1\ncell inside 0 void -circle\n"
    narrow = _sample(
        text,
        bounds=(0.999, 1.001, -0.001, 0.001),
        resolution=5,
        tolerance=1.0e-8,
    )
    wide = _sample(
        text,
        bounds=(0.999, 1.001, -0.001, 0.001),
        resolution=5,
        tolerance=0.0011,
    )

    assert narrow.indeterminate_count < wide.indeterminate_count
    assert wide.indeterminate_count == wide.total_points
    assert PointClassification.BOUNDARY in wide.classifications
    assert wide.boundary_indeterminate_count == wide.total_points


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"xmax": -1.0}, "xmax"),
        ({"ymax": -1.0}, "ymax"),
        ({"resolution": 1}, "resolution"),
        ({"resolution": 501}, "resolution"),
        ({"target_universe": ""}, "target_universe"),
        ({"boundary_tolerance": -1.0}, "boundary_tolerance"),
        ({"max_workload": 0}, "max_workload"),
    ],
)
def test_sampling_configuration_rejects_invalid_values(
    overrides: dict[str, float | int | str], message: str
) -> None:
    values: dict[str, float | int | str] = {
        "xmin": -1.0,
        "xmax": 1.0,
        "ymin": -1.0,
        "ymax": 1.0,
        "z": 0.0,
        "resolution": 10,
        "target_universe": "0",
    }
    values.update(overrides)

    with pytest.raises(GeometryConfigError, match=message):
        GeometrySamplingConfig(**values)  # type: ignore[arg-type]


def test_diagnostic_plot_uses_categorical_legend_without_colorbar() -> None:
    result = _sample(
        "surf circle cyl 0 0 1\ncell inside 0 void -circle\n",
        resolution=10,
    )
    labels = {
        PointClassification.UNDEFINED: "Undefined",
        PointClassification.NORMAL: "Normal",
        PointClassification.OVERLAP: "Overlap",
        PointClassification.INCOMPLETE: "Incomplete",
        PointClassification.BOUNDARY: "Boundary",
    }

    figure = create_diagnostic_figure(
        result,
        title="XY sample",
        classification_labels=labels,
    )

    assert figure.axes[0].get_title() == "XY sample"
    assert len(figure.axes) == 1
    assert figure.axes[0].get_aspect() == 1.0
    assert [text.get_text() for text in figure.axes[0].get_legend().get_texts()] == [
        labels[item] for item in PointClassification
    ]
    close_figure(figure)


def test_pwr_categories_keep_geometry_separate_from_diagnostics() -> None:
    result = _sample(
        """\
surf fuel_boundary cyl 0 0 0.40
surf clad_boundary cyl 0 0 0.46
surf pin_boundary sqc 0 0 0.65
cell fuel_cell 0 fuel -fuel_boundary
cell clad_cell 0 clad fuel_boundary -clad_boundary
cell coolant_cell 0 coolant clad_boundary -pin_boundary
cell exterior_cell 0 outside pin_boundary
mat fuel -10.0 rgb 220 55 35
92235.09c -1.0
mat clad -6.5 rgb 150 155 165
40000.09c -1.0
mat coolant -0.7 rgb 55 135 220
1001.09c -2.0
""",
        bounds=(-0.75, 0.75, -0.75, 0.75),
        resolution=151,
    )
    material_labels = {
        item.label: index for index, item in enumerate(result.material_categories)
    }
    cell_labels = {
        item.label: index for index, item in enumerate(result.cell_categories)
    }
    center = 75
    annulus = 75 + 43
    outer = 75 + 55

    assert {"fuel", "clad", "coolant"} <= set(material_labels)
    assert result.material_category_grid[center, center] == material_labels["fuel"]
    assert result.material_category_grid[center, annulus] == material_labels["clad"]
    assert result.material_category_grid[center, outer] == material_labels["coolant"]
    assert result.cell_category_grid[center, center] == cell_labels["fuel_cell"]
    assert [item.key for item in result.cell_categories] != [
        item.key for item in result.material_categories
    ]
    assert result.normal_count > 0
    assert not np.array_equal(
        result.material_category_grid,
        result.classifications.astype(np.int32),
    )


def test_geometry_plot_has_discrete_legend_deterministic_colors_and_equal_aspect() -> (
    None
):
    result = _sample(
        """\
surf inner cyl 0 0 0.5
surf outer sqc 0 0 1.0
cell fuel_cell 0 fuel -inner
cell water_cell 0 water inner -outer
cell outside_cell 0 outside outer
mat fuel -10
92235.09c -1
mat water -1
1001.09c -2
""",
        resolution=30,
    )
    labels = {
        "outside": "Outside",
        "void": "Void",
        "unsupported": "Unsupported",
        "indeterminate": "Indeterminate",
        "undefined": "Undefined",
    }
    first = create_geometry_view_figure(
        result,
        color_by="material",
        title="Geometry view",
        special_labels=labels,
    )
    second = create_geometry_view_figure(
        result,
        color_by="material",
        title="Geometry view",
        special_labels=labels,
    )
    first_colors = [
        patch.get_facecolor() for patch in first.axes[0].get_legend().get_patches()
    ]
    second_colors = [
        patch.get_facecolor() for patch in second.axes[0].get_legend().get_patches()
    ]
    assert first_colors == second_colors
    assert len(first.axes) == 1
    assert first.axes[0].get_aspect() == 1.0
    assert first.axes[0].images[0].get_interpolation() == "nearest"
    close_figure(first)
    close_figure(second)


def test_cell_and_material_category_maps_diverge_when_cells_share_material() -> None:
    result = _sample(
        """\
surf fuel_edge cyl 0 0 0.3
surf split_edge cyl 0 0 0.6
surf outer_edge sqc 0 0 1.0
cell fuel_cell 0 fuel -fuel_edge
cell inner_water 0 water fuel_edge -split_edge
cell outer_water 0 water split_edge -outer_edge
cell exterior 0 outside outer_edge
mat fuel -10
92235.09c -1
mat water -1
1001.09c -2
""",
        resolution=40,
    )
    assert len(result.cell_categories) == 4
    assert len(result.material_categories) == 3
    assert not np.array_equal(result.cell_category_grid, result.material_category_grid)


def test_incomplete_area_is_not_given_a_normal_geometry_category() -> None:
    result = _sample(
        """\
surf circle cyl 0 0 0.5
surf plane px 0 0 0
cell known 0 fuel -circle
cell unknown 0 void -plane
mat fuel -10
92235.09c -1
""",
        resolution=12,
    )
    assert set(np.unique(result.material_category_grid)) == {0}
    assert result.material_categories[0].kind == "unsupported"


def test_japanese_font_selection_prefers_supported_installed_candidate() -> None:
    selected = select_plot_font(
        "ja",
        available_fonts={"Yu Gothic": "synthetic-yu.ttf", "Meiryo": "synthetic.ttf"},
        glyph_checker=lambda path: path == "synthetic-yu.ttf",
    )
    assert selected.family == "Yu Gothic"
    assert selected.supports_japanese


def test_missing_japanese_font_is_controlled_and_english_needs_no_japanese_font() -> (
    None
):
    missing = select_plot_font("ja", available_fonts={}, glyph_checker=lambda _: False)
    english = select_plot_font("en", available_fonts={})
    assert not missing.supports_japanese
    assert missing.warning
    assert english.supports_japanese
    assert english.warning is None


def test_japanese_plot_labels_are_preserved_and_figure_is_released() -> None:
    result = _sample(
        "surf circle cyl 0 0 1\ncell fuel_cell 0 fuel -circle\n"
        "mat fuel -10\n92235.09c -1\n",
        resolution=10,
    )
    font = PlotFontSelection(
        FontProperties(family="DejaVu Sans"), "test-font", None, True
    )
    figure = create_geometry_view_figure(
        result,
        color_by="material",
        title="限定的な体系図",
        special_labels={
            "outside": "外部領域",
            "void": "Void",
            "unsupported": "未対応領域",
            "indeterminate": "判定不能",
            "undefined": "未定義領域",
        },
        font=font,
    )
    assert figure.axes[0].get_title() == "限定的な体系図"
    assert "fuel" in [
        text.get_text() for text in figure.axes[0].get_legend().get_texts()
    ]
    close_figure(figure)
    assert figure.axes == []
