"""Pragmatic, non-semantic parser for SerpentGuard's first syntax subset."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from serpentguard.models import (
    Cell,
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


def _first_token(line: str) -> str | None:
    tokens = line.split(maxsplit=1)
    return tokens[0] if tokens else None
