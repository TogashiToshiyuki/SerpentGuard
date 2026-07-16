"""Pragmatic, non-semantic parser for SerpentGuard's first syntax subset."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from serpentguard.models import (
    Cell,
    Detector,
    DetectorEnergyGridReference,
    DetectorMeshAxis,
    DetectorUnsupportedOption,
    EnergyGrid,
    Material,
    MaterialComponent,
    ParsedModel,
    ParserDiagnostic,
    SourceLocation,
    Surface,
    UnknownCard,
)
from serpentguard.preprocessor import PreprocessedSource, preprocess

# This list is intentionally frozen for the first milestone. It gives the line-oriented
# scanner reliable card boundaries without implying support for these card families.
KNOWN_CARD_KEYWORDS = frozenset(
    {
        "branch",
        "casematrix",
        "cell",
        "coef",
        "datamesh",
        "dep",
        "det",
        "div",
        "dtrans",
        "ene",
        "ftrans",
        "fun",
        "gplot",
        "hisv",
        "ifc",
        "include",
        "lat",
        "mat",
        "mesh",
        "mflow",
        "mix",
        "mplot",
        "nest",
        "particle",
        "pbed",
        "phb",
        "pin",
        "plot",
        "rep",
        "sample",
        "sens",
        "set",
        "solid",
        "src",
        "strans",
        "surf",
        "therm",
        "thermstoch",
        "tme",
        "trans",
        "transa",
        "transb",
        "transv",
        "umsh",
        "utrans",
        "voro",
        "wwgen",
        "wwin",
    }
)

_SUPPORTED_SURFACE_TYPES = frozenset({"cyl", "sqc"})
_UNSUPPORTED_REGION_CHARACTERS = frozenset("()#")
_ZAID_PATTERN = re.compile(r"^\d+\.[A-Za-z0-9]+$")
_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_DETECTOR_PARTICLES = frozenset({"n", "p", "g"})
_DETECTOR_OPTION_KEYWORDS = frozenset(
    {
        "da",
        "dc",
        "de",
        "df",
        "dfet",
        "dfl",
        "dh",
        "dhis",
        "di",
        "dl",
        "dm",
        "dmesh",
        "dn",
        "dphb",
        "dr",
        "ds",
        "dt",
        "dtl",
        "du",
        "dumsh",
        "dv",
        "dx",
        "dy",
        "dz",
    }
)
_SUPPORTED_DETECTOR_OPTIONS = frozenset({"de", "dx", "dy", "dz"})


@dataclass(frozen=True, slots=True)
class _CardSpan:
    """Internal source span bounded by known card keywords."""

    keyword: str
    start_index: int
    end_index: int
    meaningful_indices: tuple[int, ...]
    cleaned_lines: tuple[str, ...]
    raw_text: str


def parse_file(path: str | Path) -> ParsedModel:
    """Read and parse one local UTF-8 file without opening referenced include files."""
    input_path = Path(path)
    file_name = str(input_path)
    try:
        data = input_path.read_bytes()
    except OSError:
        return _failed_file_result(
            file_name,
            code="PARSER_IO",
            message="The local input file could not be read.",
        )
    return parse_bytes(data, file_name=file_name)


def parse_bytes(data: bytes, *, file_name: str = "<memory>") -> ParsedModel:
    """Decode and parse one in-memory UTF-8 input, such as a local upload."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _failed_file_result(
            file_name,
            code="PARSER_ENCODING",
            message="The local input file is not valid UTF-8.",
        )
    return parse_text(text, file_name=file_name)


def parse_text(text: str, *, file_name: str = "<memory>") -> ParsedModel:
    """Parse the documented first-milestone subset from an in-memory string."""
    source = preprocess(text, file_name=file_name)
    result = ParsedModel(
        source_files=[file_name],
        diagnostics=list(source.diagnostics),
    )

    for span in _iter_card_spans(source):
        if span.keyword == "surf":
            _parse_surface(span, source, result)
        elif span.keyword == "cell":
            _parse_cell(span, source, result)
        elif span.keyword == "mat":
            _parse_material(span, source, result)
        elif span.keyword == "ene":
            _parse_energy_grid(span, source, result)
        elif span.keyword == "det":
            _parse_detector(span, source, result)
        else:
            _retain_unknown(span, source, result)

    return result


