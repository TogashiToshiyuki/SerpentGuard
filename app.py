"""Local bilingual Streamlit interface for deterministic SerpentGuard analysis."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import streamlit as st

from serpentguard.analysis import analyze_model, has_unrecoverable_parse_failure
from serpentguard.geometry import (
    DEFAULT_BOUNDARY_TOLERANCE,
    DEFAULT_GRID_RESOLUTION,
    MAX_GRID_RESOLUTION,
    MIN_GRID_RESOLUTION,
    GeometryConfigError,
    GeometrySamplingConfig,
    GeometrySamplingResult,
    PointClassification,
    sample_geometry,
)
from serpentguard.geometry_plot import create_geometry_figure
from serpentguard.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGE_SESSION_KEY,
    SUPPORTED_LANGUAGES,
    SupportedLanguage,
    language_display_name,
    translate,
)
from serpentguard.models import AnalysisReport, ParsedModel
from serpentguard.parser import parse_bytes
from serpentguard.ui import (
    SEVERITY_ORDER,
    available_rule_ids,
    filter_findings,
    geometry_excluded_cell_rows,
    geometry_representative_rows,
    localized_finding_title,
    localized_findings_table_rows,
    localized_object_label,
    parsed_model_debug_payload,
    severity_counts,
    severity_display_label,
)

_RESULT_KEY = "serpentguard_analysis_result"
_GEOMETRY_RESULT_KEY = "serpentguard_geometry_result"
_SEVERITY_FILTER_KEY = "serpentguard_severity_filter"
_RULE_FILTER_KEY = "serpentguard_rule_filter"


def _clear_previous_result() -> None:
    st.session_state.pop(_RESULT_KEY, None)
    st.session_state.pop(_GEOMETRY_RESULT_KEY, None)
    st.session_state.pop(_SEVERITY_FILTER_KEY, None)
    st.session_state.pop(_RULE_FILTER_KEY, None)


def _render_geometry_sampler(
    parsed: ParsedModel,
    language: SupportedLanguage,
    t: Callable[..., str],
) -> None:
    """Render the explicit geometry form and any canonical sampling result."""
    st.info(t("geometry.intro"))
    st.warning(
        "\n".join(
            (
                f"- {t('geometry.warning.sampling')}",
                f"- {t('geometry.warning.narrow')}",
                f"- {t('geometry.warning.plotter')}",
            )
        )
    )

    with st.form("serpentguard_geometry_form"):
        slice_columns = st.columns(3)
        z_value = slice_columns[0].number_input(
            t("geometry.form.z"),
            value=0.0,
            format="%.6f",
            key="serpentguard_geometry_z",
        )
        resolution = slice_columns[1].number_input(
            t("geometry.form.resolution"),
            min_value=MIN_GRID_RESOLUTION,
            max_value=MAX_GRID_RESOLUTION,
            value=DEFAULT_GRID_RESOLUTION,
            step=1,
            help=t("geometry.form.resolution_help"),
            key="serpentguard_geometry_resolution",
        )
        boundary_tolerance = slice_columns[2].number_input(
            t("geometry.form.tolerance"),
            min_value=0.0,
            value=DEFAULT_BOUNDARY_TOLERANCE,
            format="%.2e",
            help=t("geometry.form.tolerance_help"),
            key="serpentguard_geometry_tolerance",
        )

        x_columns = st.columns(2)
        xmin = x_columns[0].number_input(
            t("geometry.form.xmin"),
            value=-1.0,
            format="%.6f",
            key="serpentguard_geometry_xmin",
        )
        xmax = x_columns[1].number_input(
            t("geometry.form.xmax"),
            value=1.0,
            format="%.6f",
            key="serpentguard_geometry_xmax",
        )
        y_columns = st.columns(2)
        ymin = y_columns[0].number_input(
            t("geometry.form.ymin"),
            value=-1.0,
            format="%.6f",
            key="serpentguard_geometry_ymin",
        )
        ymax = y_columns[1].number_input(
            t("geometry.form.ymax"),
            value=1.0,
            format="%.6f",
            key="serpentguard_geometry_ymax",
        )
        sample_requested = st.form_submit_button(
            t("geometry.form.submit"),
            type="primary",
        )

    if sample_requested:
        try:
            config = GeometrySamplingConfig(
                xmin=float(xmin),
                xmax=float(xmax),
                ymin=float(ymin),
                ymax=float(ymax),
                z=float(z_value),
                resolution=int(resolution),
                boundary_tolerance=float(boundary_tolerance),
            )
        except GeometryConfigError as error:
            st.error(t("geometry.config_error", message=error))
        else:
            with st.spinner(t("geometry.spinner")):
                st.session_state[_GEOMETRY_RESULT_KEY] = sample_geometry(parsed, config)

    geometry_result = st.session_state.get(_GEOMETRY_RESULT_KEY)
    if not isinstance(geometry_result, GeometrySamplingResult):
        return

    config = geometry_result.config
    st.caption(
        t(
            "geometry.summary",
            xmin=f"{config.xmin:.8g}",
            xmax=f"{config.xmax:.8g}",
            ymin=f"{config.ymin:.8g}",
            ymax=f"{config.ymax:.8g}",
            z=f"{config.z:.8g}",
            resolution=config.resolution,
            total=geometry_result.total_points,
            tolerance=f"{config.boundary_tolerance:.3g}",
        )
    )
    st.caption(
        t(
            "geometry.cells",
            included=len(geometry_result.included_cells),
            excluded=len(geometry_result.excluded_cells),
        )
    )
    if not geometry_result.included_cells:
        st.warning(t("geometry.no_included_cells"))

    metric_columns = st.columns(4)
    metric_columns[0].metric(
        t("geometry.metric.overlap"), geometry_result.overlap_count
    )
    metric_columns[1].metric(
        t("geometry.metric.undefined"), geometry_result.undefined_count
    )
    metric_columns[2].metric(t("geometry.metric.normal"), geometry_result.normal_count)
    metric_columns[3].metric(
        t("geometry.metric.indeterminate"), geometry_result.indeterminate_count
    )

    classification_labels = {
        PointClassification.UNDEFINED: t("geometry.classification.undefined"),
        PointClassification.NORMAL: t("geometry.classification.normal"),
        PointClassification.OVERLAP: t("geometry.classification.overlap"),
        PointClassification.INDETERMINATE: t("geometry.classification.indeterminate"),
    }
    figure = create_geometry_figure(
        geometry_result,
        title=t("geometry.plot.title", z=f"{config.z:.8g}"),
        classification_labels=classification_labels,
    )
    st.pyplot(figure, use_container_width=True)
    figure.clear()

    representative_columns = st.columns(2)
    representative_sets = (
        (
            representative_columns[0],
            "geometry.representatives.overlap",
            geometry_result.overlap_representatives,
        ),
        (
            representative_columns[1],
            "geometry.representatives.undefined",
            geometry_result.undefined_representatives,
        ),
    )
    for column, heading_key, points in representative_sets:
        column.markdown(f"#### {t(heading_key)}")
        rows = geometry_representative_rows(points, language)
        if rows:
            column.dataframe(rows, hide_index=True)
        else:
            column.info(t("geometry.representatives.none"))

    st.markdown(f"#### {t('geometry.excluded.heading')}")
    excluded_rows = geometry_excluded_cell_rows(
        geometry_result.excluded_cells,
        language,
    )
    if excluded_rows:
        st.dataframe(excluded_rows, hide_index=True)
    else:
        st.success(t("geometry.excluded.none"))


stored_language = st.session_state.get(LANGUAGE_SESSION_KEY, DEFAULT_LANGUAGE)
if stored_language not in SUPPORTED_LANGUAGES:
    stored_language = DEFAULT_LANGUAGE
    st.session_state[LANGUAGE_SESSION_KEY] = stored_language

st.set_page_config(
    page_title=translate("page.title", stored_language),
    layout="wide",
)

language: SupportedLanguage = st.selectbox(
    translate("language.selector", stored_language),
    options=SUPPORTED_LANGUAGES,
    format_func=language_display_name,
    key=LANGUAGE_SESSION_KEY,
)
t = partial(translate, language=language)

st.title(t("app.title"))
st.warning(t("app.warning"))
st.info(t("app.local_notice"))

st.subheader(t("section.upload"))
main_input = st.file_uploader(
    t("upload.main.label"),
    help=t("upload.main.help"),
    key="serpentguard_main_input",
    on_change=_clear_previous_result,
)
supporting_files = st.file_uploader(
    t("upload.supporting.label"),
    accept_multiple_files=True,
    help=t("upload.supporting.help"),
    key="serpentguard_supporting_inputs",
)
if supporting_files:
    st.caption(t("upload.supporting.caption", count=len(supporting_files)))

st.subheader(t("section.purpose"))
analysis_purpose = st.text_area(
    t("purpose.label"),
    placeholder=t("purpose.placeholder"),
    help=t("purpose.help"),
)

st.subheader(t("section.run"))
run_check = st.button(
    t("run.button"),
    type="primary",
    disabled=main_input is None,
    help=t("run.help"),
)

if run_check and main_input is not None:
    with st.spinner(t("run.spinner")):
        parsed = parse_bytes(main_input.getvalue(), file_name=main_input.name)
        report = analyze_model(parsed)
        st.session_state.pop(_GEOMETRY_RESULT_KEY, None)
        st.session_state[_RESULT_KEY] = {
            "file_name": main_input.name,
            "analysis_purpose": analysis_purpose.strip(),
            "parsed": parsed,
            "report": report,
        }

result = st.session_state.get(_RESULT_KEY)

st.subheader(t("section.summary"))
if result is None:
    st.info(t("summary.empty"))
else:
    parsed = result["parsed"]
    report = result["report"]
    if not isinstance(parsed, ParsedModel) or not isinstance(report, AnalysisReport):
        st.error(t("summary.invalid_state"))
    else:
        if has_unrecoverable_parse_failure(parsed):
            st.error(t("summary.parser_unrecoverable"))
        elif any(
            finding.rule_id in {"SG011", "SG015"} and finding.severity == "ERROR"
            for finding in report.findings
        ):
            st.error(t("summary.parser_recoverable"))

        object_columns = st.columns(4)
        object_columns[0].metric(t("metric.surfaces"), report.model_summary["surfaces"])
        object_columns[1].metric(t("metric.cells"), report.model_summary["cells"])
        object_columns[2].metric(
            t("metric.materials"), report.model_summary["materials"]
        )
        object_columns[3].metric(
            t("metric.unknown_cards"), report.model_summary["unknown_cards"]
        )

        counts = severity_counts(report.findings)
        severity_columns = st.columns(4)
        for column, severity in zip(severity_columns, SEVERITY_ORDER, strict=True):
            column.metric(severity_display_label(severity, language), counts[severity])

st.subheader(t("section.findings"))
if result is None:
    st.info(t("findings.before_run"))
elif isinstance(result.get("parsed"), ParsedModel) and isinstance(
    result.get("report"), AnalysisReport
):
    parsed = result["parsed"]
    report = result["report"]
    rule_ids = available_rule_ids(report.findings)
    filter_columns = st.columns(2)
    selected_severities = filter_columns[0].multiselect(
        t("findings.filter.severity"),
        options=list(SEVERITY_ORDER),
        default=list(SEVERITY_ORDER),
        format_func=lambda severity: severity_display_label(severity, language),
        key=_SEVERITY_FILTER_KEY,
    )
    selected_rule_ids = filter_columns[1].multiselect(
        t("findings.filter.rule_id"),
        options=rule_ids,
        default=rule_ids,
        key=_RULE_FILTER_KEY,
    )
    filtered_findings = filter_findings(
        report.findings,
        severities=selected_severities,
        rule_ids=selected_rule_ids,
    )

    if filtered_findings:
        st.dataframe(
            localized_findings_table_rows(filtered_findings, language),
            hide_index=True,
        )
        st.caption(
            t(
                "findings.count",
                shown=len(filtered_findings),
                total=len(report.findings),
            )
        )
        for finding_number, finding in enumerate(filtered_findings, start=1):
            object_label = (
                finding.object_name
                or localized_object_label(
                    finding.object_type,
                    None,
                    language,
                )
                or t("object.input")
            )
            with st.expander(
                t(
                    "findings.evidence_expander",
                    number=finding_number,
                    rule_id=finding.rule_id,
                    object_label=object_label,
                )
            ):
                st.caption(localized_finding_title(finding, language))
                st.json(finding.evidence)
    elif report.findings:
        st.info(t("findings.no_filter_matches"))
    else:
        st.success(t("findings.none"))

    with st.expander(t("debug.expander")):
        st.caption(t("debug.caption"))
        st.json(parsed_model_debug_payload(parsed))

st.subheader(t("section.geometry"))
geometry_parsed = result.get("parsed") if isinstance(result, dict) else None
if result is None:
    st.info(t("geometry.before_run"))
elif isinstance(geometry_parsed, ParsedModel) and not has_unrecoverable_parse_failure(
    geometry_parsed
):
    _render_geometry_sampler(geometry_parsed, language, t)
else:
    st.error(t("geometry.unavailable"))

st.subheader(t("section.ai"))
st.info(t("ai.placeholder"))
