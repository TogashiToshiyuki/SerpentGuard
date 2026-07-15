"""Deliberately limited, deterministic XY geometry sampling.

This module is independent of Streamlit and intentionally supports only the
surface subset documented by SerpentGuard.  It is a sampling aid, not a full
Serpent CSG implementation or a replacement for Serpent's geometry plotter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from math import isfinite
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from serpentguard.models import Cell, ParsedModel, SourceLocation, Surface

SUPPORTED_GEOMETRY_SURFACE_TYPES = frozenset({"cyl", "sqc"})
DEFAULT_BOUNDARY_TOLERANCE = 1.0e-9
DEFAULT_GRID_RESOLUTION = 100
MIN_GRID_RESOLUTION = 2
MAX_GRID_RESOLUTION = 500
DEFAULT_MAX_REPRESENTATIVE_POINTS = 10

GeometryExclusionCode = Literal[
    "unsupported_surface_type",
    "undefined_surface",
    "ambiguous_surface",
    "invalid_surface_parameters",
    "unsupported_cell_syntax",
    "empty_region",
]


class GeometryConfigError(ValueError):
    """Raised when a requested sampling configuration is invalid."""


class PointClassification(IntEnum):
    """Classification assigned to one XY grid point."""

    UNDEFINED = 0
    NORMAL = 1
    OVERLAP = 2
    INDETERMINATE = 3


@dataclass(frozen=True, slots=True)
class GeometrySamplingConfig:
    """Validated user-confirmed XY slice and grid configuration."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float
    z: float
    resolution: int
    boundary_tolerance: float = DEFAULT_BOUNDARY_TOLERANCE
    max_representative_points: int = DEFAULT_MAX_REPRESENTATIVE_POINTS

    def __post_init__(self) -> None:
        values = {
            "xmin": self.xmin,
            "xmax": self.xmax,
            "ymin": self.ymin,
            "ymax": self.ymax,
            "z": self.z,
            "boundary_tolerance": self.boundary_tolerance,
        }
        for name, value in values.items():
            if not isfinite(value):
                raise GeometryConfigError(f"{name} must be finite")
        if self.xmax <= self.xmin:
            raise GeometryConfigError("xmax must be greater than xmin")
        if self.ymax <= self.ymin:
            raise GeometryConfigError("ymax must be greater than ymin")
        if isinstance(self.resolution, bool) or not isinstance(self.resolution, int):
            raise GeometryConfigError("resolution must be an integer")
        if not MIN_GRID_RESOLUTION <= self.resolution <= MAX_GRID_RESOLUTION:
            raise GeometryConfigError(
                f"resolution must be between {MIN_GRID_RESOLUTION} and "
                f"{MAX_GRID_RESOLUTION}"
            )
        if self.boundary_tolerance < 0.0:
            raise GeometryConfigError("boundary_tolerance must not be negative")
        if (
            isinstance(self.max_representative_points, bool)
            or not isinstance(self.max_representative_points, int)
            or self.max_representative_points < 1
        ):
            raise GeometryConfigError(
                "max_representative_points must be a positive integer"
            )


@dataclass(frozen=True, slots=True)
class GeometryExclusion:
    """One structured reason why a cell was not evaluated."""

    code: GeometryExclusionCode
    surface_name: str | None = None
    surface_type: str | None = None


@dataclass(frozen=True, slots=True)
class ExcludedCell:
    """A parsed or retained cell excluded from geometry sampling."""

    name: str
    location: SourceLocation
    reasons: tuple[GeometryExclusion, ...]


