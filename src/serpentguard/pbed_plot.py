"""PBED placement slice mathematics and Matplotlib rendering."""

from __future__ import annotations

import math
from typing import Literal

from matplotlib.collections import PatchCollection
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Patch
from pydantic import BaseModel, ConfigDict, Field

from serpentguard.geometry_plot import PlotFontSelection, select_plot_font
from serpentguard.i18n import ENGLISH
from serpentguard.pbed import PbedData


class PbedSliceCircle(BaseModel):
    """Exact intersection of one verified placement sphere with an XY plane."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float
    y: float
    radius: float = Field(ge=0.0)
    universe: str
    record_number: int = Field(ge=1)


class PbedSliceResult(BaseModel):
    """Language-neutral placement cross-section summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    z: float
    mode: Literal["slice", "projection"] = "slice"
    total_placement_count: int = Field(ge=0)
    intersecting_placement_count: int = Field(ge=0)
    circles: tuple[PbedSliceCircle, ...] = ()


def slice_pbed_placements(data: PbedData, *, z: float) -> PbedSliceResult:
    """Intersect verified placement spheres with the requested XY plane."""
    if not math.isfinite(z):
        raise ValueError("PBED slice z must be finite")

    circles: list[PbedSliceCircle] = []
    for placement in data.placements:
        delta_z = z - placement.z
        radial_square = placement.radius**2 - delta_z**2
        if radial_square < 0.0:
            continue
        circles.append(
            PbedSliceCircle(
                x=placement.x,
                y=placement.y,
                radius=math.sqrt(max(0.0, radial_square)),
                universe=placement.universe,
                record_number=placement.record_number,
            )
        )

    return PbedSliceResult(
        z=z,
        total_placement_count=data.valid_record_count,
        intersecting_placement_count=len(circles),
        circles=tuple(circles),
    )


def project_pbed_centers(data: PbedData) -> PbedSliceResult:
    """Project verified sphere centers to XY using their full documented radii."""
    return PbedSliceResult(
        z=0.0,
        mode="projection",
        total_placement_count=data.valid_record_count,
        intersecting_placement_count=data.valid_record_count,
        circles=tuple(
            PbedSliceCircle(
                x=placement.x,
                y=placement.y,
                radius=placement.radius,
                universe=placement.universe,
                record_number=placement.record_number,
            )
            for placement in data.placements
        ),
    )


def create_pbed_slice_figure(
    result: PbedSliceResult,
    *,
    title: str,
    font: PlotFontSelection | None = None,
    universe_label: str = "Universe",
) -> Figure:
    """Render placement cross-sections without claiming overlap validity."""
    figure = Figure(figsize=(7.5, 6.0), constrained_layout=True)
    axis = figure.subplots()
    selected_font = font or select_plot_font(ENGLISH)
    universes = tuple(sorted({item.universe for item in result.circles}))
    palette = ("#3e8ed0", "#e24a33", "#55a868", "#8172b3", "#ccb974")
    legend_handles: list[Patch] = []
    for universe_index, universe in enumerate(universes):
        color = palette[universe_index % len(palette)]
        patches = [
            Circle((item.x, item.y), item.radius)
            for item in result.circles
            if item.universe == universe
        ]
        collection = PatchCollection(
            patches,
            facecolor=color,
            edgecolor="#1f2937",
            linewidth=0.5,
            alpha=0.45,
        )
        axis.add_collection(collection)
        legend_handles.append(
            Patch(
                facecolor=color,
                edgecolor="#374151",
                label=f"{universe_label} {universe}",
            )
        )
    if result.circles:
        axis.autoscale_view()
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("x [cm]")
    axis.set_ylabel("y [cm]")
    axis.set_title(title, fontproperties=selected_font.properties)
    if legend_handles:
        legend = axis.legend(handles=legend_handles, loc="best", frameon=True)
        for text in legend.get_texts():
            text.set_fontproperties(selected_font.properties)
    return figure
