"""Deliberately limited, deterministic universe-local XY geometry sampling.

This module is independent of Streamlit and intentionally supports only the
surface subset documented by SerpentGuard. It is a sampling aid, not a full
Serpent CSG implementation or a replacement for Serpent's geometry plotter.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
from math import isfinite
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from serpentguard.models import (
    Cell,
    ParsedModel,
    SourceLocation,
    Surface,
    UnknownCard,
)

SUPPORTED_GEOMETRY_SURFACE_TYPES = frozenset({"cyl", "sqc"})
DEFAULT_BOUNDARY_TOLERANCE = 1.0e-9
DEFAULT_GRID_RESOLUTION = 100
MIN_GRID_RESOLUTION = 2
MAX_GRID_RESOLUTION = 500
DEFAULT_MAX_REPRESENTATIVE_POINTS = 10
DEFAULT_MAX_GEOMETRY_WORKLOAD = 50_000_000

GeometryExclusionCode = Literal[
    "unsupported_surface_type",
    "undefined_surface",
    "ambiguous_surface",
    "invalid_surface_parameters",
    "unsupported_cell_syntax",
    "empty_region",
    "duplicate_cell_name",
]


class GeometryConfigError(ValueError):
    """Raised when a requested sampling configuration is invalid."""


class GeometryUniverseError(GeometryConfigError):
    """Raised when the requested universe has no supported parsed cells."""

    def __init__(self, target_universe: str, available: tuple[str, ...]) -> None:
        self.target_universe = target_universe
        self.available_universes = available
        available_text = ", ".join(available) if available else "none"
        super().__init__(
            f"target universe {target_universe!r} is unavailable; "
            f"available universes: {available_text}"
        )


class GeometryWorkloadError(GeometryConfigError):
    """Raised before allocation when a sampling request exceeds the workload guard."""

    def __init__(
        self,
        estimate: GeometryWorkloadEstimate,
        limit: int,
    ) -> None:
        self.estimate = estimate
        self.limit = limit
        super().__init__(
            f"estimated workload {estimate.estimated_operations} exceeds limit {limit}"
        )


class PointClassification(IntEnum):
    """Classification assigned to one XY grid point."""

    UNDEFINED = 0
    NORMAL = 1
    OVERLAP = 2
    INCOMPLETE = 3
    BOUNDARY = 4
    # Backward-compatible alias for callers that treated all uncertainty alike.
    INDETERMINATE = INCOMPLETE


GeometryCategoryKind = Literal[
    "cell",
    "material",
    "outside",
    "void",
    "unsupported",
    "indeterminate",
    "undefined",
]


@dataclass(frozen=True, slots=True)
class GeometryCategory:
    """One language-neutral category referenced by an integer geometry grid."""

    key: str
    label: str
    kind: GeometryCategoryKind
    serpent_rgb: tuple[int, int, int] | None = None


@dataclass(frozen=True, slots=True)
class GeometrySamplingConfig:
    """Validated user-confirmed universe, XY slice, and grid configuration."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float
    z: float
    resolution: int
    target_universe: str
    boundary_tolerance: float = DEFAULT_BOUNDARY_TOLERANCE
    max_representative_points: int = DEFAULT_MAX_REPRESENTATIVE_POINTS
    max_workload: int = DEFAULT_MAX_GEOMETRY_WORKLOAD

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
        if not isinstance(self.target_universe, str) or not self.target_universe:
            raise GeometryConfigError("target_universe must be a non-empty string")
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
        if (
            isinstance(self.max_workload, bool)
            or not isinstance(self.max_workload, int)
            or self.max_workload < 1
        ):
            raise GeometryConfigError("max_workload must be a positive integer")


@dataclass(frozen=True, slots=True)
class GeometryWorkloadEstimate:
    """Conservative operation estimate evaluated before grid allocation."""

    grid_point_count: int
    evaluated_cell_count: int
    signed_reference_count: int
    estimated_operations: int