@dataclass(frozen=True, slots=True)
class RepresentativePoint:
    """One deterministic representative point for a classification."""

    x: float
    y: float
    involved_cells: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeometrySamplingResult:
    """Complete language-neutral output from the limited geometry sampler."""

    config: GeometrySamplingConfig
    x_coordinates: NDArray[np.float64]
    y_coordinates: NDArray[np.float64]
    classifications: NDArray[np.uint8]
    match_counts: NDArray[np.int64]
    included_cells: tuple[str, ...]
    excluded_cells: tuple[ExcludedCell, ...]
    overlap_count: int
    undefined_count: int
    normal_count: int
    indeterminate_count: int
    overlap_representatives: tuple[RepresentativePoint, ...]
    undefined_representatives: tuple[RepresentativePoint, ...]
    indeterminate_representatives: tuple[RepresentativePoint, ...]

    @property
    def total_points(self) -> int:
        """Return the total number of requested grid points."""
        return self.config.resolution**2

    @property
    def evaluated_points(self) -> int:
        """Return the number of points assigned a determinate classification."""
        return self.total_points - self.indeterminate_count


@dataclass(frozen=True, slots=True)
class _PreparedCell:
    cell: Cell
    terms: tuple[tuple[str, ...], ...]


def sample_geometry(
    model: ParsedModel,
    config: GeometrySamplingConfig,
) -> GeometrySamplingResult:
    """Sample supported cells over a user-confirmed, inclusive XY grid.

    Boundary points are indeterminate.  A cell is evaluated only when every
    referenced surface has one unambiguous, valid supported definition.
    """
    x_coordinates = np.linspace(
        config.xmin, config.xmax, config.resolution, dtype=np.float64
    )
    y_coordinates = np.linspace(
        config.ymin, config.ymax, config.resolution, dtype=np.float64
    )
    x_grid, y_grid = np.meshgrid(x_coordinates, y_coordinates)

    surface_groups = _group_surfaces(model)
    retained_surfaces = _retained_surface_cards(model)
    prepared_cells, excluded_cells = _prepare_cells(
        model, surface_groups, retained_surfaces
    )

    surface_values: dict[str, NDArray[np.float64]] = {}
    for prepared in prepared_cells:
        for signed_reference in prepared.cell.signed_surface_references:
            surface_name = _unsigned_reference(signed_reference)
            if surface_name not in surface_values:
                surface_values[surface_name] = _signed_distance(
                    surface_groups[surface_name][0], x_grid, y_grid
                )

    cell_names: list[str] = []
    cell_match_masks: list[NDArray[np.bool_]] = []
    cell_indeterminate_masks: list[NDArray[np.bool_]] = []
    for prepared in prepared_cells:
        match_mask, indeterminate_mask = _evaluate_cell(
            prepared,
            surface_values,
            config.boundary_tolerance,
        )
        cell_names.append(prepared.cell.name)
        cell_match_masks.append(match_mask)
        cell_indeterminate_masks.append(indeterminate_mask)

    shape = x_grid.shape
    match_counts = np.zeros(shape, dtype=np.int64)
    any_indeterminate = np.zeros(shape, dtype=np.bool_)
    for match_mask, indeterminate_mask in zip(
        cell_match_masks, cell_indeterminate_masks, strict=True
    ):
        match_counts += match_mask
        any_indeterminate |= indeterminate_mask

    classifications = np.full(shape, PointClassification.INDETERMINATE, dtype=np.uint8)
    if prepared_cells:
        overlap_mask = match_counts >= 2
        indeterminate_mask = (match_counts < 2) & any_indeterminate
        determinate_mask = ~overlap_mask & ~indeterminate_mask
        classifications[overlap_mask] = PointClassification.OVERLAP
        classifications[determinate_mask & (match_counts == 0)] = (
            PointClassification.UNDEFINED
        )
        classifications[determinate_mask & (match_counts == 1)] = (
            PointClassification.NORMAL
        )

    overlap_count = _classification_count(classifications, PointClassification.OVERLAP)
    undefined_count = _classification_count(
        classifications, PointClassification.UNDEFINED
    )
    normal_count = _classification_count(classifications, PointClassification.NORMAL)
    indeterminate_count = _classification_count(
        classifications, PointClassification.INDETERMINATE
    )

    representative_args = (
        classifications,
        x_coordinates,
        y_coordinates,
        cell_names,
        cell_match_masks,
        config.max_representative_points,
    )
    return GeometrySamplingResult(
        config=config,
        x_coordinates=x_coordinates,
        y_coordinates=y_coordinates,
        classifications=classifications,
        match_counts=match_counts,
        included_cells=tuple(cell_names),
        excluded_cells=tuple(excluded_cells),
        overlap_count=overlap_count,
        undefined_count=undefined_count,
        normal_count=normal_count,
        indeterminate_count=indeterminate_count,
        overlap_representatives=_representatives(
            PointClassification.OVERLAP, *representative_args
        ),
        undefined_representatives=_representatives(
            PointClassification.UNDEFINED, *representative_args
        ),
        indeterminate_representatives=_representatives(
            PointClassification.INDETERMINATE, *representative_args
        ),
    )