def _failed_file_result(file_name: str, *, code: str, message: str) -> ParsedModel:
    location = SourceLocation(file_name=file_name, line_start=1, line_end=1)
    return ParsedModel(
        source_files=[file_name],
        diagnostics=[
            ParserDiagnostic(
                code=code,
                severity="ERROR",
                message=message,
                location=location,
            )
        ],
    )


def _iter_card_spans(source: PreprocessedSource) -> list[_CardSpan]:
    cleaned_lines = source.text.split("\n")
    original_lines = source.original_text.split("\n")
    spans: list[_CardSpan] = []
    index = 0

    while index < len(cleaned_lines):
        keyword = _first_token(cleaned_lines[index])
        if keyword is None:
            index += 1
            continue

        normalized_keyword = keyword.lower()
        if normalized_keyword in KNOWN_CARD_KEYWORDS:
            end_index = index + 1
            while end_index < len(cleaned_lines):
                next_token = _first_token(cleaned_lines[end_index])
                if next_token is not None and next_token.lower() in KNOWN_CARD_KEYWORDS:
                    break
                end_index += 1
        else:
            # An unrecognized first token has no trustworthy continuation grammar.
            end_index = index + 1

        meaningful_indices = tuple(
            line_index
            for line_index in range(index, end_index)
            if cleaned_lines[line_index].strip()
        )
        last_index = meaningful_indices[-1]
        spans.append(
            _CardSpan(
                keyword=normalized_keyword,
                start_index=index,
                end_index=end_index,
                meaningful_indices=meaningful_indices,
                cleaned_lines=tuple(cleaned_lines[index : last_index + 1]),
                raw_text="\n".join(original_lines[index : last_index + 1]),
            )
        )
        index = end_index

    return spans


def _parse_surface(
    span: _CardSpan,
    source: PreprocessedSource,
    result: ParsedModel,
) -> None:
    tokens = _flatten_tokens(span)
    if len(span.meaningful_indices) != 1 or len(tokens) != 6:
        _retain_malformed(
            span,
            source,
            result,
            code="PARSER001",
            message=(
                "A supported surf card must be one line with a name, type, "
                "and three parameters."
            ),
        )
        return

    surface_type = tokens[2].lower()
    if surface_type not in _SUPPORTED_SURFACE_TYPES:
        _retain_unknown(span, source, result)
        return

    parameters = _parse_finite_numbers(tokens[3:])
    if parameters is None:
        _retain_malformed(
            span,
            source,
            result,
            code="PARSER001",
            message="A supported surf card contains a malformed numeric parameter.",
        )
        return

    result.surfaces.append(
        Surface(
            name=tokens[1],
            surface_type=surface_type,
            parameters=parameters,
            location=_span_location(span, source),
            raw_text=span.raw_text,
        )
    )


def _parse_cell(
    span: _CardSpan,
    source: PreprocessedSource,
    result: ParsedModel,
) -> None:
    tokens = _flatten_tokens(span)
    if len(span.meaningful_indices) != 1 or len(tokens) < 5:
        _retain_malformed(
            span,
            source,
            result,
            code="PARSER002",
            message=(
                "A supported cell card must be one line with at least one "
                "surface reference."
            ),
        )
        return

    fill_token = tokens[3]
    if fill_token.lower() == "fill":
        _retain_unknown(span, source, result)
        return

    region_tokens = tokens[4:]
    intersection_terms = _parse_intersection_terms(region_tokens)
    if intersection_terms is None:
        _retain_unknown(span, source, result)
        return

    fill_type: Literal["material", "void", "outside"]
    material: str | None
    if fill_token.lower() == "void":
        fill_type = "void"
        material = None
    elif fill_token.lower() == "outside":
        fill_type = "outside"
        material = None
    else:
        fill_type = "material"
        material = fill_token

    signed_references = [
        reference for intersection in intersection_terms for reference in intersection
    ]
    result.cells.append(
        Cell(
            name=tokens[1],
            universe=tokens[2],
            material=material,
            fill_type=fill_type,
            region_expression=" ".join(region_tokens),
            signed_surface_references=signed_references,
            referenced_surfaces=[
                reference.removeprefix("-") for reference in signed_references
            ],
            intersection_terms=intersection_terms,
            location=_span_location(span, source),
            raw_text=span.raw_text,
        )
    )