@dataclass(frozen=True, slots=True)
class GeometryExclusion:
    """One structured reason why a cell was not evaluated."""

    code: GeometryExclusionCode
    surface_name: str | None = None
    surface_type: str | None = None
    duplicate_count: int | None = None


@dataclass(frozen=True, slots=True)
class ExcludedCell:
    """A parsed or retained cell excluded from geometry sampling."""

    name: str
    location: SourceLocation
    reasons: tuple[GeometryExclusion, ...]
    universe: str | None = None


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
    selected_universe: str
    coverage_complete: bool
    undefined_detection_enabled: bool
    supported_cell_count: int
    excluded_cell_count: int
    signed_reference_count: int
    workload: GeometryWorkloadEstimate
    x_coordinates: NDArray[np.float64]
    y_coordinates: NDArray[np.float64]
    classifications: NDArray[np.uint8]
    match_counts: NDArray[np.int64]
    cell_category_grid: NDArray[np.int32]
    material_category_grid: NDArray[np.int32]
    cell_categories: tuple[GeometryCategory, ...]
    material_categories: tuple[GeometryCategory, ...]
    included_cells: tuple[str, ...]
    excluded_cells: tuple[ExcludedCell, ...]
    overlap_count: int
    undefined_count: int
    normal_count: int
    indeterminate_count: int
    incomplete_count: int
    boundary_indeterminate_count: int
    incomplete_domain_count: int
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


def available_universes(model: ParsedModel) -> tuple[str, ...]:
    """Return deterministic universe choices from supported parsed cells only."""
    return tuple(sorted({cell.universe for cell in model.cells}))


def default_target_universe(model: ParsedModel) -> str | None:
    """Prefer universe 0, otherwise return the first deterministic choice."""
    universes = available_universes(model)
    if "0" in universes:
        return "0"
    return universes[0] if universes else None