def _group_surfaces(model: ParsedModel) -> dict[str, list[Surface]]:
    groups: dict[str, list[Surface]] = {}
    for surface in model.surfaces:
        groups.setdefault(surface.name, []).append(surface)
    return groups


def _retained_surface_cards(model: ParsedModel) -> dict[str, tuple[str | None, ...]]:
    cards: dict[str, list[str | None]] = {}
    for card in model.unknown_cards:
        if card.keyword.lower() != "surf" or len(card.tokens) < 2:
            continue
        surface_name = card.tokens[1]
        surface_type = card.tokens[2].lower() if len(card.tokens) >= 3 else None
        cards.setdefault(surface_name, []).append(surface_type)
    return {name: tuple(types) for name, types in cards.items()}


def _prepare_cells(
    model: ParsedModel,
    surface_groups: dict[str, list[Surface]],
    retained_surfaces: dict[str, tuple[str | None, ...]],
) -> tuple[list[_PreparedCell], list[ExcludedCell]]:
    prepared: list[_PreparedCell] = []
    excluded: list[ExcludedCell] = []

    for cell in model.cells:
        terms = tuple(tuple(term) for term in cell.intersection_terms)
        if not terms and cell.signed_surface_references:
            terms = (tuple(cell.signed_surface_references),)

        reasons: list[GeometryExclusion] = []
        if not terms or any(not term for term in terms):
            reasons.append(GeometryExclusion(code="empty_region"))

        for surface_name in dict.fromkeys(cell.referenced_surfaces):
            definitions = surface_groups.get(surface_name, [])
            retained_types = retained_surfaces.get(surface_name, ())
            total_definitions = len(definitions) + len(retained_types)
            if total_definitions > 1:
                reasons.append(
                    GeometryExclusion(
                        code="ambiguous_surface", surface_name=surface_name
                    )
                )
                continue
            if retained_types:
                retained_type = retained_types[0]
                code: GeometryExclusionCode = (
                    "invalid_surface_parameters"
                    if retained_type in SUPPORTED_GEOMETRY_SURFACE_TYPES
                    else "unsupported_surface_type"
                )
                reasons.append(
                    GeometryExclusion(
                        code=code,
                        surface_name=surface_name,
                        surface_type=retained_type,
                    )
                )
                continue
            if not definitions:
                reasons.append(
                    GeometryExclusion(
                        code="undefined_surface", surface_name=surface_name
                    )
                )
                continue

            surface = definitions[0]
            surface_type = surface.surface_type.lower()
            if surface_type not in SUPPORTED_GEOMETRY_SURFACE_TYPES:
                reasons.append(
                    GeometryExclusion(
                        code="unsupported_surface_type",
                        surface_name=surface_name,
                        surface_type=surface_type,
                    )
                )
            elif not _valid_surface_parameters(surface):
                reasons.append(
                    GeometryExclusion(
                        code="invalid_surface_parameters",
                        surface_name=surface_name,
                        surface_type=surface_type,
                    )
                )

        unique_reasons = tuple(dict.fromkeys(reasons))
        if unique_reasons:
            excluded.append(
                ExcludedCell(
                    name=cell.name,
                    location=cell.location,
                    reasons=unique_reasons,
                )
            )
        else:
            prepared.append(_PreparedCell(cell=cell, terms=terms))

    for card in model.unknown_cards:
        if card.keyword.lower() != "cell":
            continue
        name = card.tokens[1] if len(card.tokens) >= 2 else "<unknown>"
        excluded.append(
            ExcludedCell(
                name=name,
                location=card.location,
                reasons=(GeometryExclusion(code="unsupported_cell_syntax"),),
            )
        )

    return prepared, excluded