def _parse_material(
    span: _CardSpan,
    source: PreprocessedSource,
    result: ParsedModel,
) -> None:
    line_tokens = [
        span.cleaned_lines[line_index - span.start_index].split()
        for line_index in span.meaningful_indices
    ]
    header_tokens = line_tokens[0]
    rgb: tuple[int, int, int] | None = None
    if len(header_tokens) == 7 and header_tokens[3].lower() == "rgb":
        rgb_values = _parse_rgb_channels(header_tokens[4:])
        if rgb_values is None:
            _retain_malformed(
                span,
                source,
                result,
                code="PARSER003",
                message=(
                    "A supported mat rgb option requires three integer channels "
                    "between 0 and 255."
                ),
                diagnostic_line_index=span.start_index,
            )
            return
        rgb = rgb_values
    elif len(header_tokens) != 3:
        if len(header_tokens) > 3:
            _retain_unknown(span, source, result)
        else:
            _retain_malformed(
                span,
                source,
                result,
                code="PARSER003",
                message="A supported mat card header requires a name and density.",
                diagnostic_line_index=span.start_index,
            )
        return

    density: float | Literal["sum"]
    if header_tokens[2].lower() == "sum":
        density = "sum"
    else:
        parsed_density = _parse_finite_numbers([header_tokens[2]])
        if parsed_density is None:
            _retain_malformed(
                span,
                source,
                result,
                code="PARSER003",
                message="A supported mat card contains a malformed density.",
                diagnostic_line_index=span.start_index,
            )
            return
        density = parsed_density[0]

    composition: list[MaterialComponent] = []
    for component_offset, component_tokens in enumerate(line_tokens[1:], start=1):
        component_line_index = span.meaningful_indices[component_offset]
        if (
            len(component_tokens) != 2
            or _ZAID_PATTERN.fullmatch(component_tokens[0]) is None
        ):
            _retain_malformed(
                span,
                source,
                result,
                code="PARSER003",
                message=(
                    "A supported mat composition line requires one ZAID and "
                    "one fraction."
                ),
                diagnostic_line_index=component_line_index,
            )
            return
        fraction = _parse_finite_numbers([component_tokens[1]])
        if fraction is None:
            _retain_malformed(
                span,
                source,
                result,
                code="PARSER003",
                message=(
                    "A supported mat card contains a malformed composition fraction."
                ),
                diagnostic_line_index=component_line_index,
            )
            return
        composition.append(
            MaterialComponent(zaid=component_tokens[0], fraction=fraction[0])
        )

    if not composition:
        _retain_malformed(
            span,
            source,
            result,
            code="PARSER003",
            message="A supported mat card requires at least one ZAID/fraction pair.",
            diagnostic_line_index=span.start_index,
        )
        return

    result.materials.append(
        Material(
            name=header_tokens[1],
            density=density,
            rgb=rgb,
            composition=composition,
            location=_span_location(span, source),
            raw_text=span.raw_text,
        )
    )


