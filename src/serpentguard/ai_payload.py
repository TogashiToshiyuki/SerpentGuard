"""Privacy-preserving data contract for the optional AI explanation.

This module performs no network access and does not import the OpenAI SDK.  The
builder copies only explicitly permitted summaries into a versioned model; it
never serializes a ``ParsedModel`` or geometry result wholesale.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from hashlib import sha256
from math import isfinite
from typing import Any, Literal

from pydantic import Field, JsonValue

from serpentguard.geometry import GeometrySamplingResult
from serpentguard.models import (
    AnalysisReport,
    Detector,
    DiagnosticSeverity,
    Finding,
    FindingConfidence,
    ParsedModel,
    SerpentGuardModel,
)

AI_PAYLOAD_SCHEMA_VERSION = "1.0"
MAX_ANALYSIS_PURPOSE_LENGTH = 500
MAX_FINDINGS = 100
MAX_DETECTORS = 50
MAX_OBJECT_NAME_LENGTH = 96
MAX_MESSAGE_LENGTH = 600
MAX_LIMITATIONS = 20
MAX_EVIDENCE_ITEMS = 30
MAX_EVIDENCE_SEQUENCE_ITEMS = 20
MAX_EVIDENCE_DEPTH = 4

_REDACTED_PATH = "[redacted absolute path]"
_REDACTED_SECRET = "[redacted secret]"
_OMITTED_SOURCE = "[omitted possible Serpent input]"
_OMITTED_VALUE = "[omitted unsupported value]"

_WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/]")
_WINDOWS_UNC_PATH = re.compile(r"(?<![\\])\\\\[^\\/\r\n]+[\\/]")
_POSIX_ABSOLUTE_PATH = re.compile(r"(?:^|[\s(\"'=])/(?!/)[^\s\"'<>]+")
_SECRET_PATTERNS = (
    re.compile(r"(?i)\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{12,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(
        r"(?i)\b(?:OPENAI_API_KEY|API_KEY|ACCESS_TOKEN|AUTH_TOKEN|PASSWORD|SECRET)"
        r"\s*[:=]\s*[^\s,;]+"
    ),
)
_BLOCK_COMMENT = re.compile(r"/\*.*?(?:\*/|$)", re.DOTALL)
_PERCENT_COMMENT = re.compile(r"(?m)%.*$")
_SERPENT_CARD_LINE = re.compile(
    r"(?im)^\s*(?:"
    r"surf\s+\S+\s+\S+|"
    r"cell\s+\S+\s+\S+\s+\S+|"
    r"mat\s+\S+\s+(?:sum|[-+]?(?:\d|\.\d))|"
    r"ene\s+\S+\s+[123]\b|"
    r"det\s+\S+(?:\s|$)|"
    r"pbed\s+\S+\s+\S+|"
    r"include\s+\S+"
    r")"
)
_SAFE_EVIDENCE_KEY = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_PROHIBITED_FIELD_NAMES = frozenset(
    {
        "raw_text",
        "raw_input",
        "input_text",
        "source_text",
        "comment",
        "comments",
        "composition",
        "material_composition",
        "api_key",
        "openai_api_key",
        "access_token",
        "auth_token",
        "authorization",
        "password",
        "secret",
    }
)
_PROHIBITED_FIELD_PREFIXES = (
    "raw_text",
    "raw_input",
    "input_text",
    "source_text",
    "comment",
    "composition",
    "material_composition",
    "api_key",
    "openai_api_key",
    "access_token",
    "auth_token",
    "authorization",
    "password",
    "secret",
    "client_secret",
)


class PayloadPrivacyError(ValueError):
    """Raised when a payload cannot satisfy the local privacy contract."""


class AIObjectCounts(SerpentGuardModel):
    """Allowed aggregate counts; no object definition is included."""

    surfaces: int = Field(ge=0)
    cells: int = Field(ge=0)
    materials: int = Field(ge=0)
    energy_grids: int = Field(ge=0)
    detectors: int = Field(ge=0)
    unknown_cards: int = Field(ge=0)
    parser_diagnostics: int = Field(ge=0)


class AIFindingSummary(SerpentGuardModel):
    """One selected deterministic finding with sanitized structured evidence."""

    rule_id: str = Field(max_length=32)
    severity: DiagnosticSeverity
    title: str = Field(max_length=160)
    message: str = Field(max_length=MAX_MESSAGE_LENGTH)
    source_file: str | None = Field(default=None, max_length=128)
    line: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    object_type: str | None = Field(default=None, max_length=64)
    object_name: str | None = Field(default=None, max_length=MAX_OBJECT_NAME_LENGTH)
    evidence: dict[str, JsonValue] = Field(default_factory=dict)
    confidence: FindingConfidence


class AIFindingSelection(SerpentGuardModel):
    """Bounded list of the findings selected in the local interface."""

    selected_count: int = Field(ge=0)
    included_count: int = Field(ge=0)
    omitted_count: int = Field(ge=0)
    items: list[AIFindingSummary] = Field(default_factory=list, max_length=MAX_FINDINGS)


class AIGeometryBounds(SerpentGuardModel):
    """User-confirmed XY sampling bounds."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float


