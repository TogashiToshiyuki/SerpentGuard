"""Comment preprocessing that preserves source line positions."""

from __future__ import annotations

from dataclasses import dataclass

from serpentguard.models import ParserDiagnostic, SourceLocation


@dataclass(frozen=True, slots=True)
class PreprocessedSource:
    """Normalized source alongside its comment-stripped representation."""

    file_name: str
    original_text: str
    text: str
    diagnostics: tuple[ParserDiagnostic, ...]


def normalize_newlines(text: str) -> str:
    """Convert CRLF and bare CR newlines to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def preprocess(text: str, *, file_name: str = "<memory>") -> PreprocessedSource:
    """Remove supported comments while retaining every newline and character offset.

    Comment contents are replaced with spaces rather than deleted. This makes source
    locations stable and avoids retaining the full input in any diagnostic message.
    """
    normalized = normalize_newlines(text)
    cleaned = list(normalized)
    diagnostics: list[ParserDiagnostic] = []
    index = 0
    line_number = 1
    block_start_line: int | None = None

    while index < len(normalized):
        character = normalized[index]

        if block_start_line is not None:
            if (
                character == "*"
                and index + 1 < len(normalized)
                and normalized[index + 1] == "/"
            ):
                cleaned[index] = " "
                cleaned[index + 1] = " "
                index += 2
                block_start_line = None
                continue
            if character == "\n":
                line_number += 1
            else:
                cleaned[index] = " "
            index += 1
            continue

        if character == "%":
            while index < len(normalized) and normalized[index] != "\n":
                cleaned[index] = " "
                index += 1
            continue

        if (
            character == "/"
            and index + 1 < len(normalized)
            and normalized[index + 1] == "*"
        ):
            block_start_line = line_number
            cleaned[index] = " "
            cleaned[index + 1] = " "
            index += 2
            continue

        if character == "\n":
            line_number += 1
        index += 1

    if block_start_line is not None:
        diagnostics.append(
            ParserDiagnostic(
                code="SG011",
                severity="ERROR",
                message="Block comment is not terminated before the end of the file.",
                location=SourceLocation(
                    file_name=file_name,
                    line_start=block_start_line,
                    line_end=block_start_line,
                ),
            )
        )

    return PreprocessedSource(
        file_name=file_name,
        original_text=normalized,
        text="".join(cleaned),
        diagnostics=tuple(diagnostics),
    )