def sample_geometry(
    model: ParsedModel,
    config: GeometrySamplingConfig,
) -> GeometrySamplingResult:
    """Sample one universe over a user-confirmed, inclusive XY grid.

    Boundary points are indeterminate. A cell is evaluated only when every
    referenced surface has one unambiguous, valid supported definition. When
    any selected-universe cell is excluded, zero supported matches are also
    indeterminate because an excluded cell could occupy that point.
    """
    universes = available_universes(model)
    if config.target_universe not in universes:
        raise GeometryUniverseError(config.target_universe, universes)

    surface_groups = _group_surfaces(model)
    retained_surfaces = _retained_surface_cards(model)
    prepared_cells, excluded_cells = _prepare_cells(
        model,
        config.target_universe,
        surface_groups,
        retained_surfaces,
    )
    workload = _estimate_workload(config, prepared_cells)
    if workload.estimated_operations > config.max_workload:
        raise GeometryWorkloadError(workload, config.max_workload)

    x_coordinates = np.linspace(
        config.xmin, config.xmax, config.resolution, dtype=np.float64
    )
    y_coordinates = np.linspace(
        config.ymin, config.ymax, config.resolution, dtype=np.float64
    )
    x_values = x_coordinates[np.newaxis, :]
    y_values = y_coordinates[:, np.newaxis]
    shape = (config.resolution, config.resolution)

    surfaces = {
        surface_name: definitions[0]
        for surface_name, definitions in surface_groups.items()
        if len(definitions) == 1
    }
    match_counts = np.zeros(shape, dtype=np.int64)
    unique_match_indices = np.full(shape, -1, dtype=np.int32)
    any_indeterminate = np.zeros(shape, dtype=np.bool_)
    for prepared_index, prepared in enumerate(prepared_cells):
        match_mask, indeterminate_mask = _evaluate_cell(
            prepared,
            surfaces,
            x_values,
            y_values,
            config.boundary_tolerance,
            shape,
        )
        first_match = match_mask & (match_counts == 0)
        repeated_match = match_mask & (match_counts > 0)
        unique_match_indices[first_match] = prepared_index
        unique_match_indices[repeated_match] = -1
        match_counts += match_mask
        any_indeterminate |= indeterminate_mask

    coverage_complete = not excluded_cells
    classifications = np.full(shape, PointClassification.INCOMPLETE, dtype=np.uint8)
    overlap_mask = match_counts >= 2
    boundary_indeterminate_mask = (match_counts < 2) & any_indeterminate
    certain_mask = ~overlap_mask & ~boundary_indeterminate_mask
    single_match_mask = certain_mask & (match_counts == 1)
    zero_match_mask = certain_mask & (match_counts == 0)

    classifications[overlap_mask] = PointClassification.OVERLAP
    classifications[boundary_indeterminate_mask] = PointClassification.BOUNDARY
    if coverage_complete:
        classifications[single_match_mask] = PointClassification.NORMAL
        classifications[zero_match_mask] = PointClassification.UNDEFINED

    incomplete_domain_count = (
        int(np.count_nonzero(zero_match_mask)) if not coverage_complete else 0
    )
    overlap_count = _classification_count(classifications, PointClassification.OVERLAP)
    undefined_count = _classification_count(
        classifications, PointClassification.UNDEFINED
    )
    normal_count = _classification_count(classifications, PointClassification.NORMAL)
    incomplete_count = _classification_count(
        classifications, PointClassification.INCOMPLETE
    )
    boundary_indeterminate_count = _classification_count(
        classifications, PointClassification.BOUNDARY
    )
    indeterminate_count = incomplete_count + boundary_indeterminate_count
    cell_category_grid, cell_categories = _build_geometry_categories(
        model,
        prepared_cells,
        unique_match_indices,
        classifications,
        color_by="cell",
    )
    material_category_grid, material_categories = _build_geometry_categories(
        model,
        prepared_cells,
        unique_match_indices,
        classifications,
        color_by="material",
    )

    representative_args = (
        classifications,
        x_coordinates,
        y_coordinates,
        prepared_cells,
        surfaces,
        config.boundary_tolerance,
        config.max_representative_points,
    )
    return GeometrySamplingResult(
        config=config,
        selected_universe=config.target_universe,
        coverage_complete=coverage_complete,
        undefined_detection_enabled=coverage_complete,
        supported_cell_count=len(prepared_cells),
        excluded_cell_count=len(excluded_cells),
        signed_reference_count=workload.signed_reference_count,
        workload=workload,
        x_coordinates=x_coordinates,
        y_coordinates=y_coordinates,
        classifications=classifications,
        match_counts=match_counts,
        cell_category_grid=cell_category_grid,
        material_category_grid=material_category_grid,
        cell_categories=cell_categories,
        material_categories=material_categories,
        included_cells=tuple(prepared.cell.name for prepared in prepared_cells),
        excluded_cells=tuple(excluded_cells),
        overlap_count=overlap_count,
        undefined_count=undefined_count,
        normal_count=normal_count,
        indeterminate_count=indeterminate_count,
        incomplete_count=incomplete_count,
        boundary_indeterminate_count=boundary_indeterminate_count,
        incomplete_domain_count=incomplete_domain_count,
        overlap_representatives=_representatives(
            PointClassification.OVERLAP, *representative_args
        ),
        undefined_representatives=_representatives(
            PointClassification.UNDEFINED, *representative_args
        ),
        indeterminate_representatives=_representatives(
            PointClassification.INCOMPLETE, *representative_args
        ),
    )


