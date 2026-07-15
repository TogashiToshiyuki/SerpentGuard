"""Matplotlib rendering for language-neutral geometry sampling results."""

from __future__ import annotations

from collections.abc import Mapping

from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.figure import Figure

from serpentguard.geometry import GeometrySamplingResult, PointClassification

_CLASSIFICATION_COLORS = (
    "#f2c14e",  # undefined
    "#59a14f",  # normal
    "#e15759",  # overlap
    "#9d9da1",  # indeterminate
)


def create_geometry_figure(
    result: GeometrySamplingResult,
    *,
    title: str,
    classification_labels: Mapping[PointClassification, str],
) -> Figure:
    """Create a 2D classification plot without depending on Streamlit."""
    required = set(PointClassification)
    missing = required - set(classification_labels)
    if missing:
        missing_names = ", ".join(item.name for item in sorted(missing))
        raise ValueError(f"Missing classification labels: {missing_names}")

    figure = Figure(figsize=(7.5, 6.0), constrained_layout=True)
    axis = figure.subplots()
    color_map = ListedColormap(_CLASSIFICATION_COLORS)
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], color_map.N)
    image = axis.imshow(
        result.classifications,
        origin="lower",
        extent=(
            result.config.xmin,
            result.config.xmax,
            result.config.ymin,
            result.config.ymax,
        ),
        interpolation="nearest",
        aspect="equal",
        cmap=color_map,
        norm=norm,
    )
    axis.set_xlabel("x")
    axis.set_ylabel("y")
    axis.set_title(title)
    colorbar = figure.colorbar(
        image,
        ax=axis,
        ticks=[classification.value for classification in PointClassification],
        shrink=0.85,
    )
    colorbar.ax.set_yticklabels(
        [classification_labels[item] for item in PointClassification]
    )
    return figure
