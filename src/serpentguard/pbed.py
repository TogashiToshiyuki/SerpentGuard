"""Typed, incremental reader for the verified five-field PBED subset."""

from __future__ import annotations

import math
from typing import BinaryIO, Literal

from pydantic import BaseModel, ConfigDict, Field

from serpentguard.models import DiagnosticSeverity

DEFAULT_MAX_PBED_FILE_SIZE = 16 * 1024 * 1024
DEFAULT_MAX_PBED_RECORDS = 100_000


class PbedModel(BaseModel):
    """Strict base model for serializable PBED results."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class PbedReadPolicy(PbedModel):
    """Resource limits applied before and during incremental parsing."""

    max_file_size_bytes: int = Field(default=DEFAULT_MAX_PBED_FILE_SIZE, ge=1)
    max_record_count: int = Field(default=DEFAULT_MAX_PBED_RECORDS, ge=1)


class PbedDiagnostic(PbedModel):
    """A sanitized PBED validation result tied to a line or record."""

    rule_id: Literal["SG019", "SG020"]
    code: str
    severity: DiagnosticSeverity
    message: str
    source_name: str
    line: int | None = Field(default=None, ge=1)
    record_number: int | None = Field(default=None, ge=1)


class PbedPlacement(PbedModel):
    """One officially documented spherical PBED placement."""

    x: float
    y: float
    z: float
    radius: float = Field(gt=0.0)
    universe: str = Field(min_length=1)
    record_number: int = Field(ge=1)
    source_line: int = Field(ge=1)


class PbedBoundingBox(PbedModel):
    """Axis-aligned extent of the outer placement spheres, in centimetres."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float


class PbedData(PbedModel):
    """Validated PBED placement data without any retained raw lines."""

    source_name: str
    placements: tuple[PbedPlacement, ...] = ()
    total_record_count: int = Field(ge=0)
    valid_record_count: int = Field(ge=0)
    invalid_record_count: int = Field(ge=0)
    physical_line_count: int = Field(ge=0)
    bounding_box: PbedBoundingBox | None = None
    truncated: bool = False


class PbedParseResult(PbedModel):
    """PBED data and deterministic diagnostics."""

    data: PbedData | None = None
    diagnostics: tuple[PbedDiagnostic, ...] = ()


