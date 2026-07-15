"""Local Streamlit interface for deterministic SerpentGuard analysis."""

from __future__ import annotations

import streamlit as st

from serpentguard.analysis import analyze_model, has_unrecoverable_parse_failure
from serpentguard.models import AnalysisReport, ParsedModel
from serpentguard.parser import parse_bytes
from serpentguard.ui import (
    SEVERITY_ORDER,
    available_rule_ids,
    filter_findings,
    findings_table_rows,
    parsed_model_debug_payload,
    severity_counts,
)

_RESULT_KEY = "serpentguard_analysis_result"
_SEVERITY_FILTER_KEY = "serpentguard_severity_filter"
_RULE_FILTER_KEY = "serpentguard_rule_filter"


def _clear_previous_result() -> None:
    st.session_state.pop(_RESULT_KEY, None)
    st.session_state.pop(_SEVERITY_FILTER_KEY, None)
    st.session_state.pop(_RULE_FILTER_KEY, None)


st.set_page_config(page_title="SerpentGuard", layout="wide")

st.title("SerpentGuard")
st.warning(
    "Experimental tool: SerpentGuard covers only a limited syntax subset and does "
    "not establish geometric, physical, reactor-safety, or criticality-safety "
    "validity. Review every finding independently."
)
st.info(
    "Analysis is local. Uploaded input is parsed in this Streamlit process and is "
    "not sent to an AI service."
)

st.subheader("1. Upload Serpent input")
main_input = st.file_uploader(
    "Main input file",
    help="Upload one UTF-8 Serpent input file for deterministic local analysis.",
    key="serpentguard_main_input",
    on_change=_clear_previous_result,
)
supporting_files = st.file_uploader(
    "Supporting files (optional)",
    accept_multiple_files=True,
    help=(
        "These files are accepted for workflow preparation only. Include resolution "
        "is not implemented, so they are not opened or analyzed."
    ),
    key="serpentguard_supporting_inputs",
)
if supporting_files:
    st.caption(
        f"{len(supporting_files)} supporting file(s) selected. "
        "They will not be opened in this milestone."
    )

st.subheader("2. Analysis purpose")
analysis_purpose = st.text_area(
    "Purpose (optional)",
    placeholder="For example: preflight review before a local Serpent run",
    help=(
        "This note stays local and does not change deterministic findings in this "
        "milestone."
    ),
)

st.subheader("3. Run check")
run_check = st.button(
    "Run check",
    type="primary",
    disabled=main_input is None,
    help="Upload a main input file to enable deterministic analysis.",
)

if run_check and main_input is not None:
    with st.spinner("Parsing and running deterministic checks..."):
        parsed = parse_bytes(main_input.getvalue(), file_name=main_input.name)
        report = analyze_model(parsed)
        st.session_state[_RESULT_KEY] = {
            "file_name": main_input.name,
            "analysis_purpose": analysis_purpose.strip(),
            "parsed": parsed,
            "report": report,
        }

result = st.session_state.get(_RESULT_KEY)

st.subheader("4. Summary counts")
if result is None:
    st.info("Upload a main input file and press Run check to generate a summary.")
else:
    parsed = result["parsed"]
    report = result["report"]
    if not isinstance(parsed, ParsedModel) or not isinstance(report, AnalysisReport):
        st.error("The stored analysis result is invalid. Please upload the file again.")
    else:
        if has_unrecoverable_parse_failure(parsed):
            st.error(
                "The uploaded file could not be parsed. Confirm that it is a readable "
                "UTF-8 text file, then run the check again."
            )
        elif any(
            finding.rule_id in {"SG011", "SG015"} and finding.severity == "ERROR"
            for finding in report.findings
        ):
            st.error(
                "Parsing completed with recoverable syntax errors. Parsed counts may "
                "be incomplete; review SG011 and SG015 findings below."
            )

        object_columns = st.columns(4)
        object_columns[0].metric("Surfaces", report.model_summary["surfaces"])
        object_columns[1].metric("Cells", report.model_summary["cells"])
        object_columns[2].metric("Materials", report.model_summary["materials"])
        object_columns[3].metric("Unknown cards", report.model_summary["unknown_cards"])

        counts = severity_counts(report.findings)
        severity_columns = st.columns(4)
        for column, severity in zip(severity_columns, SEVERITY_ORDER, strict=True):
            column.metric(severity, counts[severity])

st.subheader("5. Findings table")
if result is None:
    st.info("Findings will appear after Run check is pressed.")
elif isinstance(result.get("parsed"), ParsedModel) and isinstance(
    result.get("report"), AnalysisReport
):
    parsed = result["parsed"]
    report = result["report"]
    rule_ids = available_rule_ids(report.findings)
    filter_columns = st.columns(2)
    selected_severities = filter_columns[0].multiselect(
        "Severity",
        options=list(SEVERITY_ORDER),
        default=list(SEVERITY_ORDER),
        key=_SEVERITY_FILTER_KEY,
    )
    selected_rule_ids = filter_columns[1].multiselect(
        "Rule ID",
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
            findings_table_rows(filtered_findings),
            hide_index=True,
        )
        st.caption(
            f"Showing {len(filtered_findings)} of {len(report.findings)} findings."
        )
        for finding_number, finding in enumerate(filtered_findings, start=1):
            object_label = finding.object_name or finding.object_type or "input"
            with st.expander(
                f"Evidence {finding_number}: {finding.rule_id} — {object_label}"
            ):
                st.json(finding.evidence)
    elif report.findings:
        st.info("No findings match the selected filters.")
    else:
        st.success("No deterministic findings were produced for the supported subset.")

    with st.expander("Parsed model JSON (debugging)"):
        st.caption("Raw card text is omitted from this debugging view.")
        st.json(parsed_model_debug_payload(parsed))

st.subheader("6. Geometry plot")
st.info("Geometry checking is not implemented in this milestone.")

st.subheader("7. AI explanation")
st.info("AI review is optional and has not been enabled in this milestone.")
