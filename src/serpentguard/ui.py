"""Pure presentation helpers shared by the local Streamlit interface and tests."""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection
from typing import Any

from serpentguard.geometry import (
    ExcludedCell,
    GeometryExclusion,
    RepresentativePoint,
)
from serpentguard.i18n import (
    ENGLISH,
    JAPANESE,
    SupportedLanguage,
    translate,
)
from serpentguard.models import DiagnosticSeverity, Finding, ParsedModel
from serpentguard.references import (
    ExternalResolutionReport,
    ReferenceDiagnostic,
)

SEVERITY_ORDER: tuple[DiagnosticSeverity, ...] = (
    "ERROR",
    "WARNING",
    "REVIEW",
    "INFO",
)
LOCALIZED_FINDING_RULE_IDS = frozenset(
    {
        "SG001",
        "SG002",
        "SG003",
        "SG004",
        "SG005",
        "SG006",
        "SG007",
        "SG008",
        "SG009",
        "SG010",
        "SG011",
        "SG014",
        "SG015",
        "SG021",
        "SG022",
        "SG023",
        "SG024",
        "SG025",
        "SG026",
        "SG027",
    }
)
_LOCALIZED_PARSER_CODES = frozenset(
    {
        "PARSER_IO",
        "PARSER_ENCODING",
        "PARSER001",
        "PARSER002",
        "PARSER003",
        "PARSER004",
        "PARSER005",
    }
)
_REFERENCE_DIAGNOSTIC_KEYS = frozenset(
    {
        "MAIN_ENCODING",
        "PBED_CARD_SYNTAX",
        "DUPLICATE_BUNDLE_NAME",
        "REFERENCE_MISSING",
        "ABSOLUTE_REFERENCE_REJECTED",
        "INVALID_REFERENCE_PATH",
        "REFERENCE_OUTSIDE_ROOT",
        "REFERENCE_NOT_FILE",
        "REFERENCE_READ_FAILED",
        "AMBIGUOUS_BUNDLE_REFERENCE",
        "PBED_FILE_SIZE_LIMIT",
        "PBED_RECORD_LIMIT",
        "PBED_COLUMN_COUNT",
        "PBED_BLANK_LINE",
        "PBED_NUMERIC_VALUE",
        "PBED_NON_POSITIVE_RADIUS",
        "PBED_ENCODING",
        "PBED_EMPTY",
    }
)


def severity_counts(findings: list[Finding]) -> dict[DiagnosticSeverity, int]:
    """Return a stable four-severity summary, including zero counts."""
    counts = Counter(finding.severity for finding in findings)
    return {severity: counts[severity] for severity in SEVERITY_ORDER}


def available_rule_ids(findings: list[Finding]) -> list[str]:
    """Return sorted unique rule IDs for filter controls."""
    return sorted({finding.rule_id for finding in findings})


def filter_findings(
    findings: list[Finding],
    *,
    severities: Collection[str],
    rule_ids: Collection[str],
) -> list[Finding]:
    """Apply conjunctive severity and rule filters without changing finding order."""
    severity_filter = set(severities)
    rule_filter = set(rule_ids)
    return [
        finding
        for finding in findings
        if finding.severity in severity_filter and finding.rule_id in rule_filter
    ]


def ai_generation_requested(
    *,
    button_pressed: bool,
    consent_confirmed: bool,
    payload_available: bool,
) -> bool:
    """Gate a future AI action behind a visible payload and explicit user action.

    This pure helper cannot invoke a client or perform network access.  The future API
    milestone may use its return value as one of several safeguards.
    """
    return button_pressed and consent_confirmed and payload_available


def findings_table_rows(findings: list[Finding]) -> list[dict[str, str]]:
    """Preserve the original English findings-table output."""
    return localized_findings_table_rows(findings, ENGLISH)


def severity_display_label(
    severity: DiagnosticSeverity,
    language: SupportedLanguage,
) -> str:
    """Localize a severity label without changing its canonical stored value."""
    return translate(f"severity.{severity}", language)