class AIGeometryStatistics(SerpentGuardModel):
    """Aggregate geometry statistics without grids, coordinates, or cell names."""

    selected_universe: str = Field(max_length=MAX_OBJECT_NAME_LENGTH)
    bounds: AIGeometryBounds
    z_coordinate: float
    resolution: int = Field(ge=1)
    total_points: int = Field(ge=0)
    overlap_candidates: int = Field(ge=0)
    undefined_candidates: int = Field(ge=0)
    normal_points: int = Field(ge=0)
    incomplete_points: int = Field(ge=0)
    boundary_indeterminate_points: int = Field(ge=0)
    coverage_complete: bool
    undefined_detection_enabled: bool
    supported_cell_count: int = Field(ge=0)
    excluded_cell_count: int = Field(ge=0)


class AIDetectorAxisMetadata(SerpentGuardModel):
    """One supported Cartesian detector binning axis."""

    axis: Literal["x", "y", "z"]
    minimum: float
    maximum: float
    bin_count: int


class AIDetectorMetadata(SerpentGuardModel):
    """Limited detector metadata without raw cards or response definitions."""

    name: str = Field(max_length=MAX_OBJECT_NAME_LENGTH)
    particle: Literal["n", "p", "g"] | None = None
    energy_grid_references: list[str] = Field(default_factory=list, max_length=8)
    mesh_axes: list[AIDetectorAxisMetadata] = Field(default_factory=list, max_length=3)
    unsupported_option_names: list[str] = Field(default_factory=list, max_length=16)


class AIDetectorMetadataSummary(SerpentGuardModel):
    """Bounded detector list and truncation metadata."""

    total_count: int = Field(ge=0)
    included_count: int = Field(ge=0)
    omitted_count: int = Field(ge=0)
    items: list[AIDetectorMetadata] = Field(
        default_factory=list, max_length=MAX_DETECTORS
    )


class AIReviewPayload(SerpentGuardModel):
    """Version 1 privacy-preserving contract for an optional AI explanation."""

    schema_version: Literal["1.0"] = AI_PAYLOAD_SCHEMA_VERSION
    analysis_purpose: str = Field(max_length=MAX_ANALYSIS_PURPOSE_LENGTH)
    object_counts: AIObjectCounts
    findings: AIFindingSelection
    geometry_statistics: AIGeometryStatistics | None = None
    detector_metadata: AIDetectorMetadataSummary
    limitations: list[str] = Field(default_factory=list, max_length=MAX_LIMITATIONS)


def build_ai_review_payload(
    *,
    analysis_purpose: str,
    report: AnalysisReport,
    parsed_model: ParsedModel,
    selected_findings: Sequence[Finding] | None = None,
    geometry_result: GeometrySamplingResult | None = None,
) -> AIReviewPayload:
    """Build and audit the only JSON contract eligible for AI review.

    ``ParsedModel`` and ``GeometrySamplingResult`` are read only through explicit
    allowlists.  Raw cards, comments, material compositions, category grids,
    representative coordinates, absolute backing paths, and secrets are never copied.
    """
    selected = list(report.findings if selected_findings is None else selected_findings)
    included_findings = selected[:MAX_FINDINGS]
    finding_items = [_finding_summary(finding) for finding in included_findings]

    detector_items = [
        _detector_metadata(detector)
        for detector in parsed_model.detectors[:MAX_DETECTORS]
    ]
    limitations = [
        sanitized
        for limitation in report.limitations[:MAX_LIMITATIONS]
        if (sanitized := sanitize_text(limitation, max_length=MAX_MESSAGE_LENGTH))
    ]
    if len(selected) > MAX_FINDINGS and len(limitations) < MAX_LIMITATIONS:
        omitted_findings = len(selected) - MAX_FINDINGS
        limitations.append(
            f"AI payload finding limit applied: {omitted_findings} selected findings "
            "omitted."
        )
    if (
        len(parsed_model.detectors) > MAX_DETECTORS
        and len(limitations) < MAX_LIMITATIONS
    ):
        limitations.append(
            f"AI payload detector limit applied: "
            f"{len(parsed_model.detectors) - MAX_DETECTORS} detectors omitted."
        )

    payload = AIReviewPayload(
        analysis_purpose=sanitize_analysis_purpose(analysis_purpose),
        object_counts=_object_counts(report),
        findings=AIFindingSelection(
            selected_count=len(selected),
            included_count=len(finding_items),
            omitted_count=len(selected) - len(finding_items),
            items=finding_items,
        ),
        geometry_statistics=(
            _geometry_statistics(geometry_result)
            if geometry_result is not None
            else None
        ),
        detector_metadata=AIDetectorMetadataSummary(
            total_count=len(parsed_model.detectors),
            included_count=len(detector_items),
            omitted_count=len(parsed_model.detectors) - len(detector_items),
            items=detector_items,
        ),
        limitations=limitations,
    )
    assert_payload_privacy(payload)
    return payload


