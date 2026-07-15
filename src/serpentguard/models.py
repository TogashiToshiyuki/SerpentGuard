"""Structured results produced by the limited SerpentGuard parser."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SerpentGuardModel(BaseModel):
    """Strict base class for structured SerpentGuard models."""

    model_config = ConfigDict(extra="forbid")


class SourceLocation(SerpentGuardModel):
    """Inclusive source span for an input object or diagnostic."""

    file_name: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_line_order(self) -> Self:
        """Reject inverted source spans."""
        if self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


DiagnosticSeverity = Literal["ERROR", "WARNING", "REVIEW", "INFO"]


class ParserDiagnostic(SerpentGuardModel):
    """A non-semantic issue or parser limitation tied to source text."""

    code: str
    severity: DiagnosticSeverity
    message: str
    location: SourceLocation
    card_keyword: str | None = None


class Surface(SerpentGuardModel):
    """A surface in the first-milestone supported subset."""

    name: str
    surface_type: str
    parameters: list[float]
    location: SourceLocation
    raw_text: str


class Cell(SerpentGuardModel):
    """A cell with shallow union-separated intersection terms."""

    name: str
    universe: str
    material: str | None
    fill_type: Literal["material", "void", "outside"]
    region_expression: str
    signed_surface_references: list[str]
    referenced_surfaces: list[str]
    intersection_terms: list[list[str]] = Field(default_factory=list)
    location: SourceLocation
    raw_text: str


class MaterialComponent(SerpentGuardModel):
    """One ZAID/fraction pair in a material composition."""

    zaid: str
    fraction: float


class Material(SerpentGuardModel):
    """A material using the limited density and composition syntax."""

    name: str
    density: float | Literal["sum"]
    rgb: tuple[int, int, int] | None = None
    composition: list[MaterialComponent]
    location: SourceLocation
    raw_text: str


class UnknownCard(SerpentGuardModel):
    """An unsupported or malformed card retained without interpretation."""

    keyword: str
    tokens: list[str]
    location: SourceLocation
    raw_text: str


class ParsedModel(SerpentGuardModel):
    """Complete syntactic parse result for one or more tracked sources."""

    surfaces: list[Surface] = Field(default_factory=list)
    cells: list[Cell] = Field(default_factory=list)
    materials: list[Material] = Field(default_factory=list)
    unknown_cards: list[UnknownCard] = Field(default_factory=list)
    diagnostics: list[ParserDiagnostic] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)


FindingConfidence = Literal["high", "medium", "low"]


class Finding(SerpentGuardModel):
    """One deterministic static-analysis result suitable for text or JSON output."""

    rule_id: str
    severity: DiagnosticSeverity
    title: str
    message: str
    file: str | None = None
    line: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    object_type: str | None = None
    object_name: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: FindingConfidence


class AnalysisReport(SerpentGuardModel):
    """Serializable result of parsing and deterministic static analysis."""

    model_summary: dict[str, int]
    findings: list[Finding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
