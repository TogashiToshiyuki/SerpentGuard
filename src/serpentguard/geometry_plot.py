"""Discrete Matplotlib views for language-neutral geometry sampling results."""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

import numpy as np
from matplotlib import font_manager
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.ft2font import FT2Font
from matplotlib.patches import Patch

from serpentguard.geometry import (
    GeometryCategory,
    GeometryCategoryKind,
    GeometrySamplingResult,
    PointClassification,
)
from serpentguard.i18n import ENGLISH, JAPANESE, SupportedLanguage

GeometryColorMode = Literal["material", "cell"]

_APPLICATION_COLORS = (
    "#e24a33",  # warm red
    "#9296a0",  # cladding-like gray
    "#3e8ed0",  # coolant-like blue
    "#55a868",
    "#8172b3",
    "#ccb974",
    "#64b5cd",
    "#c44e52",
    "#937860",
    "#da8bc3",
)
_SPECIAL_COLORS: dict[GeometryCategoryKind, str] = {
    "outside": "#6b7280",
    "void": "#f8fafc",
    "unsupported": "#7c3aed",
    "indeterminate": "#f59e0b",
    "undefined": "#f2c14e",
    "cell": "#3e8ed0",
    "material": "#3e8ed0",
}
_DIAGNOSTIC_COLORS: dict[PointClassification, str] = {
    PointClassification.UNDEFINED: "#f2c14e",
    PointClassification.NORMAL: "#4c78a8",
    PointClassification.OVERLAP: "#e15759",
    PointClassification.INCOMPLETE: "#7c3aed",
    PointClassification.BOUNDARY: "#f59e0b",
}
_JAPANESE_GLYPH_SAMPLE = "体系図診断材料境界面幾何形状未対応判定不能"
_FONT_CANDIDATES = {
    "win32": ("Yu Gothic", "Yu Gothic UI", "Meiryo", "Noto Sans JP", "MS Gothic"),
    "darwin": (
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Noto Sans CJK JP",
        "Noto Sans JP",
    ),
    "linux": ("Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "TakaoGothic"),
}


@dataclass(frozen=True, slots=True)
class PlotFontSelection:
    """Runtime font decision and its controlled Japanese fallback status."""

    properties: FontProperties
    family: str
    path: str | None
    supports_japanese: bool
    warning: str | None = None


def select_plot_font(
    language: SupportedLanguage,
    *,
    available_fonts: Mapping[str, str] | None = None,
    glyph_checker: Callable[[str], bool] | None = None,
) -> PlotFontSelection:
    """Select a platform font and verify Japanese glyph coverage when required."""
    fonts = dict(available_fonts) if available_fonts is not None else None
    installed = (
        set(fonts)
        if fonts is not None
        else {item.name for item in font_manager.fontManager.ttflist}
    )

    def font_path(family: str) -> str | None:
        if fonts is not None:
            return fonts.get(family)
        return _normal_font_path(family) if family in installed else None

    checker = glyph_checker or _has_required_japanese_glyphs
    if language == ENGLISH:
        path = font_path("DejaVu Sans")
        properties = (
            FontProperties(fname=path) if path else FontProperties(family="DejaVu Sans")
        )
        return PlotFontSelection(properties, "DejaVu Sans", path, True)

    platform_key = "win32" if sys.platform.startswith("win") else sys.platform
    candidates = _FONT_CANDIDATES.get(platform_key, _FONT_CANDIDATES["linux"])
    for family in candidates:
        path = font_path(family)
        if path and checker(path):
            return PlotFontSelection(FontProperties(fname=path), family, path, True)

    fallback_path = font_path("DejaVu Sans")
    properties = (
        FontProperties(fname=fallback_path)
        if fallback_path
        else FontProperties(family="DejaVu Sans")
    )
    return PlotFontSelection(
        properties,
        "DejaVu Sans",
        fallback_path,
        False,
        "No installed Japanese-capable Matplotlib font passed glyph validation.",
    )


@cache
def _normal_font_path(family: str) -> str | None:
    """Resolve a regular face instead of an arbitrary bold/italic family member."""
    properties = FontProperties(family=family, style="normal", weight="normal")
    try:
        return font_manager.findfont(properties, fallback_to_default=False)
    except ValueError:
        return None


def _has_required_japanese_glyphs(path: str) -> bool:
    try:
        charmap = FT2Font(str(Path(path))).get_charmap()
    except (OSError, RuntimeError):
        return False
    return all(ord(character) in charmap for character in _JAPANESE_GLYPH_SAMPLE)


def create_geometry_view_figure(
    result: GeometrySamplingResult,
    *,
    color_by: GeometryColorMode,
    title: str,
    special_labels: Mapping[GeometryCategoryKind, str],
    use_serpent_rgb: bool = False,
    font: PlotFontSelection | None = None,
) -> Figure:
    """Render unique supported occupancy by material or cell with a compact legend."""
    if color_by == "material":
        category_grid = result.material_category_grid
        categories = result.material_categories
    elif color_by == "cell":
        category_grid = result.cell_category_grid
        categories = result.cell_categories
    else:
        raise ValueError("color_by must be 'material' or 'cell'")
    missing = {
        item.kind
        for item in categories
        if item.kind not in special_labels and item.kind not in {"cell", "material"}
    }
    if missing:
        raise ValueError(
            f"Missing special category labels: {', '.join(sorted(missing))}"
        )

    selected_font = font or select_plot_font(ENGLISH)
    colors = _geometry_colors(categories, use_serpent_rgb=use_serpent_rgb)
    figure, axis = _base_figure(result, title, selected_font)
    color_map = ListedColormap(colors or ["#ffffff"])
    norm = BoundaryNorm(np.arange(-0.5, len(colors) + 0.5), color_map.N)
    axis.imshow(
        category_grid,
        origin="lower",
        extent=_extent(result),
        interpolation="nearest",
        aspect="equal",
        cmap=color_map,
        norm=norm,
    )
    handles = [
        Patch(
            facecolor=colors[index],
            edgecolor="#374151",
            linewidth=0.7,
            label=_category_display_label(category, special_labels),
        )
        for index, category in enumerate(categories)
    ]
    if handles:
        legend = axis.legend(
            handles=handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
            ncol=min(3, len(handles)),
            frameon=True,
            fontsize=10,
        )
        for text in legend.get_texts():
            text.set_fontproperties(selected_font.properties)
    return figure


def _geometry_colors(
    categories: tuple[GeometryCategory, ...], *, use_serpent_rgb: bool
) -> list[str | tuple[float, float, float]]:
    colors: list[str | tuple[float, float, float]] = []
    application_index = 0
    for category in categories:
        if category.kind in {"cell", "material"}:
            if use_serpent_rgb and category.serpent_rgb is not None:
                colors.append(
                    tuple(channel / 255.0 for channel in category.serpent_rgb)
                )
            else:
                colors.append(
                    _APPLICATION_COLORS[application_index % len(_APPLICATION_COLORS)]
                )
                application_index += 1
        else:
            colors.append(_SPECIAL_COLORS[category.kind])
    return colors


def _category_display_label(
    category: GeometryCategory,
    special_labels: Mapping[GeometryCategoryKind, str],
) -> str:
    if category.kind in {"cell", "material"}:
        return category.label
    special = special_labels[category.kind]
    if category.key.startswith("cell:"):
        return f"{category.label} ({special})"
    return special


def create_diagnostic_figure(
    result: GeometrySamplingResult,
    *,
    title: str,
    classification_labels: Mapping[PointClassification, str],
    font: PlotFontSelection | None = None,
) -> Figure:
    """Render preflight classifications independently of geometry categories."""
    required = set(PointClassification)
    missing = required - set(classification_labels)
    if missing:
        raise ValueError(
            "Missing classification labels: "
            + ", ".join(item.name for item in sorted(missing))
        )
    selected_font = font or select_plot_font(ENGLISH)
    ordered = tuple(PointClassification)
    colors = [_DIAGNOSTIC_COLORS[item] for item in ordered]
    figure, axis = _base_figure(result, title, selected_font)
    color_map = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(-0.5, len(colors) + 0.5), color_map.N)
    axis.imshow(
        result.classifications,
        origin="lower",
        extent=_extent(result),
        interpolation="nearest",
        aspect="equal",
        cmap=color_map,
        norm=norm,
    )
    legend = axis.legend(
        handles=[
            Patch(
                facecolor=colors[index],
                edgecolor="#374151",
                label=classification_labels[classification],
            )
            for index, classification in enumerate(ordered)
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=min(3, len(ordered)),
        frameon=True,
        fontsize=10,
    )
    for text in legend.get_texts():
        text.set_fontproperties(selected_font.properties)
    return figure


def create_geometry_figure(
    result: GeometrySamplingResult,
    *,
    title: str,
    classification_labels: Mapping[PointClassification, str],
) -> Figure:
    """Backward-compatible name for the diagnostic classification view."""
    return create_diagnostic_figure(
        result, title=title, classification_labels=classification_labels
    )


def _base_figure(
    result: GeometrySamplingResult,
    title: str,
    font: PlotFontSelection,
) -> tuple[Figure, Axes]:
    figure = Figure(figsize=(8.0, 6.6), constrained_layout=True)
    axis = figure.subplots()
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlim(result.config.xmin, result.config.xmax)
    axis.set_ylim(result.config.ymin, result.config.ymax)
    axis.set_xlabel("x", fontproperties=font.properties, fontsize=11)
    axis.set_ylabel("y", fontproperties=font.properties, fontsize=11)
    axis.set_title(title, fontproperties=font.properties, fontsize=14)
    for label in (*axis.get_xticklabels(), *axis.get_yticklabels()):
        label.set_fontproperties(font.properties)
    return figure, axis


def _extent(result: GeometrySamplingResult) -> tuple[float, float, float, float]:
    return (
        result.config.xmin,
        result.config.xmax,
        result.config.ymin,
        result.config.ymax,
    )


def close_figure(figure: Figure) -> None:
    """Release a rendered figure after Streamlit has serialized it."""
    plt.close(figure)
    figure.clear()


def ui_font_properties() -> FontProperties:
    """Compatibility helper returning a verified Japanese-capable font when possible."""
    return select_plot_font(JAPANESE).properties
