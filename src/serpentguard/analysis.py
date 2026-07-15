"""Deterministic symbol-table checks for the supported parsed model."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TypeVar

from serpentguard.models import (
    AnalysisReport,
    Cell,
    DiagnosticSeverity,
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
DefinitionT = TypeVar("DefinitionT", Surface, Cell, Material)


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """Explicit thresholds for deterministic complexity review."""

    max_region_references: int = 20
    max_union_operators: int = 4

    def __post_init__(self) -> None:
        if self.max_region_references < 1:
            raise ValueError("max_region_references must be at least 1")
        if self.max_union_operators < 0:
            raise ValueError("max_union_operators cannot be negative")


@dataclass(frozen=True, slots=True)
class SymbolTable:
    """All supported definitions grouped by exact, case-preserved name."""

    surfaces: dict[str, list[Surface]]
    cells: dict[str, list[Cell]]
    materials: dict[str, list[Material]]

    @classmethod
    def from_model(cls, model: ParsedModel) -> SymbolTable:
        return cls(
            surfaces=_group_by_name(model.surfaces),
            cells=_group_by_name(model.cells),
            materials=_group_by_name(model.materials),
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
    findings.extend(_undefined_surface_findings(model, symbols))
    findings.extend(_undefined_material_findings(model, symbols))
    findings.extend(_unused_surface_findings(model, symbols))
    findings.extend(_unused_material_findings(model, symbols))
    findings.extend(_contradictory_surface_findings(model))
    findings.extend(_duplicate_condition_findings(model))
    findings.extend(_complexity_findings(model, active_config))
    findings.extend(_diagnostic_findings(model))

    return AnalysisReport(
        model_summary={
            "surfaces": len(model.surfaces),
            "cells": len(model.cells),
            "materials": len(model.materials),
            "unknown_cards": len(model.unknown_cards),
            "parser_diagnostics": len(model.diagnostics),
        },
        findings=findings,
        limitations=[
            "Only the documented parsed surf, cell, and mat subset is analyzed.",
            "Object names are matched exactly with case preserved.",
            "Includes, geometry, detectors, physics, and AI are not analyzed.",
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
    | dict[str, list[Material]],
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
