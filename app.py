"""Minimal Streamlit shell for the SerpentGuard foundation phase."""

import streamlit as st

st.set_page_config(page_title="SerpentGuard")

st.title("SerpentGuard")
st.warning(
    "Experimental tool: no checks are implemented yet. Do not use it as the sole "
    "basis for reactor-safety or criticality-safety decisions."
)
st.file_uploader(
    "Serpent input file",
    disabled=True,
    help="File handling will be added with the deterministic checker.",
)
st.button(
    "Run check",
    disabled=True,
    help="Deterministic checks are not implemented yet.",
)