def _parse_energy_grid(
    span: _CardSpan,
    source: PreprocessedSource,
    result: ParsedModel,
) -> None:
    tokens = _flatten_tokens(span)
    if len(tokens) < 3:
        _retain_malformed(
            span,
            source,
            result,
            code="PARSER004",
            message="A supported ene card requires a name and grid type.",
        )
        return

    grid_type = _parse_integer(tokens[2])
    if grid_type is None:
        _retain_malformed(
            span,
            source,
            result,
            code="PARSER004",
            message="A supported ene card contains a malformed grid type.",
        )
        return
    if grid_type not in {1, 2, 3}:
        _retain_unknown(span, source, result)
        return

    if grid_type == 1:
        boundaries = _parse_finite_numbers(tokens[3:])
        if boundaries is None:
            _retain_malformed(
                span,
                source,
                result,
                code="PARSER004",
                message="A supported type-1 ene card has a malformed boundary.",
            )
            return
        minimum = min(boundaries) if len(boundaries) >= 2 else None
        maximum = max(boundaries) if len(boundaries) >= 2 else None
        result.energy_grids.append(
            EnergyGrid(
                name=tokens[1],
                grid_type=1,
                bin_count=max(len(boundaries) - 1, 0),
                boundaries=boundaries,
                minimum=minimum,
                maximum=maximum,
                location=_span_location(span, source),
                raw_text=span.raw_text,
            )
        )
        return

    if len(tokens) != 6:
        _retain_malformed(
            span,
            source,
            result,
            code="PARSER004",
            message=(
                "A supported type-2 or type-3 ene card requires a bin count, "
                "minimum, and maximum."
            ),
        )
        return
    bin_count = _parse_integer(tokens[3])
    limits = _parse_finite_numbers(tokens[4:])
    if bin_count is None or limits is None:
        _retain_malformed(
            span,
            source,
            result,
            code="PARSER004",
            message="A supported ene card contains a malformed numeric parameter.",
        )
        return
    result.energy_grids.append(
        EnergyGrid(
            name=tokens[1],
            grid_type=grid_type,
            bin_count=bin_count,
            minimum=limits[0],
            maximum=limits[1],
            location=_span_location(span, source),
            raw_text=span.raw_text,
        )
    )


def _parse_detector(
    span: _CardSpan,
    source: PreprocessedSource,
    result: ParsedModel,
) -> None:
    stream = _span_token_stream(span)
    if len(stream) < 2:
        _retain_malformed(
            span,
            source,
            result,
            code="PARSER005",
            message="A supported det card requires a detector name.",
        )
        return

    name = stream[1][0]
    cursor = 2
    particle: Literal["n", "p", "g"] | None = None
    if cursor < len(stream) and stream[cursor][0].lower() in _DETECTOR_PARTICLES:
        particle = stream[cursor][0].lower()  # type: ignore[assignment]
        cursor += 1

    references: list[DetectorEnergyGridReference] = []
    axes: list[DetectorMeshAxis] = []
    unsupported: list[DetectorUnsupportedOption] = []
    seen_selected: set[str] = set()
    while cursor < len(stream):
        end = cursor + 1
        while (
            end < len(stream)
            and stream[end][0].lower() not in _DETECTOR_OPTION_KEYWORDS
        ):
            end += 1
        option_tokens = [token for token, _ in stream[cursor:end]]
        keyword = option_tokens[0].lower()
        location = _line_location(stream[cursor][1], source)
        cursor = end

        if keyword not in _SUPPORTED_DETECTOR_OPTIONS:
            unsupported.append(
                DetectorUnsupportedOption(
                    keyword=keyword,
                    tokens=option_tokens,
                    reason="unsupported",
                    location=location,
                )
            )
            continue
        if keyword in seen_selected:
            unsupported.append(
                DetectorUnsupportedOption(
                    keyword=keyword,
                    tokens=option_tokens,
                    reason="duplicate",
                    location=location,
                )
            )
            continue
        seen_selected.add(keyword)

        if keyword == "de" and len(option_tokens) == 2:
            references.append(
                DetectorEnergyGridReference(
                    name=option_tokens[1],
                    location=location,
                )
            )
            continue
        if keyword in {"dx", "dy", "dz"} and len(option_tokens) == 4:
            limits = _parse_finite_numbers(option_tokens[1:3])
            bin_count = _parse_integer(option_tokens[3])
            if limits is not None and bin_count is not None:
                axes.append(
                    DetectorMeshAxis(
                        axis=keyword[1],  # type: ignore[arg-type]
                        minimum=limits[0],
                        maximum=limits[1],
                        bin_count=bin_count,
                        location=location,
                    )
                )
                continue

        unsupported.append(
            DetectorUnsupportedOption(
                keyword=keyword,
                tokens=option_tokens,
                reason="malformed",
                location=location,
            )
        )
        result.diagnostics.append(
            ParserDiagnostic(
                code="PARSER005",
                severity="ERROR",
                message=(
                    f"Detector option '{keyword}' is malformed for the supported "
                    "limited form."
                ),
                location=location,
                card_keyword="det",
            )
        )

    result.detectors.append(
        Detector(
            name=name,
            particle=particle,
            energy_grid_references=references,
            mesh_axes=axes,
            unsupported_options=unsupported,
            location=_span_location(span, source),
            raw_text=span.raw_text,
        )
    )


