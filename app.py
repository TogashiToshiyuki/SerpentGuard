"""Local bilingual Streamlit interface for deterministic SerpentGuard analysis."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import streamlit as st

from serpentguard.ai_payload import (
    PayloadPrivacyError,
    build_ai_review_payload,
    payload_fingerprint,
)
from serpentguard.ai_review import (
    AIExplanationResponse,
    AIReviewServiceError,
    generate_ai_explanation,
)
from serpentguard.analysis import analyze_model, has_unrecoverable_parse_failure
from serpentguard.geometry import (
    DEFAULT_BOUNDARY_TOLERANCE,
    DEFAULT_GRID_RESOLUTION,
    DEFAULT_MAX_GEOMETRY_WORKLOAD,
    MAX_GRID_RESOLUTION,
    MIN_GRID_RESOLUTION,
    GeometryConfigError,
    GeometrySamplingConfig,
    GeometrySamplingResult,
    GeometryWorkloadError,
    PointClassification,
    available_universes,
    default_target_universe,
    sample_geometry,
)
from serpentguard.geometry_plot import (
    close_figure,
    create_diagnostic_figure,
    create_geometry_view_figure,
    select_plot_font,
)
from serpentguard.i18n import (
    DEFAULT_LANGUAGE,
    ENGLISH,
    JAPANESE,
    LANGUAGE_SESSION_KEY,
    SUPPORTED_LANGUAGES,
    SupportedLanguage,
    language_display_name,
    translate,
)
from serpentguard.models import AnalysisReport, Finding, ParsedModel
from serpentguard.parser import parse_bytes
from serpentguard.pbed_plot import (
    PbedSliceResult,
    create_pbed_slice_figure,
    project_pbed_centers,
    slice_pbed_placements,
)
from serpentguard.references import (
    ExternalResolutionReport,
    LocalProjectSource,
    ReferencePolicyError,
    UploadedSourceBundle,
)
from serpentguard.ui import (
    SEVERITY_ORDER,
    ai_generation_requested,
    available_rule_ids,
    external_reference_table_rows,
    filter_findings,
    geometry_excluded_cell_rows,
    geometry_representative_rows,
    localized_finding_title,
    localized_findings_table_rows,
    localized_object_label,
    localized_reference_diagnostic_message,
    parsed_model_debug_payload,
    severity_counts,
    severity_display_label,
)

_RESULT_KEY = "serpentguard_analysis_result"
_GEOMETRY_RESULT_KEY = "serpentguard_geometry_result"
_REFERENCE_RESULT_KEY = "serpentguard_external_reference_result"
_LOCAL_PROJECT_KEY = "serpentguard_local_project_source"
_PBED_SLICE_RESULT_KEY = "serpentguard_pbed_slice_result"
_SEVERITY_FILTER_KEY = "serpentguard_severity_filter"
_RULE_FILTER_KEY = "serpentguard_rule_filter"
_SOURCE_MODE_KEY = "serpentguard_source_mode"
_PBED_TARGET_KEY = "serpentguard_pbed_target"
_PBED_Z_KEY = "serpentguard_pbed_slice_z"
_PBED_MODE_KEY = "serpentguard_pbed_view_mode"
_AI_CONSENT_KEY = "serpentguard_ai_payload_consent"
_AI_PAYLOAD_FINGERPRINT_KEY = "serpentguard_ai_payload_fingerprint"
_AI_GENERATE_BUTTON_KEY = "serpentguard_ai_generate_button"
_AI_RESPONSE_KEY = "serpentguard_ai_explanation_response"
_AI_RESPONSE_FINGERPRINT_KEY = "serpentguard_ai_response_fingerprint"
_MAX_PBED_PLOT_CIRCLES = 20_000
_GEOMETRY_WIDGET_KEYS = (
    "serpentguard_geometry_universe",
    "serpentguard_geometry_z",
    "serpentguard_geometry_resolution",
    "serpentguard_geometry_tolerance",
    "serpentguard_geometry_xmin",
    "serpentguard_geometry_xmax",
    "serpentguard_geometry_ymin",
    "serpentguard_geometry_ymax",
)


def _clear_previous_result() -> None:
    st.session_state.pop(_RESULT_KEY, None)
    st.session_state.pop(_GEOMETRY_RESULT_KEY, None)
    st.session_state.pop(_REFERENCE_RESULT_KEY, None)
    st.session_state.pop(_LOCAL_PROJECT_KEY, None)
    st.session_state.pop(_PBED_SLICE_RESULT_KEY, None)
    st.session_state.pop(_PBED_TARGET_KEY, None)
    st.session_state.pop(_PBED_Z_KEY, None)
    st.session_state.pop(_PBED_MODE_KEY, None)
    st.session_state.pop(_SEVERITY_FILTER_KEY, None)
    st.session_state.pop(_RULE_FILTER_KEY, None)
    _clear_ai_review_state()
    for key in _GEOMETRY_WIDGET_KEYS:
        st.session_state.pop(key, None)


def _clear_ai_review_state() -> None:
    """Clear consent whenever the canonical payload may have changed."""
    st.session_state.pop(_AI_CONSENT_KEY, None)
    st.session_state.pop(_AI_PAYLOAD_FINGERPRINT_KEY, None)
    _clear_ai_generated_result()


def _clear_ai_generated_result() -> None:
    """Remove an explanation when its reviewed payload is no longer current."""
    st.session_state.pop(_AI_RESPONSE_KEY, None)
    st.session_state.pop(_AI_RESPONSE_FINGERPRINT_KEY, None)


def _render_ai_explanation_result(
    response: AIExplanationResponse,
    t: Callable[..., str],
) -> None:
    """Render advisory structured output without changing local findings."""
    st.warning(t("ai.result.advisory"))
    st.markdown(f"### {t('ai.result.heading')}")
    st.markdown(f"#### {t('ai.result.summary')}")
    st.write(response.summary)
    st.markdown(f"#### {t('ai.result.prioritized')}")
    if response.prioritized_findings:
        st.dataframe(
            [
                {
                    t("ai.result.rule_id"): item.rule_id,
                    t("ai.result.priority"): item.priority,
                    t("ai.result.rationale"): item.rationale,
                }
                for item in response.prioritized_findings
            ],
            hide_index=True,
        )
    else:
        st.info(t("ai.result.no_prioritized"))
    st.markdown(f"#### {t('ai.result.explanation')}")
    st.write(response.explanation)
    st.markdown(f"#### {t('ai.result.suggested_checks')}")
    for check in response.suggested_checks:
        st.markdown(f"- {check}")
    st.caption(t("ai.result.confidence", confidence=response.confidence))
    st.markdown(f"#### {t('ai.result.limitations')}")
    for limitation in response.limitations:
        st.markdown(f"- {limitation}")


def _render_ai_review(
    result: object,
    selected_findings: list[Finding] | None,
    t: Callable[..., str],
) -> None:
    """Render a local-only payload preview and explicit future-send gate."""
    parsed = result.get("parsed") if isinstance(result, dict) else None
    report = result.get("report") if isinstance(result, dict) else None
    purpose = result.get("analysis_purpose") if isinstance(result, dict) else ""
    if not isinstance(parsed, ParsedModel) or not isinstance(report, AnalysisReport):
        st.info(t("ai.placeholder"))
        st.checkbox(t("ai.consent"), disabled=True, key=_AI_CONSENT_KEY)
        st.button(
            t("ai.generate"),
            disabled=True,
            help=t("ai.generate.help"),
            key=_AI_GENERATE_BUTTON_KEY,
        )
        return

    geometry = st.session_state.get(_GEOMETRY_RESULT_KEY)
    geometry_result = geometry if isinstance(geometry, GeometrySamplingResult) else None
    try:
        payload = build_ai_review_payload(
            analysis_purpose=purpose if isinstance(purpose, str) else "",
            report=report,
            parsed_model=parsed,
            selected_findings=selected_findings or [],
            geometry_result=geometry_result,
        )
    except (PayloadPrivacyError, ValueError):
        _clear_ai_review_state()
        st.error(t("ai.payload_error"))
        st.checkbox(t("ai.consent"), disabled=True, key=_AI_CONSENT_KEY)
        st.button(
            t("ai.generate"),
            disabled=True,
            help=t("ai.generate.help"),
            key=_AI_GENERATE_BUTTON_KEY,
        )
        return

    fingerprint = payload_fingerprint(payload)
    if st.session_state.get(_AI_PAYLOAD_FINGERPRINT_KEY) != fingerprint:
        _clear_ai_generated_result()
        st.session_state[_AI_PAYLOAD_FINGERPRINT_KEY] = fingerprint
        st.session_state[_AI_CONSENT_KEY] = False

    st.caption(t("ai.preview.caption"))
    st.json(payload.model_dump(mode="json"))
    st.caption(
        t(
            "ai.preview.findings",
            included=payload.findings.included_count,
            selected=payload.findings.selected_count,
        )
    )
    consent_confirmed = st.checkbox(t("ai.consent"), key=_AI_CONSENT_KEY)
    button_pressed = st.button(
        t("ai.generate"),
        disabled=not consent_confirmed,
        help=None if consent_confirmed else t("ai.generate.help"),
        key=_AI_GENERATE_BUTTON_KEY,
    )
    if ai_generation_requested(
        button_pressed=button_pressed,
        consent_confirmed=consent_confirmed,
        payload_available=True,
    ):
        _clear_ai_generated_result()
        try:
            with st.spinner(t("ai.spinner")):
                explanation = generate_ai_explanation(payload)
        except AIReviewServiceError as error:
            st.error(t(f"ai.error.{error.code}"))
        else:
            st.session_state[_AI_RESPONSE_KEY] = explanation
            st.session_state[_AI_RESPONSE_FINGERPRINT_KEY] = fingerprint

    stored_response = st.session_state.get(_AI_RESPONSE_KEY)
    stored_fingerprint = st.session_state.get(_AI_RESPONSE_FINGERPRINT_KEY)
    if (
        isinstance(stored_response, AIExplanationResponse)
        and stored_fingerprint == fingerprint
    ):
        _render_ai_explanation_result(stored_response, t)


def _render_external_references(
    language: SupportedLanguage,
    t: Callable[..., str],
) -> None:
    """Render sanitized resolution results and explicit local authorization."""
    st.markdown(f"### {t('reference.heading')}")
    st.caption(t("reference.intro"))
    report = st.session_state.get(_REFERENCE_RESULT_KEY)
    if not isinstance(report, ExternalResolutionReport):
        st.info(t("reference.before_run"))
        return

    if any(item.status == "pending_authorization" for item in report.references):
        st.info(t("reference.local.pending"))
        if st.button(t("reference.local.confirm"), type="primary"):
            local_project = st.session_state.get(_LOCAL_PROJECT_KEY)
            if isinstance(local_project, LocalProjectSource):
                with st.spinner(t("reference.local.spinner")):
                    report = local_project.resolve_pbed(authorize_supporting_files=True)
                st.session_state[_REFERENCE_RESULT_KEY] = report
                st.session_state.pop(_PBED_SLICE_RESULT_KEY, None)

    if report.references:
        st.caption(t("reference.summary", count=len(report.references)))
        st.dataframe(
            external_reference_table_rows(report, language),
            hide_index=True,
        )
    else:
        st.info(t("reference.none"))

    if report.unused_supporting_files:
        with st.expander(
            t("reference.unused", count=len(report.unused_supporting_files))
        ):
            for logical_name in report.unused_supporting_files:
                st.write(logical_name)

    diagnostics = list(report.diagnostics)
    diagnostics.extend(
        diagnostic
        for resolved in report.references
        for diagnostic in resolved.diagnostics
    )
    for diagnostic in diagnostics:
        location = diagnostic.source_name
        if diagnostic.line is not None:
            location = f"{location}:{diagnostic.line}"
        if diagnostic.record_number is not None:
            location = f"{location} (record {diagnostic.record_number})"
        label = t(
            "reference.diagnostic.label",
            rule_id=diagnostic.rule_id,
            code=diagnostic.code,
            location=location,
        )
        display = t(
            "reference.diagnostic.display",
            label=label,
            message=localized_reference_diagnostic_message(diagnostic, language),
        )
        if diagnostic.severity == "ERROR":
            st.error(display)
        elif diagnostic.severity == "WARNING":
            st.warning(display)
        else:
            st.info(display)

    _render_pbed_visualization(report, language, t)


def _render_pbed_visualization(
    report: ExternalResolutionReport,
    language: SupportedLanguage,
    t: Callable[..., str],
) -> None:
    """Render verified placement summaries and an explicit sphere cross-section."""
    candidates = [
        resolved
        for resolved in report.references
        if resolved.pbed_data is not None and resolved.pbed_data.valid_record_count > 0
    ]
    if not candidates:
        return

    st.markdown(f"#### {t('pbed.heading')}")
    st.warning(t("pbed.slice.warning"))
    option_ids = [
        f"{item.reference.source_line}:{item.reference.target_name}"
        for item in candidates
    ]
    stored_target = st.session_state.get(_PBED_TARGET_KEY)
    if stored_target not in option_ids:
        st.session_state.pop(_PBED_TARGET_KEY, None)
    selected_id = st.selectbox(
        t("pbed.slice.target"),
        options=option_ids,
        format_func=lambda item_id: (
            candidates[option_ids.index(item_id)].reference.target_name
        ),
        key=_PBED_TARGET_KEY,
    )
    selected = candidates[option_ids.index(selected_id)]
    data = selected.pbed_data
    if data is None:  # pragma: no cover - candidates invariant
        return

    st.caption(
        t(
            "pbed.summary",
            valid=data.valid_record_count,
            invalid=data.invalid_record_count,
        )
    )
    bounds = data.bounding_box
    if bounds is None:
        st.info(t("pbed.no_bounding_box"))
    else:
        st.caption(
            t(
                "pbed.bounding_box",
                xmin=f"{bounds.xmin:.8g}",
                xmax=f"{bounds.xmax:.8g}",
                ymin=f"{bounds.ymin:.8g}",
                ymax=f"{bounds.ymax:.8g}",
                zmin=f"{bounds.zmin:.8g}",
                zmax=f"{bounds.zmax:.8g}",
            )
        )

    mode = st.radio(
        t("pbed.view.mode"),
        options=("slice", "projection"),
        format_func=lambda value: t(f"pbed.view.{value}"),
        horizontal=True,
        key=_PBED_MODE_KEY,
    )
    with st.form("serpentguard_pbed_slice_form"):
        z_value = st.number_input(
            t("pbed.slice.z"),
            value=0.0,
            format="%.8g",
            key=_PBED_Z_KEY,
            disabled=mode == "projection",
        )
        render_requested = st.form_submit_button(t(f"pbed.{mode}.run"))

    if render_requested:
        slice_result = (
            slice_pbed_placements(data, z=float(z_value))
            if mode == "slice"
            else project_pbed_centers(data)
        )
        st.session_state[_PBED_SLICE_RESULT_KEY] = {
            "target_id": selected_id,
            "mode": mode,
            "result": slice_result,
        }

    stored_slice = st.session_state.get(_PBED_SLICE_RESULT_KEY)
    if (
        not isinstance(stored_slice, dict)
        or stored_slice.get("target_id") != selected_id
        or stored_slice.get("mode") != mode
    ):
        return
    slice_result = stored_slice.get("result")
    if not isinstance(slice_result, PbedSliceResult):
        return

    if slice_result.mode == "slice":
        st.caption(
            t(
                "pbed.slice.summary",
                intersecting=slice_result.intersecting_placement_count,
                total=slice_result.total_placement_count,
                z=f"{slice_result.z:.8g}",
            )
        )
    else:
        st.caption(
            t("pbed.projection.summary", total=slice_result.total_placement_count)
        )
    if not slice_result.circles:
        st.info(t("pbed.slice.none"))
        return
    if len(slice_result.circles) > _MAX_PBED_PLOT_CIRCLES:
        st.warning(
            t(
                "pbed.slice.limit",
                count=len(slice_result.circles),
                limit=_MAX_PBED_PLOT_CIRCLES,
            )
        )
        return
    pbed_font = select_plot_font(language)
    pbed_plot_language = language
    if language == JAPANESE and not pbed_font.supports_japanese:
        st.warning(t("geometry.font.warning"))
        pbed_plot_language = ENGLISH
        pbed_font = select_plot_font(ENGLISH)
    pbed_t = partial(translate, language=pbed_plot_language)
    title = (
        pbed_t("pbed.slice.title", z=f"{slice_result.z:.8g}")
        if slice_result.mode == "slice"
        else pbed_t("pbed.projection.title")
    )
    figure = create_pbed_slice_figure(
        slice_result,
        title=title,
        font=pbed_font,
        universe_label=pbed_t("pbed.universe"),
    )
    st.pyplot(figure, use_container_width=True)
    close_figure(figure)


def _render_geometry_sampler(
    parsed: ParsedModel,
    language: SupportedLanguage,
    t: Callable[..., str],
) -> None:
    """Render the explicit geometry form and any canonical sampling result."""
    universes = available_universes(parsed)
    default_universe = default_target_universe(parsed)
    if not universes or default_universe is None:
        st.error(t("geometry.no_universes"))
        return

    stored_universe = st.session_state.get("serpentguard_geometry_universe")
    if stored_universe not in universes:
        st.session_state.pop("serpentguard_geometry_universe", None)

    st.info(t("geometry.intro"))
    st.caption(t("geometry.local_coordinates"))
    if "0" not in universes:
        st.info(t("geometry.universe.defaulted", universe=default_universe))
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
        target_universe = st.selectbox(
            t("geometry.form.universe"),
            options=universes,
            index=universes.index(default_universe),
            key="serpentguard_geometry_universe",
        )
        slice_columns = st.columns(3)
        z_value = slice_columns[0].number_input(
            t("geometry.form.z"),
            value=0.0,
            format="%.6f",
            disabled=True,
            help=t("geometry.form.z_help"),
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
        st.caption(t("geometry.form.z_help"))
        st.caption(
            t(
                "geometry.workload.help",
                limit=f"{DEFAULT_MAX_GEOMETRY_WORKLOAD:,}",
            )
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
                target_universe=target_universe,
                boundary_tolerance=float(boundary_tolerance),
            )
            with st.spinner(t("geometry.spinner")):
                geometry_result = sample_geometry(parsed, config)
        except GeometryWorkloadError as error:
            estimate = error.estimate
            st.error(
                t(
                    "geometry.workload_error",
                    operations=f"{estimate.estimated_operations:,}",
                    limit=f"{error.limit:,}",
                    points=f"{estimate.grid_point_count:,}",
                    cells=estimate.evaluated_cell_count,
                    references=estimate.signed_reference_count,
                )
            )
        except GeometryConfigError as error:
            st.error(t("geometry.config_error", message=error))
        else:
            st.session_state[_GEOMETRY_RESULT_KEY] = geometry_result

    geometry_result = st.session_state.get(_GEOMETRY_RESULT_KEY)
    if not isinstance(geometry_result, GeometrySamplingResult):
        return

    config = geometry_result.config
    st.caption(
        t(
            "geometry.universe.selected",
            universe=geometry_result.selected_universe,
        )
    )
    st.caption(
        t(
            "geometry.summary",
            universe=geometry_result.selected_universe,
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
            included=geometry_result.supported_cell_count,
            excluded=geometry_result.excluded_cell_count,
            references=geometry_result.signed_reference_count,
            workload=f"{geometry_result.workload.estimated_operations:,}",
        )
    )
    if geometry_result.coverage_complete:
        st.success(t("geometry.coverage.complete"))
    else:
        st.warning(
            t(
                "geometry.coverage.incomplete",
                excluded=geometry_result.excluded_cell_count,
            )
        )
        st.warning(
            t(
                "geometry.undefined.disabled",
                count=geometry_result.incomplete_domain_count,
            )
        )
        if any(
            reason.code == "duplicate_cell_name"
            for cell in geometry_result.excluded_cells
            for reason in cell.reasons
        ):
            st.warning(t("geometry.duplicate.warning"))
    if not geometry_result.included_cells:
        st.warning(t("geometry.no_included_cells"))

    overlap_metric_key = (
        "geometry.metric.overlap"
        if geometry_result.coverage_complete
        else "geometry.metric.overlap_incomplete"
    )
    normal_metric_key = (
        "geometry.metric.normal"
        if geometry_result.coverage_complete
        else "geometry.metric.normal_incomplete"
    )
    metric_columns = st.columns(4)
    metric_columns[0].metric(t(overlap_metric_key), geometry_result.overlap_count)
    metric_columns[1].metric(
        t("geometry.metric.undefined"), geometry_result.undefined_count
    )
    metric_columns[2].metric(t(normal_metric_key), geometry_result.normal_count)
    metric_columns[3].metric(
        t("geometry.metric.indeterminate"), geometry_result.indeterminate_count
    )

    undefined_key = (
        "geometry.classification.undefined"
        if geometry_result.undefined_detection_enabled
        else "geometry.classification.undefined_disabled"
    )
    plot_font = select_plot_font(language)
    plot_language = language
    if language == JAPANESE and not plot_font.supports_japanese:
        st.warning(t("geometry.font.warning"))
        plot_language = ENGLISH
        plot_font = select_plot_font(ENGLISH)
    plot_t = partial(translate, language=plot_language)

    geometry_tab, diagnostic_tab = st.tabs(
        [t("geometry.view.geometry"), t("geometry.view.diagnostic")]
    )
    with geometry_tab:
        color_by = st.radio(
            t("geometry.color_by.label"),
            options=("material", "cell"),
            format_func=lambda value: t(f"geometry.color_by.{value}"),
            horizontal=True,
            key="serpentguard_geometry_color_by",
        )
        has_serpent_rgb = any(
            category.serpent_rgb is not None
            for category in geometry_result.material_categories
        )
        use_serpent_rgb = False
        if color_by == "material" and has_serpent_rgb:
            use_serpent_rgb = st.checkbox(
                t("geometry.color.serpent_rgb"),
                key="serpentguard_geometry_use_serpent_rgb",
            )
        if not use_serpent_rgb:
            st.caption(t("geometry.color.application_note"))
        geometry_figure = create_geometry_view_figure(
            geometry_result,
            color_by=color_by,
            title=plot_t(
                "geometry.plot.geometry_title",
                universe=geometry_result.selected_universe,
            ),
            special_labels={
                "outside": plot_t("geometry.category.outside"),
                "void": plot_t("geometry.category.void"),
                "unsupported": plot_t("geometry.category.unsupported"),
                "indeterminate": plot_t("geometry.category.indeterminate"),
                "undefined": plot_t("geometry.category.undefined"),
            },
            use_serpent_rgb=use_serpent_rgb,
            font=plot_font,
        )
        st.pyplot(geometry_figure, use_container_width=True)
        close_figure(geometry_figure)

    with diagnostic_tab:
        st.caption(t("geometry.diagnostic.caption"))
        diagnostic_figure = create_diagnostic_figure(
            geometry_result,
            title=plot_t(
                "geometry.plot.diagnostic_title",
                universe=geometry_result.selected_universe,
            ),
            classification_labels={
                classification: plot_t_key
                for classification, plot_t_key in (
                    (PointClassification.UNDEFINED, plot_t(undefined_key)),
                    (
                        PointClassification.NORMAL,
                        plot_t("geometry.classification.normal"),
                    ),
                    (
                        PointClassification.OVERLAP,
                        plot_t(
                            "geometry.classification.overlap"
                            if geometry_result.coverage_complete
                            else "geometry.classification.overlap_incomplete"
                        ),
                    ),
                    (
                        PointClassification.INCOMPLETE,
                        plot_t("geometry.classification.incomplete"),
                    ),
                    (
                        PointClassification.BOUNDARY,
                        plot_t("geometry.classification.boundary"),
                    ),
                )
            },
            font=plot_font,
        )
        st.pyplot(diagnostic_figure, use_container_width=True)
        close_figure(diagnostic_figure)

        representative_columns = st.columns(2)
        representative_sets = (
            (
                representative_columns[0],
                (
                    "geometry.representatives.overlap"
                    if geometry_result.coverage_complete
                    else "geometry.representatives.overlap_incomplete"
                ),
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
            elif (
                heading_key == "geometry.representatives.undefined"
                and not geometry_result.undefined_detection_enabled
            ):
                column.info(
                    t(
                        "geometry.undefined.disabled",
                        count=geometry_result.incomplete_domain_count,
                    )
                )
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
source_mode = st.radio(
    t("source.mode.label"),
    options=("uploaded_bundle", "local_project"),
    format_func=lambda mode: t(f"source.mode.{mode}"),
    horizontal=True,
    key=_SOURCE_MODE_KEY,
    on_change=_clear_previous_result,
)
main_input = None
supporting_files = []
local_main_path = ""
local_root_path = ""
if source_mode == "uploaded_bundle":
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
        on_change=_clear_previous_result,
    )
    if supporting_files:
        st.caption(t("upload.supporting.caption", count=len(supporting_files)))
else:
    local_main_path = st.text_input(
        t("local.main.label"),
        help=t("local.main.help"),
        key="serpentguard_local_main_path",
        on_change=_clear_previous_result,
    )
    local_root_path = st.text_input(
        t("local.root.label"),
        help=t("local.root.help"),
        key="serpentguard_local_root_path",
        on_change=_clear_previous_result,
    )

st.subheader(t("section.purpose"))
analysis_purpose = st.text_area(
    t("purpose.label"),
    placeholder=t("purpose.placeholder"),
    help=t("purpose.help"),
)

st.subheader(t("section.run"))
run_disabled = (
    main_input is None
    if source_mode == "uploaded_bundle"
    else not local_main_path.strip() or not local_root_path.strip()
)
run_check = st.button(
    t("run.button"),
    type="primary",
    disabled=run_disabled,
    help=t("run.help.upload" if source_mode == "uploaded_bundle" else "run.help.local"),
)

if run_check:
    try:
        with st.spinner(t("run.spinner")):
            local_project: LocalProjectSource | None = None
            if source_mode == "uploaded_bundle" and main_input is not None:
                bundle = UploadedSourceBundle(
                    main_name=main_input.name,
                    main_content=main_input.getvalue(),
                    supporting_files=[
                        (support.name, support.getvalue())
                        for support in supporting_files
                    ],
                )
                main_bytes = bundle.read_main_bytes()
                file_name = bundle.main.logical_name
                reference_report = bundle.resolve_pbed()
            else:
                local_project = LocalProjectSource(
                    main_path=local_main_path.strip(),
                    authorized_root=local_root_path.strip(),
                )
                main_bytes = local_project.read_main_bytes()
                file_name = local_project.main.logical_name
                reference_report = local_project.preview_pbed()

            parsed = parse_bytes(main_bytes, file_name=file_name)
            report = analyze_model(parsed)
    except ReferencePolicyError as error:
        st.error(
            t(
                "reference.local.error",
                message=t(f"reference.policy.{error.code}"),
            )
        )
    else:
        _clear_ai_review_state()
        st.session_state.pop(_GEOMETRY_RESULT_KEY, None)
        st.session_state.pop(_PBED_SLICE_RESULT_KEY, None)
        st.session_state[_REFERENCE_RESULT_KEY] = reference_report
        if local_project is None:
            st.session_state.pop(_LOCAL_PROJECT_KEY, None)
        else:
            st.session_state[_LOCAL_PROJECT_KEY] = local_project
        st.session_state[_RESULT_KEY] = {
            "file_name": file_name,
            "analysis_purpose": analysis_purpose.strip(),
            "parsed": parsed,
            "report": report,
        }

result = st.session_state.get(_RESULT_KEY)
ai_selected_findings: list[Finding] | None = None

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

        object_columns = st.columns(6)
        object_columns[0].metric(t("metric.surfaces"), report.model_summary["surfaces"])
        object_columns[1].metric(t("metric.cells"), report.model_summary["cells"])
        object_columns[2].metric(
            t("metric.materials"), report.model_summary["materials"]
        )
        object_columns[3].metric(
            t("metric.energy_grids"), report.model_summary["energy_grids"]
        )
        object_columns[4].metric(
            t("metric.detectors"), report.model_summary["detectors"]
        )
        object_columns[5].metric(
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
    ai_selected_findings = filtered_findings

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

_render_external_references(language, t)

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
_render_ai_review(result, ai_selected_findings, t)