def sanitize_analysis_purpose(value: str) -> str:
    """Remove source-like/comment text before retaining a short purpose summary."""
    without_comments = _remove_comment_text(value)
    if _looks_like_serpent_input(without_comments):
        return _OMITTED_SOURCE
    return sanitize_text(
        without_comments,
        max_length=MAX_ANALYSIS_PURPOSE_LENGTH,
        remove_comments=False,
    )


def sanitize_text(
    value: str,
    *,
    max_length: int,
    remove_comments: bool = True,
) -> str:
    """Sanitize untrusted text conservatively and bound its serialized length."""
    text = _remove_comment_text(value) if remove_comments else value
    if _looks_like_serpent_input(text):
        text = _OMITTED_SOURCE

    safe_lines: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if _contains_absolute_path(line):
            safe_lines.append(_REDACTED_PATH)
        elif _contains_secret(line):
            safe_lines.append(_REDACTED_SECRET)
        else:
            safe_lines.append(line)
    collapsed = " ".join(" ".join(safe_lines).split())
    return _truncate(collapsed, max_length)


def sanitize_source_name(value: str | None) -> str | None:
    """Reduce a source location to a sanitized leaf name, never a local path."""
    if value is None:
        return None
    stripped = value.strip()
    if stripped.startswith("<") and stripped.endswith(">"):
        return _truncate(stripped, 128)
    normalized = stripped.replace("\\", "/").rstrip("/")
    leaf = normalized.rsplit("/", maxsplit=1)[-1]
    return sanitize_text(leaf, max_length=128) or None


def sanitize_object_name(value: str | None) -> str | None:
    """Sanitize and deterministically truncate a user-defined object name."""
    if value is None:
        return None
    return sanitize_text(value, max_length=MAX_OBJECT_NAME_LENGTH) or None


def payload_fingerprint(payload: AIReviewPayload) -> str:
    """Return a stable digest used to bind UI consent to the visible JSON."""
    serialized = payload.model_dump_json(exclude_none=False)
    return sha256(serialized.encode("utf-8")).hexdigest()


def assert_payload_privacy(payload: AIReviewPayload) -> None:
    """Apply a defense-in-depth audit to the fully constructed payload."""
    _audit_value(payload.model_dump(mode="json"), path="payload")


def _object_counts(report: AnalysisReport) -> AIObjectCounts:
    summary = report.model_summary
    return AIObjectCounts(
        surfaces=summary.get("surfaces", 0),
        cells=summary.get("cells", 0),
        materials=summary.get("materials", 0),
        energy_grids=summary.get("energy_grids", 0),
        detectors=summary.get("detectors", 0),
        unknown_cards=summary.get("unknown_cards", 0),
        parser_diagnostics=summary.get("parser_diagnostics", 0),
    )


def _finding_summary(finding: Finding) -> AIFindingSummary:
    title = sanitize_text(finding.title, max_length=160) or "[omitted]"
    message = (
        sanitize_text(finding.message, max_length=MAX_MESSAGE_LENGTH) or "[omitted]"
    )
    evidence = _sanitize_evidence(finding.evidence)
    return AIFindingSummary(
        rule_id=sanitize_text(finding.rule_id, max_length=32),
        severity=finding.severity,
        title=title,
        message=message,
        source_file=sanitize_source_name(finding.file),
        line=finding.line,
        line_end=finding.line_end,
        object_type=(
            sanitize_text(finding.object_type, max_length=64)
            if finding.object_type is not None
            else None
        ),
        object_name=sanitize_object_name(finding.object_name),
        evidence=evidence,
        confidence=finding.confidence,
    )