def _build_geometry_categories(
    model: ParsedModel,
    prepared_cells: list[_PreparedCell],
    unique_match_indices: NDArray[np.int32],
    classifications: NDArray[np.uint8],
    *,
    color_by: Literal["cell", "material"],
) -> tuple[NDArray[np.int32], tuple[GeometryCategory, ...]]:
    """Build compact categorical occupancy without storing strings per point."""
    grid = np.full(classifications.shape, -1, dtype=np.int32)
    categories: list[GeometryCategory] = []
    category_indices: dict[str, int] = {}
    material_groups: dict[str, list[tuple[int, int, int] | None]] = {}
    for material in model.materials:
        material_groups.setdefault(material.name, []).append(material.rgb)

    def add(category: GeometryCategory) -> int:
        existing = category_indices.get(category.key)
        if existing is not None:
            return existing
        index = len(categories)
        categories.append(category)
        category_indices[category.key] = index
        return index

    normal_mask = classifications == PointClassification.NORMAL
    for prepared_index, prepared in enumerate(prepared_cells):
        cell = prepared.cell
        cell_mask = normal_mask & (unique_match_indices == prepared_index)
        if not np.any(cell_mask):
            continue
        if color_by == "cell":
            kind: GeometryCategoryKind = (
                cell.fill_type if cell.fill_type in {"void", "outside"} else "cell"
            )
            category = GeometryCategory(
                key=f"cell:{cell.name}", label=cell.name, kind=kind
            )
        elif cell.fill_type in {"void", "outside"}:
            category = GeometryCategory(
                key=f"special:{cell.fill_type}",
                label=cell.fill_type,
                kind=cell.fill_type,
            )
        else:
            material_name = cell.material or ""
            definitions = material_groups.get(material_name, [])
            rgb = definitions[0] if len(definitions) == 1 else None
            category = GeometryCategory(
                key=f"material:{material_name}",
                label=material_name,
                kind="material",
                serpent_rgb=rgb,
            )
        grid[cell_mask] = add(category)

    special_states: tuple[tuple[PointClassification, GeometryCategory], ...] = (
        (
            PointClassification.OVERLAP,
            GeometryCategory("special:indeterminate", "indeterminate", "indeterminate"),
        ),
        (
            PointClassification.BOUNDARY,
            GeometryCategory("special:indeterminate", "indeterminate", "indeterminate"),
        ),
        (
            PointClassification.INCOMPLETE,
            GeometryCategory("special:unsupported", "unsupported", "unsupported"),
        ),
        (
            PointClassification.UNDEFINED,
            GeometryCategory("special:undefined", "undefined", "undefined"),
        ),
    )
    for classification, category in special_states:
        mask = classifications == classification
        if np.any(mask):
            grid[mask] = add(category)
    return grid, tuple(categories)


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
    target_universe: str,
    surface_groups: dict[str, list[Surface]],
    retained_surfaces: dict[str, tuple[str | None, ...]],
) -> tuple[list[_PreparedCell], list[ExcludedCell]]:
    selected_cells = [cell for cell in model.cells if cell.universe == target_universe]
    selected_unknown_cells = [
        card
        for card in model.unknown_cards
        if card.keyword.lower() == "cell"
        and _unknown_cell_universe(card) in {None, target_universe}
    ]
    definition_counts = Counter(cell.name for cell in selected_cells)
    definition_counts.update(
        _unknown_cell_name(card) for card in selected_unknown_cells
    )

    prepared: list[_PreparedCell] = []
    excluded: list[ExcludedCell] = []
    for cell in selected_cells:
        terms = tuple(tuple(term) for term in cell.intersection_terms)
        if not terms and cell.signed_surface_references:
            terms = (tuple(cell.signed_surface_references),)

        if definition_counts[cell.name] > 1:
            excluded.append(
                ExcludedCell(
                    name=cell.name,
                    location=cell.location,
                    reasons=(
                        GeometryExclusion(
                            code="duplicate_cell_name",
                            duplicate_count=definition_counts[cell.name],
                        ),
                    ),
                    universe=target_universe,
                )
            )
            continue

        reasons: list[GeometryExclusion] = []
        if not terms or any(not term for term in terms):
            reasons.append(GeometryExclusion(code="empty_region"))

        referenced_surfaces = dict.fromkeys(
            _unsigned_reference(reference) for term in terms for reference in term
        )
        for surface_name in referenced_surfaces:
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
                    universe=target_universe,
                )
            )
        else:
            prepared.append(_PreparedCell(cell=cell, terms=terms))

    for card in selected_unknown_cells:
        name = _unknown_cell_name(card)
        reasons: list[GeometryExclusion] = [
            GeometryExclusion(code="unsupported_cell_syntax")
        ]
        if definition_counts[name] > 1:
            reasons.insert(
                0,
                GeometryExclusion(
                    code="duplicate_cell_name",
                    duplicate_count=definition_counts[name],
                ),
            )
        excluded.append(
            ExcludedCell(
                name=name,
                location=card.location,
                reasons=tuple(reasons),
                universe=_unknown_cell_universe(card),
            )
        )

    return prepared, excluded


