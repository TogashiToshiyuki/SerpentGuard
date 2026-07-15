"""Sandboxed resolution of explicitly supported local external references."""

from __future__ import annotations

import io
import os
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO, Literal

from pydantic import BaseModel, ConfigDict, Field

from serpentguard.models import DiagnosticSeverity
from serpentguard.pbed import PbedData, PbedReadPolicy, parse_pbed_binary
from serpentguard.preprocessor import preprocess

DEFAULT_MAX_MAIN_FILE_SIZE = 4 * 1024 * 1024
DEFAULT_MAX_BUNDLE_DOCUMENTS = 64
ABSOLUTE_TARGET_MARKER = "<absolute path rejected>"
INVALID_TARGET_MARKER = "<invalid path rejected>"

_PBED_CARD = re.compile(
    r'^\s*pbed\s+(\S+)\s+(\S+)\s+"([^"]+)"(?:\s+(pow))?\s*$',
    flags=re.IGNORECASE,
)
_WINDOWS_INVALID_NAME_CHARACTERS = frozenset('<>:"|?*')
_WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
)

ResolutionMode = Literal["uploaded_bundle", "local_project"]
ResolutionStatus = Literal[
    "resolved",
    "pending_authorization",
    "missing",
    "rejected",
    "ambiguous",
    "invalid",
    "limit_exceeded",
]
ReferencePathKind = Literal["relative", "absolute", "invalid"]