def _parse_intersection_terms(region_tokens: list[str]) -> list[list[str]] | None:
    expression = " ".join(region_tokens)
    if any(character in expression for character in _UNSUPPORTED_REGION_CHARACTERS):
        return None

    intersections: list[list[str]] = []
    for raw_intersection in expression.split(":"):
        references = raw_intersection.split()
        if not references:
            return None
        for reference in references:
            if reference == "-" or reference.startswith("+"):
                return None
            name = reference.removeprefix("-")
            if not name or name.startswith("-"):
                return None
        intersections.append(references)
    return intersections


def _parse_finite_numbers(tokens: list[str]) -> list[float] | None:
    try:
        values = [float(token) for token in tokens]
    except ValueError:
        return None
    if not all(math.isfinite(value) for value in values):
        return None
    return values


def _parse_integer(token: str) -> int | None:
    if _INTEGER_PATTERN.fullmatch(token) is None:
        return None
    return int(token)


def _parse_rgb_channels(tokens: list[str]) -> tuple[int, int, int] | None:
    """Parse the documented integer RGB triplet without accepting float aliases."""
    if len(tokens) != 3 or any(re.fullmatch(r"\d+", token) is None for token in tokens):
        return None
    values = tuple(int(token) for token in tokens)
    if any(value > 255 for value in values):
        return None
    return values  # type: ignore[return-value]


def _retain_malformed(
    span: _CardSpan,
    source: PreprocessedSource,
    result: ParsedModel,
    *,
    code: str,
    message: str,
    diagnostic_line_index: int | None = None,
) -> None:
    _append_unknown(span, source, result)
    location = _span_location(span, source)
    if diagnostic_line_index is not None:
        location = _line_location(diagnostic_line_index, source)
    result.diagnostics.append(
        ParserDiagnostic(
            code=code,
            severity="ERROR",
            message=message,
            location=location,
            card_keyword=span.keyword,
        )
    )


def _retain_unknown(
    span: _CardSpan,
    source: PreprocessedSource,
    result: ParsedModel,
) -> None:
    _append_unknown(span, source, result)
    message = (
        "Card is outside the implemented parser subset and was retained "
        "without interpretation."
    )
    if span.keyword == "include":
        message = "Include card was retained but its referenced path was not opened."
    result.diagnostics.append(
        ParserDiagnostic(
            code="SG014",
            severity="INFO",
            message=message,
            location=_span_location(span, source),
            card_keyword=span.keyword,
        )
    )


def _append_unknown(
    span: _CardSpan,
    source: PreprocessedSource,
    result: ParsedModel,
) -> None:
    result.unknown_cards.append(
        UnknownCard(
            keyword=span.keyword,
            tokens=_flatten_tokens(span),
            location=_span_location(span, source),
            raw_text=span.raw_text,
        )
    )


def _span_location(span: _CardSpan, source: PreprocessedSource) -> SourceLocation:
    return SourceLocation(
        file_name=source.file_name,
        line_start=span.start_index + 1,
        line_end=span.meaningful_indices[-1] + 1,
    )


def _line_location(line_index: int, source: PreprocessedSource) -> SourceLocation:
    line_number = line_index + 1
    return SourceLocation(
        file_name=source.file_name,
        line_start=line_number,
        line_end=line_number,
    )


def _flatten_tokens(span: _CardSpan) -> list[str]:
    return [token for line in span.cleaned_lines for token in line.split()]


def _span_token_stream(span: _CardSpan) -> list[tuple[str, int]]:
    return [
        (token, span.start_index + relative_index)
        for relative_index, line in enumerate(span.cleaned_lines)
        for token in line.split()
    ]


def _first_token(line: str) -> str | None:
    tokens = line.split(maxsplit=1)
    return tokens[0] if tokens else None