def localized_finding_title(
    finding: Finding,
    language: SupportedLanguage,
) -> str:
    """Render a finding title without mutating the canonical Finding."""
    if language == ENGLISH:
        return finding.title
    if finding.rule_id not in LOCALIZED_FINDING_RULE_IDS:
        return _untranslated_fallback(finding.title, language)
    return translate(f"finding.{finding.rule_id}.title", language)


def localized_finding_message(
    finding: Finding,
    language: SupportedLanguage,
) -> str:
    """Render rule-specific structured evidence in the requested language."""
    if language == ENGLISH:
        return finding.message
    if language != JAPANESE or finding.rule_id not in LOCALIZED_FINDING_RULE_IDS:
        return _untranslated_fallback(finding.message, language)

    context = _finding_message_context(finding, language)
    if context is None:
        return _untranslated_fallback(finding.message, language)
    key, values = context
    return translate(key, language, **values)


def localized_object_label(
    object_type: str | None,
    object_name: str | None,
    language: SupportedLanguage,
) -> str:
    """Localize only the object type while preserving the user-defined name."""
    if language == ENGLISH:
        return _format_object(object_type, object_name)
    localized_type = object_type
    if object_type in {
        "surface",
        "cell",
        "material",
        "energy_grid",
        "detector",
        "card",
        "comment",
        "input",
    }:
        localized_type = translate(f"object.{object_type}", language)
    return _format_object(localized_type, object_name)


def localized_findings_table_rows(
    findings: list[Finding],
    language: SupportedLanguage,
) -> list[dict[str, str]]:
    """Flatten findings using localized headings, severities, objects, and messages."""
    rows: list[dict[str, str]] = []
    for finding in findings:
        rows.append(
            {
                translate("table.severity", language): severity_display_label(
                    finding.severity, language
                ),
                translate("table.rule_id", language): finding.rule_id,
                translate("table.file", language): finding.file or "",
                translate("table.line", language): _format_line(
                    finding.line, finding.line_end
                ),
                translate("table.object", language): localized_object_label(
                    finding.object_type,
                    finding.object_name,
                    language,
                ),
                translate("table.message", language): localized_finding_message(
                    finding, language
                ),
            }
        )
    return rows


def external_reference_table_rows(
    report: ExternalResolutionReport,
    language: SupportedLanguage,
) -> list[dict[str, str]]:
    """Flatten a sanitized reference report with localized display values."""
    rows: list[dict[str, str]] = []
    for resolved in report.references:
        reference = resolved.reference
        target_name = reference.target_name
        if reference.path_kind == "absolute":
            target_name = translate("reference.target.absolute", language)
        elif reference.path_kind == "invalid":
            target_name = translate("reference.target.invalid", language)
        rows.append(
            {
                translate("reference.table.source", language): reference.source_name,
                translate("reference.table.type", language): "PBED",
                translate("reference.table.target", language): target_name,
                translate("reference.table.status", language): translate(
                    f"reference.status.{resolved.status}", language
                ),
                translate("reference.table.size", language): (
                    str(resolved.file_size_bytes)
                    if resolved.file_size_bytes is not None
                    else ""
                ),
                translate("reference.table.records", language): (
                    str(resolved.record_count)
                    if resolved.record_count is not None
                    else ""
                ),
            }
        )
    return rows


def localized_reference_diagnostic_message(
    diagnostic: ReferenceDiagnostic,
    language: SupportedLanguage,
) -> str:
    """Localize a structured resolver diagnostic without changing the diagnostic."""
    if language == ENGLISH:
        return diagnostic.message
    if diagnostic.code not in _REFERENCE_DIAGNOSTIC_KEYS:
        return _untranslated_fallback(diagnostic.message, language)
    return translate(f"reference.diagnostic.{diagnostic.code}", language)


def parsed_model_debug_payload(model: ParsedModel) -> dict[str, Any]:
    """Create parsed-model JSON data while omitting raw card text fields."""
    payload = model.model_dump(mode="json")
    redacted = _remove_raw_text(payload)
    if not isinstance(redacted, dict):
        raise TypeError("Parsed model payload must be a dictionary")
    return redacted