def _unknown_cell_name(card: UnknownCard) -> str:
    return card.tokens[1] if len(card.tokens) >= 2 else "<unknown>"


def _unknown_cell_universe(card: UnknownCard) -> str | None:
    return card.tokens[2] if len(card.tokens) >= 3 else None


def _estimate_workload(
    config: GeometrySamplingConfig,
    prepared_cells: list[_PreparedCell],
) -> GeometryWorkloadEstimate:
    grid_point_count = config.resolution**2
    signed_reference_count = sum(
        len(prepared.cell.signed_surface_references) for prepared in prepared_cells
    )
    estimated_operations = grid_point_count * (
        len(prepared_cells) + signed_reference_count
    )
    return GeometryWorkloadEstimate(
        grid_point_count=grid_point_count,
        evaluated_cell_count=len(prepared_cells),
        signed_reference_count=signed_reference_count,
        estimated_operations=estimated_operations,
    )


def _valid_surface_parameters(surface: Surface) -> bool:
    return (
        len(surface.parameters) == 3
        and all(isfinite(parameter) for parameter in surface.parameters)
        and surface.parameters[2] > 0.0
    )


def _signed_distance(
    surface: Surface,
    x_values: NDArray[np.float64],
    y_values: NDArray[np.float64],
) -> NDArray[np.float64]:
    x0, y0, extent = surface.parameters
    if surface.surface_type.lower() == "cyl":
        return np.hypot(x_values - x0, y_values - y0) - extent
    if surface.surface_type.lower() == "sqc":
        return np.maximum(np.abs(x_values - x0), np.abs(y_values - y0)) - extent
    raise ValueError(f"Unsupported prepared surface type: {surface.surface_type}")


def _evaluate_cell(
    prepared: _PreparedCell,
    surfaces: dict[str, Surface],
    x_values: NDArray[np.float64],
    y_values: NDArray[np.float64],
    tolerance: float,
    shape: tuple[int, ...],
) -> tuple[NDArray[np.bool_], NDArray[np.bool_]]:
    cell_match = np.zeros(shape, dtype=np.bool_)
    cell_indeterminate = np.zeros(shape, dtype=np.bool_)

    for term in prepared.terms:
        term_failed = np.zeros(shape, dtype=np.bool_)
        term_boundary = np.zeros(shape, dtype=np.bool_)
        for signed_reference in term:
            surface = surfaces[_unsigned_reference(signed_reference)]
            distance = _signed_distance(surface, x_values, y_values)
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
    prepared_cells: list[_PreparedCell],
    surfaces: dict[str, Surface],
    tolerance: float,
    limit: int,
) -> tuple[RepresentativePoint, ...]:
    indices = np.argwhere(classifications == target)[:limit]
    if len(indices) == 0:
        return ()

    x_values = np.asarray(
        [x_coordinates[x_index] for _, x_index in indices], dtype=np.float64
    )
    y_values = np.asarray(
        [y_coordinates[y_index] for y_index, _ in indices], dtype=np.float64
    )
    involved_cells: list[list[str]] = [[] for _ in indices]
    for prepared in prepared_cells:
        match_mask, _ = _evaluate_cell(
            prepared,
            surfaces,
            x_values,
            y_values,
            tolerance,
            (len(indices),),
        )
        for point_index in np.flatnonzero(match_mask):
            involved_cells[point_index].append(prepared.cell.name)

    return tuple(
        RepresentativePoint(
            x=float(x_values[index]),
            y=float(y_values[index]),
            involved_cells=tuple(involved_cells[index]),
        )
        for index in range(len(indices))
    )
