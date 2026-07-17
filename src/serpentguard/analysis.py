"""Deterministic symbol-table checks for the supported parsed model."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import prod
from typing import TypeVar

from serpentguard.models import (
    AnalysisReport,
    Cell,
    Detector,
    DiagnosticSeverity,
    EnergyGrid,
    Finding,
    FindingConfidence,
    Material,
    ParsedModel,
    ParserDiagnostic,
    SourceLocation,
    Surface,
    UnknownCard,
)

UNRECOVERABLE_PARSER_CODES = frozenset({"PARSER_IO", "PARSER_ENCODING"})
_BOUNDING_BOX_UNCERTAINTY_KEYWORDS = frozenset(
    {
        "cell",
        "dtrans",
        "ftrans",
        "include",
        "lat",
        "nest",
        "pbed",
        "pin",
        "solid",
        "strans",
        "surf",
        "trans",
        "transa",
        "transb",
        "transv",
        "umsh",
        "utrans",
        "voro",
    }
)
DefinitionT = TypeVar("DefinitionT", Surface, Cell, Material, EnergyGrid, Detector)


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """Explicit thresholds for deterministic complexity review."""

    max_region_references: int = 20
    max_union_operators: int = 4
    max_detector_total_bins: int = 1_000_000

    def __post_init__(self) -> None:
        if self.max_region_references < 1:
            raise ValueError("max_region_references must be at least 1")
        if self.max_union_operators < 0:
            raise ValueError("max_union_operators cannot be negative")
        if self.max_detector_total_bins < 1:
            raise ValueError("max_detector_total_bins must be at least 1")


@dataclass(frozen=True, slots=True)
class SymbolTable:
    """All supported definitions grouped by exact, case-preserved name."""

    surfaces: dict[str, list[Surface]]
    cells: dict[str, list[Cell]]
    materials: dict[str, list[Material]]
    energy_grids: dict[str, list[EnergyGrid]]
    detectors: dict[str, list[Detector]]

    @classmethod
    def from_model(cls, model: ParsedModel) -> SymbolTable:
        return cls(
            surfaces=_group_by_name(model.surfaces),
            cells=_group_by_name(model.cells),
            materials=_group_by_name(model.materials),
            energy_grids=_group_by_name(model.energy_grids),
            detectors=_group_by_name(model.detectors),
        )


def analyze_model(
    model: ParsedModel,
    *,
    config: AnalysisConfig | None = None,
) -> AnalysisReport:
    """Run static checks without geometry evaluation, AI, or external access."""
    active_config = config or AnalysisConfig()
    symbols = SymbolTable.from_model(model)
    findings: list[Finding] = []

    findings.extend(
        _duplicate_findings(
            symbols.surfaces,
            rule_id="SG001",
            title="Duplicate surface",
            object_type="surface",
        )
    )
    findings.extend(
        _duplicate_findings(
            symbols.cells,
            rule_id="SG002",
            title="Duplicate cell",
            object_type="cell",
        )
    )
    findings.extend(
        _duplicate_findings(
            symbols.materials,
            rule_id="SG003",
            title="Duplicate material",
            object_type="material",
        )
    )
    findings.extend(
        _duplicate_findings(
            symbols.detectors,
            rule_id="SG021",
            title="Duplicate detector",
            object_type="detector",
        )
    )
    findings.extend(_undefined_surface_findings(model, symbols))
    findings.extend(_undefined_material_findings(model, symbols))
    findings.extend(_unused_surface_findings(model, symbols))
    findings.extend(_unused_material_findings(model, symbols))
    findings.extend(_contradictory_surface_findings(model))
    findings.extend(_duplicate_condition_findings(model))
    findings.extend(_complexity_findings(model, active_config))
    findings.extend(_undefined_energy_grid_findings(model, symbols))
    findings.extend(_invalid_detector_bin_findings(model))
    findings.extend(_extreme_detector_bin_findings(model, symbols, active_config))
    findings.extend(_detector_extent_findings(model, symbols))
    findings.extend(_unsupported_detector_option_findings(model))
    findings.extend(_diagnostic_findings(model))

    return AnalysisReport(
        model_summary={
            "surfaces": len(model.surfaces),
            "cells": len(model.cells),
            "materials": len(model.materials),
            "energy_grids": len(model.energy_grids),
            "detectors": len(model.detectors),
            "unknown_cards": len(model.unknown_cards),
            "parser_diagnostics": len(model.diagnostics),
        },
        findings=findings,
        limitations=[
            (
                "Only the documented parsed surf, cell, mat, ene, and det subset "
                "is analyzed."
            ),
            "Object names are matched exactly with case preserved.",
            "Detector purpose, response physics, includes, and AI are not analyzed.",
        ],
    )


def has_unrecoverable_parse_failure(model: ParsedModel) -> bool:
    """Return whether parsing could not begin for the requested local file."""
    return any(item.code in UNRECOVERABLE_PARSER_CODES for item in model.diagnostics)


def _group_by_name(
    definitions: list[DefinitionT],
) -> dict[str, list[DefinitionT]]:
    groups: dict[str, list[DefinitionT]] = {}
    for definition in definitions:
        groups.setdefault(definition.name, []).append(definition)
    return groups


def _duplicate_findings(
    groups: dict[str, list[Surface]]
    | dict[str, list[Cell]]
    | dict[str, list[Material]]
    | dict[str, list[Detector]],
    *,
    rule_id: str,
    title: str,
    object_type: str,
) -> list[Finding]:
    findings: list[Finding] = []
    for name, definitions in groups.items():
        if len(definitions) < 2:
            continue
        locations = [_location_evidence(item.location) for item in definitions]
        findings.append(
            _finding(
                rule_id=rule_id,
                severity="ERROR",
                title=title,
                message=(
                    f"The {object_type} name '{name}' is defined "
                    f"{len(definitions)} times in the parsed model."
                ),
                location=definitions[1].location,
                object_type=object_type,
                object_name=name,
                evidence={
                    "definition_count": len(definitions),
                    "definitions": locations,
                },
                confidence="high",
            )
        )
    return findings


def _undefined_surface_findings(
    model: ParsedModel,
    symbols: SymbolTable,
) -> list[Finding]:
    findings: list[Finding] = []
    incomplete = _has_unknown_syntax(model, {"cell", "surf"})
    for cell in model.cells:
        for reference in dict.fromkeys(cell.referenced_surfaces):
            if reference in symbols.surfaces:
                continue
            signed_forms = [
                item
                for item in cell.signed_surface_references
                if item.removeprefix("-") == reference
            ]
            findings.append(
                _finding(
                    rule_id="SG004",
                    severity="ERROR",
                    title="Undefined surface reference",
                    message=(
                        f"Cell '{cell.name}' references surface '{reference}', but no "
                        "supported definition with that exact name was parsed."
                    ),
                    location=cell.location,
                    object_type="cell",
                    object_name=cell.name,
                    evidence={
                        "reference": reference,
                        "signed_forms": signed_forms,
                        "matching_policy": "exact-case",
                        "analysis_scope": "supported-parsed-model",
                    },
                    confidence=_scope_confidence(incomplete),
                )
            )
    return findings


def _undefined_material_findings(
    model: ParsedModel,
    symbols: SymbolTable,
) -> list[Finding]:
    findings: list[Finding] = []
    incomplete = _has_unknown_syntax(model, {"cell", "mat"})
    for cell in model.cells:
        if cell.fill_type != "material" or cell.material is None:
            continue
        if cell.material in symbols.materials:
            continue
        findings.append(
            _finding(
                rule_id="SG005",
                severity="ERROR",
                title="Undefined material reference",
                message=(
                    f"Cell '{cell.name}' references material '{cell.material}', but "
                    "no supported definition with that exact name was parsed."
                ),
                location=cell.location,
                object_type="cell",
                object_name=cell.name,
                evidence={
                    "reference": cell.material,
                    "matching_policy": "exact-case",
                    "analysis_scope": "supported-parsed-model",
                },
                confidence=_scope_confidence(incomplete),
            )
        )
    return findings


def _unused_surface_findings(
    model: ParsedModel,
    symbols: SymbolTable,
) -> list[Finding]:
    referenced = {
        reference for cell in model.cells for reference in cell.referenced_surfaces
    }
    incomplete = _has_unknown_syntax(model, {"cell"})
    findings: list[Finding] = []
    for name, definitions in symbols.surfaces.items():
        if name in referenced:
            continue
        findings.append(
            _finding(
                rule_id="SG006",
                severity="INFO",
                title="Unused surface",
                message=(
                    f"Surface '{name}' is not referenced by any supported parsed cell."
                ),
                location=definitions[0].location,
                object_type="surface",
                object_name=name,
                evidence={
                    "definition_count": len(definitions),
                    "reference_count": 0,
                    "analysis_scope": "supported-parsed-cells",
                },
                confidence=_scope_confidence(incomplete),
            )
        )
    return findings


def _unused_material_findings(
    model: ParsedModel,
    symbols: SymbolTable,
) -> list[Finding]:
    referenced = {
        cell.material
        for cell in model.cells
        if cell.fill_type == "material" and cell.material is not None
    }
    incomplete = _has_unknown_syntax(model, {"cell"})
    findings: list[Finding] = []
    for name, definitions in symbols.materials.items():
        if name in referenced:
            continue
        findings.append(
            _finding(
                rule_id="SG007",
                severity="INFO",
                title="Unused material",
                message=(
                    f"Material '{name}' is not referenced by any supported parsed cell."
                ),
                location=definitions[0].location,
                object_type="material",
                object_name=name,
                evidence={
                    "definition_count": len(definitions),
                    "reference_count": 0,
                    "analysis_scope": "supported-parsed-cells",
                },
                confidence=_scope_confidence(incomplete),
            )
        )
    return findings


def _contradictory_surface_findings(model: ParsedModel) -> list[Finding]:
    findings: list[Finding] = []
    for cell in model.cells:
        for term_index, references in enumerate(_intersection_terms(cell), start=1):
            signs: dict[str, set[str]] = {}
            counts = Counter(references)
            for reference in references:
                name = reference.removeprefix("-")
                sign = "negative" if reference.startswith("-") else "positive"
                signs.setdefault(name, set()).add(sign)
            for name, observed_signs in signs.items():
                if observed_signs != {"positive", "negative"}:
                    continue
                findings.append(
                    _finding(
                        rule_id="SG008",
                        severity="WARNING",
                        title="Contradictory signed surface",
                        message=(
                            f"Cell '{cell.name}' uses both signs of surface '{name}' "
                            f"within intersection term {term_index}."
                        ),
                        location=cell.location,
                        object_type="cell",
                        object_name=cell.name,
                        evidence={
                            "surface": name,
                            "intersection_term": term_index,
                            "positive_count": counts[name],
                            "negative_count": counts[f"-{name}"],
                        },
                        confidence="high",
                    )
                )
    return findings


def _duplicate_condition_findings(model: ParsedModel) -> list[Finding]:
    findings: list[Finding] = []
    for cell in model.cells:
        for term_index, references in enumerate(_intersection_terms(cell), start=1):
            for reference, count in Counter(references).items():
                if count < 2:
                    continue
                findings.append(
                    _finding(
                        rule_id="SG009",
                        severity="WARNING",
                        title="Duplicate region condition",
                        message=(
                            f"Cell '{cell.name}' repeats signed condition "
                            f"'{reference}' {count} times within intersection term "
                            f"{term_index}."
                        ),
                        location=cell.location,
                        object_type="cell",
                        object_name=cell.name,
                        evidence={
                            "signed_condition": reference,
                            "occurrences": count,
                            "intersection_term": term_index,
                        },
                        confidence="high",
                    )
                )
    return findings


def _complexity_findings(
    model: ParsedModel,
    config: AnalysisConfig,
) -> list[Finding]:
    findings: list[Finding] = []
    for cell in model.cells:
        reference_count = len(cell.signed_surface_references)
        union_operators = max(len(_intersection_terms(cell)) - 1, 0)
        exceeded: dict[str, dict[str, int]] = {}
        if reference_count > config.max_region_references:
            exceeded["surface_references"] = {
                "actual": reference_count,
                "limit": config.max_region_references,
            }
        if union_operators > config.max_union_operators:
            exceeded["union_operators"] = {
                "actual": union_operators,
                "limit": config.max_union_operators,
            }
        if not exceeded:
            continue
        findings.append(
            _finding(
                rule_id="SG010",
                severity="REVIEW",
                title="Excessively complex region expression",
                message=(
                    f"Cell '{cell.name}' exceeds the configured syntactic complexity "
                    "threshold and should be reviewed manually."
                ),
                location=cell.location,
                object_type="cell",
                object_name=cell.name,
                evidence={
                    "surface_reference_count": reference_count,
                    "union_operator_count": union_operators,
                    "exceeded_thresholds": exceeded,
                },
                confidence="high",
            )
        )
    return findings


def _undefined_energy_grid_findings(
    model: ParsedModel,
    symbols: SymbolTable,
) -> list[Finding]:
    findings: list[Finding] = []
    incomplete = _has_unknown_syntax(model, {"det", "ene"})
    for detector in model.detectors:
        for reference in detector.energy_grid_references:
            if reference.name in symbols.energy_grids:
                continue
            findings.append(
                _finding(
                    rule_id="SG022",
                    severity="ERROR",
                    title="Undefined detector energy-grid reference",
                    message=(
                        f"Detector '{detector.name}' references energy grid "
                        f"'{reference.name}', but no supported definition with that "
                        "exact name was parsed."
                    ),
                    location=reference.location,
                    object_type="detector",
                    object_name=detector.name,
                    evidence={
                        "reference": reference.name,
                        "matching_policy": "exact-case",
                        "analysis_scope": "supported-parsed-energy-grids",
                    },
                    confidence=_scope_confidence(incomplete),
                )
            )
    return findings


def _invalid_detector_bin_findings(model: ParsedModel) -> list[Finding]:
    findings: list[Finding] = []
    for grid in model.energy_grids:
        if grid.bin_count <= 0:
            findings.append(
                _finding(
                    rule_id="SG023",
                    severity="ERROR",
                    title="Non-positive bin count",
                    message=(
                        f"Energy grid '{grid.name}' has non-positive bin count "
                        f"{grid.bin_count}."
                    ),
                    location=grid.location,
                    object_type="energy_grid",
                    object_name=grid.name,
                    evidence={
                        "option": "ene",
                        "bin_count": grid.bin_count,
                    },
                    confidence="high",
                )
            )
        if (
            grid.grid_type in {2, 3}
            and grid.minimum is not None
            and grid.maximum is not None
            and grid.minimum >= grid.maximum
        ):
            findings.append(
                _invalid_bounds_finding(
                    name=grid.name,
                    object_type="energy_grid",
                    option="ene",
                    minimum=grid.minimum,
                    maximum=grid.maximum,
                    location=grid.location,
                )
            )

    for detector in model.detectors:
        for axis in detector.mesh_axes:
            option = f"d{axis.axis}"
            if axis.bin_count <= 0:
                findings.append(
                    _finding(
                        rule_id="SG023",
                        severity="ERROR",
                        title="Non-positive bin count",
                        message=(
                            f"Detector '{detector.name}' option '{option}' has "
                            f"non-positive bin count {axis.bin_count}."
                        ),
                        location=axis.location,
                        object_type="detector",
                        object_name=detector.name,
                        evidence={
                            "option": option,
                            "bin_count": axis.bin_count,
                        },
                        confidence="high",
                    )
                )
            if axis.minimum >= axis.maximum:
                findings.append(
                    _invalid_bounds_finding(
                        name=detector.name,
                        object_type="detector",
                        option=option,
                        minimum=axis.minimum,
                        maximum=axis.maximum,
                        location=axis.location,
                    )
                )
    return findings


def _invalid_bounds_finding(
    *,
    name: str,
    object_type: str,
    option: str,
    minimum: float,
    maximum: float,
    location: SourceLocation,
) -> Finding:
    object_label = "Energy grid" if object_type == "energy_grid" else "Detector"
    return _finding(
        rule_id="SG024",
        severity="ERROR",
        title="Invalid bin range",
        message=(
            f"{object_label} '{name}' option '{option}' has minimum {minimum} "
            f"greater than or equal to maximum {maximum}."
        ),
        location=location,
        object_type=object_type,
        object_name=name,
        evidence={
            "option": option,
            "minimum": minimum,
            "maximum": maximum,
        },
        confidence="high",
    )


def _extreme_detector_bin_findings(
    model: ParsedModel,
    symbols: SymbolTable,
    config: AnalysisConfig,
) -> list[Finding]:
    findings: list[Finding] = []
    for detector in model.detectors:
        factors: dict[str, int] = {}
        invalid = False
        for axis in detector.mesh_axes:
            if axis.bin_count <= 0 or axis.minimum >= axis.maximum:
                invalid = True
                break
            factors[f"d{axis.axis}"] = axis.bin_count
        if invalid:
            continue

        references = detector.energy_grid_references
        if len(references) > 1:
            continue
        if references:
            definitions = symbols.energy_grids.get(references[0].name, [])
            if len(definitions) != 1 or definitions[0].bin_count <= 0:
                continue
            grid = definitions[0]
            if (
                grid.grid_type in {2, 3}
                and grid.minimum is not None
                and grid.maximum is not None
                and grid.minimum >= grid.maximum
            ):
                continue
            factors["de"] = grid.bin_count

        total_bins = prod(factors.values()) if factors else 1
        if total_bins <= config.max_detector_total_bins:
            continue
        findings.append(
            _finding(
                rule_id="SG025",
                severity="REVIEW",
                title="Extreme detector bin count",
                message=(
                    f"Detector '{detector.name}' produces {total_bins} bins across "
                    "the supported options, exceeding the configured review "
                    f"threshold {config.max_detector_total_bins}."
                ),
                location=detector.location,
                object_type="detector",
                object_name=detector.name,
                evidence={
                    "total_bin_count": total_bins,
                    "threshold": config.max_detector_total_bins,
                    "factors": factors,
                },
                confidence="high",
            )
        )
    return findings


@dataclass(frozen=True, slots=True)
class _XYBounds:
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    surface_name: str


def _detector_extent_findings(
    model: ParsedModel,
    symbols: SymbolTable,
) -> list[Finding]:
    bounds = _available_root_xy_bounds(model, symbols)
    if bounds is None:
        return []
    findings: list[Finding] = []
    for detector in model.detectors:
        axes = {axis.axis: axis for axis in detector.mesh_axes}
        x_axis = axes.get("x")
        y_axis = axes.get("y")
        if x_axis is None or y_axis is None:
            continue
        if (
            x_axis.minimum >= x_axis.maximum
            or y_axis.minimum >= y_axis.maximum
            or x_axis.bin_count <= 0
            or y_axis.bin_count <= 0
        ):
            continue
        completely_outside = (
            x_axis.maximum < bounds.xmin
            or x_axis.minimum > bounds.xmax
            or y_axis.maximum < bounds.ymin
            or y_axis.minimum > bounds.ymax
        )
        if not completely_outside:
            continue
        findings.append(
            _finding(
                rule_id="SG026",
                severity="REVIEW",
                title="Detector extent outside available geometry bounds",
                message=(
                    f"Detector '{detector.name}' has an XY mesh extent completely "
                    "outside the available supported root-geometry bounding box."
                ),
                location=detector.location,
                object_type="detector",
                object_name=detector.name,
                evidence={
                    "detector_xy_bounds": [
                        x_axis.minimum,
                        x_axis.maximum,
                        y_axis.minimum,
                        y_axis.maximum,
                    ],
                    "geometry_xy_bounds": [
                        bounds.xmin,
                        bounds.xmax,
                        bounds.ymin,
                        bounds.ymax,
                    ],
                    "geometry_boundary_surface": bounds.surface_name,
                    "geometry_universe": "0",
                },
                confidence="high",
            )
        )
    return findings


def _available_root_xy_bounds(
    model: ParsedModel,
    symbols: SymbolTable,
) -> _XYBounds | None:
    if any(
        card.keyword in _BOUNDING_BOX_UNCERTAINTY_KEYWORDS
        for card in model.unknown_cards
    ):
        return None
    boundary_names: list[str] = []
    for cell in model.cells:
        terms = _intersection_terms(cell)
        if cell.universe != "0" or cell.fill_type != "outside" or len(terms) != 1:
            continue
        if len(terms[0]) != 1 or terms[0][0].startswith("-"):
            continue
        boundary_names.append(terms[0][0])
    if len(boundary_names) != 1:
        return None
    surface_name = boundary_names[0]
    definitions = symbols.surfaces.get(surface_name, [])
    if len(definitions) != 1:
        return None
    surface = definitions[0]
    if (
        surface.surface_type not in {"cyl", "sqc"}
        or len(surface.parameters) != 3
        or surface.parameters[2] <= 0.0
    ):
        return None
    x0, y0, extent = surface.parameters
    return _XYBounds(
        xmin=x0 - extent,
        xmax=x0 + extent,
        ymin=y0 - extent,
        ymax=y0 + extent,
        surface_name=surface.name,
    )


def _unsupported_detector_option_findings(model: ParsedModel) -> list[Finding]:
    findings: list[Finding] = []
    for detector in model.detectors:
        for option in detector.unsupported_options:
            if option.reason == "malformed":
                continue
            findings.append(
                _finding(
                    rule_id="SG027",
                    severity="INFO",
                    title="Unsupported detector option",
                    message=(
                        f"Detector '{detector.name}' option '{option.keyword}' was "
                        "retained without interpretation."
                    ),
                    location=option.location,
                    object_type="detector",
                    object_name=detector.name,
                    evidence={
                        "option": option.keyword,
                        "reason": option.reason,
                        "token_count": len(option.tokens),
                    },
                    confidence="high",
                )
            )
    return findings


def _diagnostic_findings(model: ParsedModel) -> list[Finding]:
    findings: list[Finding] = []
    for diagnostic in model.diagnostics:
        if diagnostic.code == "SG011":
            findings.append(_unterminated_comment_finding(diagnostic))
        elif diagnostic.code == "SG014":
            findings.append(_unsupported_card_finding(model, diagnostic))
        else:
            findings.append(_parser_recovery_finding(diagnostic))
    return findings


def _unterminated_comment_finding(diagnostic: ParserDiagnostic) -> Finding:
    return _finding(
        rule_id="SG011",
        severity="ERROR",
        title="Unterminated block comment",
        message=diagnostic.message,
        location=diagnostic.location,
        object_type="comment",
        object_name=None,
        evidence={"opening_line": diagnostic.location.line_start},
        confidence="high",
    )


def _unsupported_card_finding(
    model: ParsedModel,
    diagnostic: ParserDiagnostic,
) -> Finding:
    unknown = _matching_unknown_card(model.unknown_cards, diagnostic)
    evidence: dict[str, object] = {"keyword": diagnostic.card_keyword}
    if unknown is not None:
        evidence["token_count"] = len(unknown.tokens)
    return _finding(
        rule_id="SG014",
        severity="INFO",
        title="Unsupported card",
        message=diagnostic.message,
        location=diagnostic.location,
        object_type="card",
        object_name=diagnostic.card_keyword,
        evidence=evidence,
        confidence="high",
    )


def _parser_recovery_finding(diagnostic: ParserDiagnostic) -> Finding:
    recoverable = diagnostic.code not in UNRECOVERABLE_PARSER_CODES
    return _finding(
        rule_id="SG015",
        severity=diagnostic.severity,
        title="Parser recovery used",
        message=diagnostic.message,
        location=diagnostic.location,
        object_type="card" if diagnostic.card_keyword else "input",
        object_name=diagnostic.card_keyword,
        evidence={
            "parser_code": diagnostic.code,
            "recoverable": recoverable,
        },
        confidence="high",
    )


def _matching_unknown_card(
    unknown_cards: list[UnknownCard],
    diagnostic: ParserDiagnostic,
) -> UnknownCard | None:
    for card in unknown_cards:
        if (
            card.keyword == diagnostic.card_keyword
            and card.location.file_name == diagnostic.location.file_name
            and card.location.line_start == diagnostic.location.line_start
        ):
            return card
    return None


def _has_unknown_syntax(model: ParsedModel, relevant_keywords: set[str]) -> bool:
    return any(
        card.keyword == "include" or card.keyword in relevant_keywords
        for card in model.unknown_cards
    )


def _scope_confidence(incomplete: bool) -> FindingConfidence:
    return "medium" if incomplete else "high"


def _intersection_terms(cell: Cell) -> list[list[str]]:
    return cell.intersection_terms or [cell.signed_surface_references]


def _location_evidence(location: SourceLocation) -> dict[str, str | int]:
    return {
        "file": location.file_name,
        "line": location.line_start,
        "line_end": location.line_end,
    }


def _finding(
    *,
    rule_id: str,
    severity: DiagnosticSeverity,
    title: str,
    message: str,
    location: SourceLocation | None,
    object_type: str | None,
    object_name: str | None,
    evidence: dict[str, object],
    confidence: FindingConfidence,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,
        title=title,
        message=message,
        file=location.file_name if location else None,
        line=location.line_start if location else None,
        line_end=location.line_end if location else None,
        object_type=object_type,
        object_name=object_name,
        evidence=evidence,
        confidence=confidence,
    )