def geometry_representative_rows(
    points: Collection[RepresentativePoint],
    language: SupportedLanguage,
) -> list[dict[str, str]]:
    """Flatten representative coordinates with localized table headings."""
    return [
        {
            translate("geometry.table.x", language): f"{point.x:.8g}",
            translate("geometry.table.y", language): f"{point.y:.8g}",
            translate("geometry.table.cells", language): ", ".join(
                point.involved_cells
            ),
        }
        for point in points
    ]


def geometry_excluded_cell_rows(
    excluded_cells: Collection[ExcludedCell],
    language: SupportedLanguage,
) -> list[dict[str, str]]:
    """Flatten structured cell exclusions without exposing raw input text."""
    separator = translate("geometry.reason.separator", language)
    return [
        {
            translate("geometry.table.cell", language): cell.name,
            translate("geometry.table.file", language): cell.location.file_name,
            translate("geometry.table.line", language): _format_line(
                cell.location.line_start,
                cell.location.line_end,
            ),
            translate("geometry.table.reason", language): separator.join(
                localized_geometry_exclusion_reason(
                    reason,
                    language,
                    cell_name=cell.name,
                )
                for reason in cell.reasons
            ),
        }
        for cell in excluded_cells
    ]


def localized_geometry_exclusion_reason(
    reason: GeometryExclusion,
    language: SupportedLanguage,
    *,
    cell_name: str | None = None,
) -> str:
    """Render one structured geometry exclusion reason."""
    key = f"geometry.exclusion.{reason.code}"
    if reason.code in {
        "undefined_surface",
        "ambiguous_surface",
    }:
        return translate(key, language, surface=reason.surface_name or "<unknown>")
    if reason.code in {
        "unsupported_surface_type",
        "invalid_surface_parameters",
    }:
        return translate(
            key,
            language,
            surface=reason.surface_name or "<unknown>",
            surface_type=reason.surface_type or "<unknown>",
        )
    if reason.code == "duplicate_cell_name":
        return translate(
            key,
            language,
            cell=cell_name or "<unknown>",
            count=reason.duplicate_count or "<unknown>",
        )
    return translate(key, language)


def _format_line(line: int | None, line_end: int | None) -> str:
    if line is None:
        return ""
    if line_end is not None and line_end != line:
        return f"{line}-{line_end}"
    return str(line)


def _format_object(object_type: str | None, object_name: str | None) -> str:
    if object_type is None:
        return object_name or ""
    if object_name is None:
        return object_type
    return f"{object_type}: {object_name}"