def parse_pbed_binary(
    stream: BinaryIO,
    *,
    source_name: str,
    size_bytes: int,
    policy: PbedReadPolicy | None = None,
) -> PbedParseResult:
    """Incrementally parse UTF-8 PBED records without retaining raw text."""
    active_policy = policy or PbedReadPolicy()
    if size_bytes > active_policy.max_file_size_bytes:
        return PbedParseResult(
            diagnostics=(
                PbedDiagnostic(
                    rule_id="SG020",
                    code="PBED_FILE_SIZE_LIMIT",
                    severity="ERROR",
                    message=(
                        "The PBED file exceeds the configured byte limit and was not "
                        "read."
                    ),
                    source_name=source_name,
                ),
            )
        )

    placements: list[PbedPlacement] = []
    diagnostics: list[PbedDiagnostic] = []
    total_records = 0
    nonblank_records = 0
    invalid_records = 0
    physical_lines = 0
    streamed_bytes = 0
    truncated = False

    try:
        for physical_lines, raw_bytes in enumerate(stream, start=1):
            streamed_bytes += len(raw_bytes)
            if streamed_bytes > active_policy.max_file_size_bytes:
                diagnostics.append(
                    PbedDiagnostic(
                        rule_id="SG020",
                        code="PBED_FILE_SIZE_LIMIT",
                        severity="ERROR",
                        message=(
                            "The PBED stream exceeded the configured byte limit; "
                            "parsing stopped before the excess line was interpreted."
                        ),
                        source_name=source_name,
                        line=physical_lines,
                    )
                )
                truncated = True
                break
            total_records += 1
            if total_records > active_policy.max_record_count:
                diagnostics.append(
                    PbedDiagnostic(
                        rule_id="SG020",
                        code="PBED_RECORD_LIMIT",
                        severity="ERROR",
                        message=(
                            "The PBED record limit was exceeded; parsing stopped "
                            "before the excess record was interpreted."
                        ),
                        source_name=source_name,
                        line=physical_lines,
                        record_number=total_records,
                    )
                )
                truncated = True
                break
            raw_line = raw_bytes.decode("utf-8", errors="strict")
            stripped = raw_line.strip()
            if not stripped:
                invalid_records += 1
                diagnostics.append(
                    _record_diagnostic(
                        source_name,
                        physical_lines,
                        total_records,
                        code="PBED_BLANK_LINE",
                        message=(
                            "A blank PBED data line is outside the verified record "
                            "subset and was excluded."
                        ),
                    )
                )
                continue

            nonblank_records += 1

            tokens = stripped.split()
            if len(tokens) != 5:
                invalid_records += 1
                diagnostics.append(
                    _record_diagnostic(
                        source_name,
                        physical_lines,
                        total_records,
                        code="PBED_COLUMN_COUNT",
                        message=(
                            "The PBED record does not contain exactly five fields and "
                            "was excluded."
                        ),
                    )
                )
                continue

            values = _parse_coordinates_and_radius(tokens[:4])
            if values is None:
                invalid_records += 1
                diagnostics.append(
                    _record_diagnostic(
                        source_name,
                        physical_lines,
                        total_records,
                        code="PBED_NUMERIC_VALUE",
                        message=(
                            "The PBED record contains a malformed or non-finite "
                            "coordinate/radius and was excluded."
                        ),
                    )
                )
                continue

            x, y, z, radius = values
            if radius <= 0.0:
                invalid_records += 1
                diagnostics.append(
                    _record_diagnostic(
                        source_name,
                        physical_lines,
                        total_records,
                        code="PBED_NON_POSITIVE_RADIUS",
                        message=(
                            "The PBED record has a non-positive outer radius and was "
                            "excluded."
                        ),
                    )
                )
                continue

            placements.append(
                PbedPlacement(
                    x=x,
                    y=y,
                    z=z,
                    radius=radius,
                    universe=tokens[4],
                    record_number=total_records,
                    source_line=physical_lines,
                )
            )
    except UnicodeDecodeError:
        diagnostics.append(
            PbedDiagnostic(
                rule_id="SG019",
                code="PBED_ENCODING",
                severity="ERROR",
                message="The PBED file is not valid UTF-8 and parsing stopped.",
                source_name=source_name,
                line=max(1, physical_lines),
            )
        )
        truncated = True

    if nonblank_records == 0:
        diagnostics.append(
            PbedDiagnostic(
                rule_id="SG019",
                code="PBED_EMPTY",
                severity="ERROR",
                message="The PBED file contains no placement records.",
                source_name=source_name,
            )
        )

    data = PbedData(
        source_name=source_name,
        placements=tuple(placements),
        total_record_count=total_records,
        valid_record_count=len(placements),
        invalid_record_count=invalid_records,
        physical_line_count=physical_lines,
        bounding_box=_bounding_box(placements),
        truncated=truncated,
    )
    return PbedParseResult(data=data, diagnostics=tuple(diagnostics))


def _parse_coordinates_and_radius(tokens: list[str]) -> tuple[float, ...] | None:
    try:
        values = tuple(float(token) for token in tokens)
    except ValueError:
        return None
    return values if all(math.isfinite(value) for value in values) else None


def _record_diagnostic(
    source_name: str,
    line: int,
    record_number: int,
    *,
    code: str,
    message: str,
) -> PbedDiagnostic:
    return PbedDiagnostic(
        rule_id="SG019",
        code=code,
        severity="ERROR",
        message=message,
        source_name=source_name,
        line=line,
        record_number=record_number,
    )


def _bounding_box(placements: list[PbedPlacement]) -> PbedBoundingBox | None:
    if not placements:
        return None
    return PbedBoundingBox(
        xmin=min(item.x - item.radius for item in placements),
        xmax=max(item.x + item.radius for item in placements),
        ymin=min(item.y - item.radius for item in placements),
        ymax=max(item.y + item.radius for item in placements),
        zmin=min(item.z - item.radius for item in placements),
        zmax=max(item.z + item.radius for item in placements),
    )