def _valid_surface_parameters(surface: Surface) -> bool:
    return (
        len(surface.parameters) == 3
        and all(isfinite(parameter) for parameter in surface.parameters)
        and surface.parameters[2] > 0.0
    )


def _signed_distance(
    surface: Surface,
    x_grid: NDArray[np.float64],
    y_grid: NDArray[np.float64],
) -> NDArray[np.float64]:
    x0, y0, extent = surface.parameters
    if surface.surface_type.lower() == "cyl":
        return np.hypot(x_grid - x0, y_grid - y0) - extent
    if surface.surface_type.lower() == "sqc":
        return np.maximum(np.abs(x_grid - x0), np.abs(y_grid - y0)) - extent
    raise ValueError(f"Unsupported prepared surface type: {surface.surface_type}")


def _evaluate_cell(
    prepared: _PreparedCell,
    surface_values: dict[str, NDArray[np.float64]],
    tolerance: float,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_]]:
    shape = next(iter(surface_values.values())).shape
    cell_match = np.zeros(shape, dtype=np.bool_)
    cell_indeterminate = np.zeros(shape, dtype=np.bool_)

    for term in prepared.terms:
        term_failed = np.zeros(shape, dtype=np.bool_)
        term_boundary = np.zeros(shape, dtype=np.bool_)
        for signed_reference in term:
            distance = surface_values[_unsigned_reference(signed_reference)]
            boundary = np.abs(distance) <= tolerance
            if signed_reference.startswith("-"):
                condition_matches = distance < -tolerance
            else:
                condition_matches = distance > tolerance
            term_failed |= ~(condition_matches | boundary)
            term_boundary |= boundary

        term_match = ~term_failed & ~term_boundary
        term_indeterminate = ~term_failed & term_boundary
        cell_match |= term_match
        cell_indeterminate |= term_indeterminate

    cell_indeterminate &= ~cell_match
    return cell_match, cell_indeterminate


def _unsigned_reference(signed_reference: str) -> str:
    return (
        signed_reference[1:]
        if signed_reference.startswith(("+", "-"))
        else signed_reference
    )


def _classification_count(
    classifications: NDArray[np.uint8], classification: PointClassification
) -> int:
    return int(np.count_nonzero(classifications == classification))


def _representatives(
    target: PointClassification,
    classifications: NDArray[np.uint8],
    x_coordinates: NDArray[np.float64],
    y_coordinates: NDArray[np.float64],
    cell_names: list[str],
    cell_match_masks: list[NDArray[np.bool_]],
    limit: int,
) -> tuple[RepresentativePoint, ...]:
    representatives: list[RepresentativePoint] = []
    for y_index, x_index in np.argwhere(classifications == target)[:limit]:
        involved_cells = tuple(
            cell_name
            for cell_name, match_mask in zip(cell_names, cell_match_masks, strict=True)
            if match_mask[y_index, x_index]
        )
        representatives.append(
            RepresentativePoint(
                x=float(x_coordinates[x_index]),
                y=float(y_coordinates[y_index]),
                involved_cells=involved_cells,
            )
        )
    return tuple(representatives)