def _finding_message_context(
    finding: Finding,
    language: SupportedLanguage,
) -> tuple[str, dict[str, object]] | None:
    name = finding.object_name
    evidence = finding.evidence

    if finding.rule_id in {"SG001", "SG002", "SG003", "SG021"}:
        definition_count = _integer(evidence.get("definition_count"))
        if name is None or definition_count is None:
            return None
        return (
            f"finding.{finding.rule_id}.message",
            {"name": name, "definition_count": definition_count},
        )

    if finding.rule_id in {"SG004", "SG005"}:
        reference = _text(evidence.get("reference"))
        if name is None or reference is None:
            return None
        return (
            f"finding.{finding.rule_id}.message",
            {"cell": name, "reference": reference},
        )

    if finding.rule_id in {"SG006", "SG007"}:
        if name is None:
            return None
        return f"finding.{finding.rule_id}.message", {"name": name}

    if finding.rule_id == "SG008":
        surface = _text(evidence.get("surface"))
        term = _integer(evidence.get("intersection_term"))
        positive_count = _integer(evidence.get("positive_count"))
        negative_count = _integer(evidence.get("negative_count"))
        if (
            name is None
            or surface is None
            or term is None
            or positive_count is None
            or negative_count is None
        ):
            return None
        return (
            "finding.SG008.message",
            {
                "cell": name,
                "surface": surface,
                "term": term,
                "positive_count": positive_count,
                "negative_count": negative_count,
            },
        )

    if finding.rule_id == "SG009":
        condition = _text(evidence.get("signed_condition"))
        occurrences = _integer(evidence.get("occurrences"))
        term = _integer(evidence.get("intersection_term"))
        if name is None or condition is None or occurrences is None or term is None:
            return None
        return (
            "finding.SG009.message",
            {
                "cell": name,
                "condition": condition,
                "occurrences": occurrences,
                "term": term,
            },
        )

    if finding.rule_id == "SG010":
        details = _complexity_details(finding, language)
        if name is None or details is None:
            return None
        return "finding.SG010.message", {"cell": name, "details": details}

    if finding.rule_id == "SG011":
        opening_line = _integer(evidence.get("opening_line"))
        if opening_line is None:
            return None
        return "finding.SG011.message", {"opening_line": opening_line}

    if finding.rule_id == "SG014":
        keyword = _text(evidence.get("keyword"))
        if keyword is None:
            return None
        return "finding.SG014.message", {"keyword": keyword}

    if finding.rule_id == "SG015":
        parser_code = _text(evidence.get("parser_code"))
        if parser_code not in _LOCALIZED_PARSER_CODES:
            return None
        return f"finding.SG015.message.{parser_code}", {}

    if finding.rule_id == "SG022":
        reference = _text(evidence.get("reference"))
        if name is None or reference is None:
            return None
        return "finding.SG022.message", {"detector": name, "reference": reference}

    if finding.rule_id == "SG023":
        option = _text(evidence.get("option"))
        bin_count = _integer(evidence.get("bin_count"))
        if name is None or option is None or bin_count is None:
            return None
        return (
            "finding.SG023.message",
            {"name": name, "option": option, "bin_count": bin_count},
        )

    if finding.rule_id == "SG024":
        option = _text(evidence.get("option"))
        minimum = _number(evidence.get("minimum"))
        maximum = _number(evidence.get("maximum"))
        if name is None or option is None or minimum is None or maximum is None:
            return None
        return (
            "finding.SG024.message",
            {
                "name": name,
                "option": option,
                "minimum": minimum,
                "maximum": maximum,
            },
        )

    if finding.rule_id == "SG025":
        total_bins = _integer(evidence.get("total_bin_count"))
        threshold = _integer(evidence.get("threshold"))
        if name is None or total_bins is None or threshold is None:
            return None
        return (
            "finding.SG025.message",
            {"name": name, "total_bins": total_bins, "threshold": threshold},
        )

    if finding.rule_id == "SG026":
        if name is None:
            return None
        return "finding.SG026.message", {"name": name}

    if finding.rule_id == "SG027":
        option = _text(evidence.get("option"))
        if name is None or option is None:
            return None
        return "finding.SG027.message", {"name": name, "option": option}

    return None


def _complexity_details(
    finding: Finding,
    language: SupportedLanguage,
) -> str | None:
    exceeded = finding.evidence.get("exceeded_thresholds")
    if not isinstance(exceeded, dict):
        return None

    details: list[str] = []
    key_map = {
        "surface_references": "finding.SG010.detail.references",
        "union_operators": "finding.SG010.detail.unions",
    }
    for threshold_name, translation_key in key_map.items():
        threshold = exceeded.get(threshold_name)
        if not isinstance(threshold, dict):
            continue
        actual = _integer(threshold.get("actual"))
        limit = _integer(threshold.get("limit"))
        if actual is None or limit is None:
            return None
        details.append(translate(translation_key, language, actual=actual, limit=limit))
    if not details:
        return None
    separator = "，" if language == JAPANESE else ", "
    return separator.join(details)


def _untranslated_fallback(message: str, language: SupportedLanguage) -> str:
    return translate("findings.untranslated", language, message=message)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _remove_raw_text(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _remove_raw_text(item)
            for key, item in value.items()
            if key != "raw_text"
        }
    if isinstance(value, list):
        return [_remove_raw_text(item) for item in value]
    return value