def _geometry_statistics(result: GeometrySamplingResult) -> AIGeometryStatistics:
    config = result.config
    return AIGeometryStatistics(
        selected_universe=sanitize_object_name(result.selected_universe) or "[omitted]",
        bounds=AIGeometryBounds(
            xmin=config.xmin,
            xmax=config.xmax,
            ymin=config.ymin,
            ymax=config.ymax,
        ),
        z_coordinate=config.z,
        resolution=config.resolution,
        total_points=result.total_points,
        overlap_candidates=result.overlap_count,
        undefined_candidates=result.undefined_count,
        normal_points=result.normal_count,
        incomplete_points=result.incomplete_count,
        boundary_indeterminate_points=result.boundary_indeterminate_count,
        coverage_complete=result.coverage_complete,
        undefined_detection_enabled=result.undefined_detection_enabled,
        supported_cell_count=result.supported_cell_count,
        excluded_cell_count=result.excluded_cell_count,
    )


def _detector_metadata(detector: Detector) -> AIDetectorMetadata:
    return AIDetectorMetadata(
        name=sanitize_object_name(detector.name) or "[omitted]",
        particle=detector.particle,
        energy_grid_references=[
            sanitize_object_name(reference.name) or "[omitted]"
            for reference in detector.energy_grid_references[:8]
        ],
        mesh_axes=[
            AIDetectorAxisMetadata(
                axis=axis.axis,
                minimum=axis.minimum,
                maximum=axis.maximum,
                bin_count=axis.bin_count,
            )
            for axis in detector.mesh_axes[:3]
        ],
        unsupported_option_names=[
            sanitize_object_name(option.keyword) or "[omitted]"
            for option in detector.unsupported_options[:16]
        ],
    )


def _sanitize_evidence(evidence: Mapping[str, Any]) -> dict[str, JsonValue]:
    sanitized: dict[str, JsonValue] = {}
    for key, value in list(evidence.items())[:MAX_EVIDENCE_ITEMS]:
        if not isinstance(key, str) or not _SAFE_EVIDENCE_KEY.fullmatch(key):
            continue
        if _is_prohibited_field_name(key):
            continue
        sanitized[key] = _sanitize_json_value(value, depth=0)
    return sanitized


def _sanitize_json_value(value: Any, *, depth: int) -> JsonValue:
    if depth >= MAX_EVIDENCE_DEPTH:
        return _OMITTED_VALUE
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if isfinite(value) else _OMITTED_VALUE
    if isinstance(value, str):
        return sanitize_text(value, max_length=MAX_MESSAGE_LENGTH)
    if isinstance(value, Mapping):
        nested: dict[str, JsonValue] = {}
        for key, item in list(value.items())[:MAX_EVIDENCE_ITEMS]:
            if not isinstance(key, str) or not _SAFE_EVIDENCE_KEY.fullmatch(key):
                continue
            if _is_prohibited_field_name(key):
                continue
            nested[key] = _sanitize_json_value(item, depth=depth + 1)
        return nested
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            _sanitize_json_value(item, depth=depth + 1)
            for item in list(value)[:MAX_EVIDENCE_SEQUENCE_ITEMS]
        ]
    return _OMITTED_VALUE


def _remove_comment_text(value: str) -> str:
    without_blocks = _BLOCK_COMMENT.sub("", value)
    return _PERCENT_COMMENT.sub("", without_blocks)


def _looks_like_serpent_input(value: str) -> bool:
    return _SERPENT_CARD_LINE.search(value) is not None


def _contains_absolute_path(value: str) -> bool:
    return any(
        pattern.search(value) is not None
        for pattern in (
            _WINDOWS_ABSOLUTE_PATH,
            _WINDOWS_UNC_PATH,
            _POSIX_ABSOLUTE_PATH,
        )
    )


def _contains_secret(value: str) -> bool:
    return any(pattern.search(value) is not None for pattern in _SECRET_PATTERNS)


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _is_prohibited_field_name(value: str) -> bool:
    normalized = _normalized_key(value)
    return normalized in _PROHIBITED_FIELD_NAMES or normalized.startswith(
        _PROHIBITED_FIELD_PREFIXES
    )


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1] + "…"


def _audit_value(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _is_prohibited_field_name(str(key)):
                raise PayloadPrivacyError(f"Prohibited field present at {path}.{key}")
            _audit_value(item, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _audit_value(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        if _contains_absolute_path(value):
            raise PayloadPrivacyError(f"Absolute path present at {path}")
        if _contains_secret(value):
            raise PayloadPrivacyError(f"Secret-like value present at {path}")
        if _looks_like_serpent_input(value):
            raise PayloadPrivacyError(f"Serpent source-like text present at {path}")
