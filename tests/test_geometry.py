"""Analytically simple tests for the deliberately limited geometry sampler."""

from __future__ import annotations

import pytest

from serpentguard.geometry import (
    GeometryConfigError,
    GeometrySamplingConfig,
    PointClassification,
    sample_geometry,
)
from serpentguard.geometry_plot import create_geometry_figure
from serpentguard.parser import parse_text


def _sample(
    text: str,
    *,
    bounds: tuple[float, float, float, float] = (-1.4, 1.4, -1.4, 1.4),
    resolution: int = 25,
    tolerance: float = 1.0e-9,
):
    xmin, xmax, ymin, ymax = bounds
    model = parse_text(text, file_name="geometry.inp")
    config = GeometrySamplingConfig(
        xmin=xmin,
        xmax=xmax,
        ymin=ymin,
        ymax=ymax,
        z=0.0,
        resolution=resolution,
        boundary_tolerance=tolerance,
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


def test_deliberate_gap_reports_undefined_candidates() -> None:
    result = _sample(
        """\
surf inner cyl 0 0 0.55
surf outer cyl 0 0 0.85
cell inside 0 void -inner
cell outside 0 outside outer
""",
        resolution=30,
    )

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
    assert len(result.excluded_cells) == 1
    exclusion = result.excluded_cells[0]
    assert exclusion.name == "unsupported"
    assert exclusion.reasons[0].code == "unsupported_surface_type"
    assert exclusion.reasons[0].surface_name == "plane"
    assert result.indeterminate_count == result.total_points
    assert result.undefined_count == 0


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
    assert PointClassification.INDETERMINATE in wide.classifications


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"xmax": -1.0}, "xmax"),
        ({"ymax": -1.0}, "ymax"),
        ({"resolution": 1}, "resolution"),
        ({"resolution": 501}, "resolution"),
        ({"boundary_tolerance": -1.0}, "boundary_tolerance"),
    ],
)
def test_sampling_configuration_rejects_invalid_values(
    overrides: dict[str, float | int], message: str
) -> None:
    values: dict[str, float | int] = {
        "xmin": -1.0,
        "xmax": 1.0,
        "ymin": -1.0,
        "ymax": 1.0,
        "z": 0.0,
        "resolution": 10,
    }
    values.update(overrides)

    with pytest.raises(GeometryConfigError, match=message):
        GeometrySamplingConfig(**values)  # type: ignore[arg-type]


def test_plot_uses_supplied_classification_labels() -> None:
    result = _sample(
        "surf circle cyl 0 0 1\ncell inside 0 void -circle\n",
        resolution=10,
    )
    labels = {
        PointClassification.UNDEFINED: "Undefined",
        PointClassification.NORMAL: "Normal",
        PointClassification.OVERLAP: "Overlap",
        PointClassification.INDETERMINATE: "Indeterminate",
    }

    figure = create_geometry_figure(
        result,
        title="XY sample",
        classification_labels=labels,
    )

    assert figure.axes[0].get_title() == "XY sample"
    assert [tick.get_text() for tick in figure.axes[1].get_yticklabels()] == list(
        labels.values()
    )
    figure.clear()