class ReferenceModel(BaseModel):
    """Strict, serializable base for path-sanitized public reports."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ReferenceResolutionPolicy(ReferenceModel):
    """Explicit limits and local access policy."""

    max_main_file_size_bytes: int = Field(default=DEFAULT_MAX_MAIN_FILE_SIZE, ge=1)
    max_bundle_documents: int = Field(default=DEFAULT_MAX_BUNDLE_DOCUMENTS, ge=1)
    pbed: PbedReadPolicy = Field(default_factory=PbedReadPolicy)


class ReferenceDiagnostic(ReferenceModel):
    """Sanitized resolution diagnostic that never carries raw text or backing paths."""

    rule_id: Literal["SG016", "SG017", "SG018", "SG019", "SG020"]
    code: str
    severity: DiagnosticSeverity
    message: str
    source_name: str
    line: int | None = Field(default=None, ge=1)
    target_name: str | None = None
    record_number: int | None = Field(default=None, ge=1)


class ExternalReference(ReferenceModel):
    """One verified PBED reference extracted from the main input."""

    source_name: str
    source_line: int = Field(ge=1)
    reference_type: Literal["pbed"] = "pbed"
    target_name: str
    path_kind: ReferencePathKind
    universe: str
    background_universe: str
    power_output_requested: bool = False


class ResolvedReference(ReferenceModel):
    """Resolution status plus optional validated PBED data."""

    reference: ExternalReference
    status: ResolutionStatus
    file_size_bytes: int | None = Field(default=None, ge=0)
    record_count: int | None = Field(default=None, ge=0)
    valid_record_count: int | None = Field(default=None, ge=0)
    invalid_record_count: int | None = Field(default=None, ge=0)
    pbed_data: PbedData | None = None
    diagnostics: tuple[ReferenceDiagnostic, ...] = ()


class ExternalResolutionReport(ReferenceModel):
    """Public dependency graph report containing logical names only."""

    mode: ResolutionMode
    main_name: str
    references: tuple[ResolvedReference, ...] = ()
    unused_supporting_files: tuple[str, ...] = ()
    diagnostics: tuple[ReferenceDiagnostic, ...] = ()


class ReferencePolicyError(ValueError):
    """A sanitized caller-facing failure to construct a source sandbox."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """A logical document backed by bytes or one already-authorized canonical path."""

    logical_name: str
    size_bytes: int
    _content: bytes | None = field(default=None, repr=False)
    _canonical_path: Path | None = field(default=None, repr=False)

    def open_binary(self) -> BinaryIO:
        """Open one fresh binary stream without exposing its backing location."""
        if self._content is not None:
            return io.BytesIO(self._content)
        if self._canonical_path is None:  # pragma: no cover - construction invariant
            raise RuntimeError("Source document has no backing content")
        return self._canonical_path.open("rb")

    def read_bytes(self, *, limit: int) -> bytes:
        """Read a small main document after enforcing its explicit byte limit."""
        if self.size_bytes > limit:
            raise ReferencePolicyError(
                "MAIN_FILE_SIZE_LIMIT",
                "The main input exceeds the configured byte limit.",
            )
        if self._content is not None:
            return self._content
        if self._canonical_path is None:  # pragma: no cover - construction invariant
            raise RuntimeError("Source document has no backing content")
        try:
            return self._canonical_path.read_bytes()
        except OSError as error:
            raise ReferencePolicyError(
                "MAIN_READ_FAILED",
                "The selected main input could not be read.",
            ) from error


class UploadedSourceBundle:
    """An explicit in-memory main file plus zero or more supporting uploads."""

    def __init__(
        self,
        *,
        main_name: str,
        main_content: bytes,
        supporting_files: Iterable[tuple[str, bytes]],
        policy: ReferenceResolutionPolicy | None = None,
    ) -> None:
        self.policy = policy or ReferenceResolutionPolicy()
        support_items = list(supporting_files)
        if len(support_items) + 1 > self.policy.max_bundle_documents:
            raise ReferencePolicyError(
                "BUNDLE_DOCUMENT_LIMIT",
                "The uploaded bundle exceeds the configured document-count limit.",
            )

        normalized_main = normalize_bundle_name(main_name)
        self.main = SourceDocument(
            logical_name=normalized_main,
            size_bytes=len(main_content),
            _content=main_content,
        )
        self.supporting = tuple(
            SourceDocument(
                logical_name=normalize_bundle_name(name),
                size_bytes=len(content),
                _content=content,
            )
            for name, content in support_items
        )

    def read_main_bytes(self) -> bytes:
        """Return the explicit main upload under the configured main-file limit."""
        return self.main.read_bytes(limit=self.policy.max_main_file_size_bytes)

    def resolve_pbed(self) -> ExternalResolutionReport:
        """Resolve PBED targets only against the explicitly uploaded documents."""
        references, extraction_diagnostics = _extract_from_document(
            self.main,
            self.policy,
        )
        candidates: dict[str, list[tuple[int, SourceDocument]]] = defaultdict(list)
        for index, document in enumerate(self.supporting):
            candidates[_windows_key(document.logical_name)].append((index, document))

        global_diagnostics = list(extraction_diagnostics)
        for duplicate_group in candidates.values():
            if len(duplicate_group) > 1:
                logical_name = duplicate_group[0][1].logical_name
                global_diagnostics.append(
                    ReferenceDiagnostic(
                        rule_id="SG018",
                        code="DUPLICATE_BUNDLE_NAME",
                        severity="ERROR",
                        message=(
                            "Multiple uploaded supporting files have the same "
                            "normalized Windows name."
                        ),
                        source_name=self.main.logical_name,
                        target_name=logical_name,
                    )
                )

        used_indices: set[int] = set()
        resolved: list[ResolvedReference] = []
        for reference in references:
            if reference.path_kind != "relative":
                resolved.append(_rejected_path(reference))
                continue

            matches = candidates.get(_windows_key(reference.target_name), [])
            if not matches:
                resolved.append(_missing_reference(reference))
                continue
            if len(matches) > 1:
                resolved.append(_ambiguous_reference(reference))
                continue

            index, document = matches[0]
            used_indices.add(index)
            resolved.append(_parse_document(reference, document, self.policy))

        unused = tuple(
            document.logical_name
            for index, document in enumerate(self.supporting)
            if index not in used_indices
        )
        return ExternalResolutionReport(
            mode="uploaded_bundle",
            main_name=self.main.logical_name,
            references=tuple(resolved),
            unused_supporting_files=unused,
            diagnostics=tuple(global_diagnostics),
        )


class LocalProjectSource:
    """A main file confined to an independently authorized canonical root."""

    def __init__(
        self,
        *,
        main_path: str | Path,
        authorized_root: str | Path,
        policy: ReferenceResolutionPolicy | None = None,
    ) -> None:
        self.policy = policy or ReferenceResolutionPolicy()
        root = _resolve_existing(Path(authorized_root), expected="directory")
        main = _resolve_existing(Path(main_path), expected="file")
        if not _is_within(main, root):
            raise ReferencePolicyError(
                "MAIN_OUTSIDE_ROOT",
                "The main input is outside the authorized local root.",
            )

        self._canonical_root = root
        self.main = SourceDocument(
            logical_name=main.relative_to(root).as_posix(),
            size_bytes=main.stat().st_size,
            _canonical_path=main,
        )

    def read_main_bytes(self) -> bytes:
        """Read only the explicitly selected main file under its size limit."""
        return self.main.read_bytes(limit=self.policy.max_main_file_size_bytes)

    def preview_pbed(self) -> ExternalResolutionReport:
        """Resolve metadata safely without reading any supporting-file content."""
        return self._resolve(authorize_supporting_files=False)

    def resolve_pbed(
        self,
        *,
        authorize_supporting_files: bool,
    ) -> ExternalResolutionReport:
        """Read PBED data only when the caller explicitly authorizes it."""
        return self._resolve(authorize_supporting_files=authorize_supporting_files)

    def _resolve(self, *, authorize_supporting_files: bool) -> ExternalResolutionReport:
        references, extraction_diagnostics = _extract_from_document(
            self.main,
            self.policy,
        )
        resolved: list[ResolvedReference] = []
        for reference in references:
            if reference.path_kind != "relative":
                resolved.append(_rejected_path(reference))
                continue

            candidate = self._canonical_root / PurePosixPath(reference.target_name)
            canonical_candidate = candidate.resolve(strict=False)
            if not _is_within(canonical_candidate, self._canonical_root):
                resolved.append(
                    _policy_rejection(
                        reference,
                        code="REFERENCE_OUTSIDE_ROOT",
                        message=(
                            "The canonical target escapes the authorized local root."
                        ),
                    )
                )
                continue
            if not canonical_candidate.exists():
                resolved.append(_missing_reference(reference))
                continue
            if not canonical_candidate.is_file():
                resolved.append(
                    _policy_rejection(
                        reference,
                        code="REFERENCE_NOT_FILE",
                        message="The resolved target is not a regular file.",
                    )
                )
                continue

            size_bytes = canonical_candidate.stat().st_size
            if not authorize_supporting_files:
                resolved.append(
                    ResolvedReference(
                        reference=reference,
                        status="pending_authorization",
                        file_size_bytes=size_bytes,
                    )
                )
                continue

            document = SourceDocument(
                logical_name=reference.target_name,
                size_bytes=size_bytes,
                _canonical_path=canonical_candidate,
            )
            resolved.append(_parse_document(reference, document, self.policy))

        return ExternalResolutionReport(
            mode="local_project",
            main_name=self.main.logical_name,
            references=tuple(resolved),
            diagnostics=extraction_diagnostics,
        )


def normalize_bundle_name(name: str) -> str:
    """Normalize one explicit bundle name using safe Windows-relative semantics."""
    return _normalize_relative_path(name, base_parts=())


def _extract_from_document(
    document: SourceDocument,
    policy: ReferenceResolutionPolicy,
) -> tuple[tuple[ExternalReference, ...], tuple[ReferenceDiagnostic, ...]]:
    try:
        data = document.read_bytes(limit=policy.max_main_file_size_bytes)
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return (), (
            ReferenceDiagnostic(
                rule_id="SG017",
                code="MAIN_ENCODING",
                severity="ERROR",
                message=(
                    "External references could not be extracted because the main "
                    "input is not valid UTF-8."
                ),
                source_name=document.logical_name,
            ),
        )
    return extract_pbed_references(text, source_name=document.logical_name)


def extract_pbed_references(
    text: str,
    *,
    source_name: str,
) -> tuple[tuple[ExternalReference, ...], tuple[ReferenceDiagnostic, ...]]:
    """Extract only the observed, documented one-line PBED card form."""
    source = preprocess(text, file_name=source_name)
    references: list[ExternalReference] = []
    diagnostics: list[ReferenceDiagnostic] = []
    base_parts = PurePosixPath(source_name).parent.parts

    for line_number, line in enumerate(source.text.split("\n"), start=1):
        tokens = line.split(maxsplit=1)
        if not tokens or tokens[0].lower() != "pbed":
            continue
        match = _PBED_CARD.fullmatch(line)
        if match is None:
            diagnostics.append(
                ReferenceDiagnostic(
                    rule_id="SG017",
                    code="PBED_CARD_SYNTAX",
                    severity="ERROR",
                    message=(
                        "The PBED card is outside the supported one-line quoted-path "
                        "form and was not resolved."
                    ),
                    source_name=source_name,
                    line=line_number,
                )
            )
            continue

        universe, background, raw_target, pow_token = match.groups()
        path_kind, target_name = _classify_and_normalize_target(
            raw_target,
            base_parts=base_parts,
        )
        references.append(
            ExternalReference(
                source_name=source_name,
                source_line=line_number,
                target_name=target_name,
                path_kind=path_kind,
                universe=universe,
                background_universe=background,
                power_output_requested=pow_token is not None,
            )
        )

    return tuple(references), tuple(diagnostics)


def _classify_and_normalize_target(
    raw_target: str,
    *,
    base_parts: tuple[str, ...],
) -> tuple[ReferencePathKind, str]:
    if _is_absolute_or_drive_relative(raw_target):
        return "absolute", ABSOLUTE_TARGET_MARKER
    try:
        return "relative", _normalize_relative_path(
            raw_target,
            base_parts=base_parts,
        )
    except ReferencePolicyError:
        return "invalid", INVALID_TARGET_MARKER


def _normalize_relative_path(value: str, *, base_parts: tuple[str, ...]) -> str:
    if not value or "\x00" in value or _is_absolute_or_drive_relative(value):
        raise ReferencePolicyError(
            "INVALID_RELATIVE_PATH",
            "A source name is not a safe relative path.",
        )

    parts = list(base_parts)
    for part in value.replace("\\", "/").split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                raise ReferencePolicyError(
                    "PATH_TRAVERSAL",
                    "A relative source name escapes the explicit bundle root.",
                )
            parts.pop()
            continue
        if not _is_safe_windows_component(part):
            raise ReferencePolicyError(
                "INVALID_WINDOWS_NAME",
                "A source name contains a Windows-invalid path component.",
            )
        parts.append(part)

    if not parts:
        raise ReferencePolicyError(
            "EMPTY_RELATIVE_PATH",
            "A source name resolves to an empty path.",
        )
    return PurePosixPath(*parts).as_posix()


def _is_absolute_or_drive_relative(value: str) -> bool:
    windows = PureWindowsPath(value)
    posix = PurePosixPath(value.replace("\\", "/"))
    return bool(windows.drive or windows.root or posix.is_absolute())


def _is_safe_windows_component(part: str) -> bool:
    if (
        any(character in _WINDOWS_INVALID_NAME_CHARACTERS for character in part)
        or any(ord(character) < 32 for character in part)
        or part.endswith((" ", "."))
    ):
        return False
    stem = part.split(".", maxsplit=1)[0].casefold()
    return stem not in _WINDOWS_RESERVED_NAMES


def _windows_key(value: str) -> str:
    return value.replace("\\", "/").casefold()


def _resolve_existing(path: Path, *, expected: Literal["file", "directory"]) -> Path:
    try:
        canonical = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ReferencePolicyError(
            "LOCAL_SOURCE_MISSING",
            f"The selected local {expected} does not exist or cannot be resolved.",
        ) from error
    if expected == "file" and not canonical.is_file():
        raise ReferencePolicyError(
            "LOCAL_MAIN_NOT_FILE",
            "The selected local main input is not a regular file.",
        )
    if expected == "directory" and not canonical.is_dir():
        raise ReferencePolicyError(
            "LOCAL_ROOT_NOT_DIRECTORY",
            "The authorized local root is not a directory.",
        )
    return canonical


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        common = os.path.commonpath(
            (os.path.normcase(candidate), os.path.normcase(root))
        )
    except ValueError:
        return False
    return common == os.path.normcase(root)


def _parse_document(
    reference: ExternalReference,
    document: SourceDocument,
    policy: ReferenceResolutionPolicy,
) -> ResolvedReference:
    try:
        with document.open_binary() as stream:
            parsed = parse_pbed_binary(
                stream,
                source_name=document.logical_name,
                size_bytes=document.size_bytes,
                policy=policy.pbed,
            )
    except OSError:
        return ResolvedReference(
            reference=reference,
            status="invalid",
            file_size_bytes=document.size_bytes,
            diagnostics=(
                ReferenceDiagnostic(
                    rule_id="SG017",
                    code="REFERENCE_READ_FAILED",
                    severity="ERROR",
                    message="The authorized PBED target could not be read.",
                    source_name=reference.source_name,
                    line=reference.source_line,
                    target_name=reference.target_name,
                ),
            ),
        )
    diagnostics = tuple(
        ReferenceDiagnostic(
            rule_id=diagnostic.rule_id,
            code=diagnostic.code,
            severity=diagnostic.severity,
            message=diagnostic.message,
            source_name=diagnostic.source_name,
            line=diagnostic.line,
            target_name=reference.target_name,
            record_number=diagnostic.record_number,
        )
        for diagnostic in parsed.diagnostics
    )
    status: ResolutionStatus = "resolved"
    if any(item.rule_id == "SG020" for item in diagnostics):
        status = "limit_exceeded"
    elif any(item.severity == "ERROR" for item in diagnostics):
        status = "invalid"

    data = parsed.data
    return ResolvedReference(
        reference=reference,
        status=status,
        file_size_bytes=document.size_bytes,
        record_count=data.total_record_count if data is not None else None,
        valid_record_count=data.valid_record_count if data is not None else None,
        invalid_record_count=data.invalid_record_count if data is not None else None,
        pbed_data=data,
        diagnostics=diagnostics,
    )


def _missing_reference(reference: ExternalReference) -> ResolvedReference:
    return ResolvedReference(
        reference=reference,
        status="missing",
        diagnostics=(
            ReferenceDiagnostic(
                rule_id="SG016",
                code="REFERENCE_MISSING",
                severity="ERROR",
                message="The referenced PBED file is not present in the allowed set.",
                source_name=reference.source_name,
                line=reference.source_line,
                target_name=reference.target_name,
            ),
        ),
    )


def _rejected_path(reference: ExternalReference) -> ResolvedReference:
    code = (
        "ABSOLUTE_REFERENCE_REJECTED"
        if reference.path_kind == "absolute"
        else "INVALID_REFERENCE_PATH"
    )
    message = (
        "Absolute external references are rejected by the local sandbox policy."
        if reference.path_kind == "absolute"
        else "The external reference path is invalid or escapes the explicit root."
    )
    return _policy_rejection(reference, code=code, message=message)


def _policy_rejection(
    reference: ExternalReference,
    *,
    code: str,
    message: str,
) -> ResolvedReference:
    return ResolvedReference(
        reference=reference,
        status="rejected",
        diagnostics=(
            ReferenceDiagnostic(
                rule_id="SG017",
                code=code,
                severity="ERROR",
                message=message,
                source_name=reference.source_name,
                line=reference.source_line,
                target_name=reference.target_name,
            ),
        ),
    )


def _ambiguous_reference(reference: ExternalReference) -> ResolvedReference:
    return ResolvedReference(
        reference=reference,
        status="ambiguous",
        diagnostics=(
            ReferenceDiagnostic(
                rule_id="SG018",
                code="AMBIGUOUS_BUNDLE_REFERENCE",
                severity="ERROR",
                message=(
                    "The PBED target matches multiple uploaded files after normalized "
                    "case-insensitive comparison."
                ),
                source_name=reference.source_name,
                line=reference.source_line,
                target_name=reference.target_name,
            ),
        ),
    )
