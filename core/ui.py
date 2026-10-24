"""Shared look & feel: one stylesheet injected on every page."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 1500px; }
h1 { font-weight: 700; letter-spacing: -0.02em; }
h2, h3 { font-weight: 650; letter-spacing: -0.01em; }
[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;
    padding: 14px 16px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
[data-testid="stMetricLabel"] p { color: #64748B; font-size: 0.8rem; }
.stButton > button, .stDownloadButton > button { border-radius: 10px; font-weight: 600; }
[data-testid="stSidebar"] { border-right: 1px solid #E2E8F0; }
div[data-testid="stDataFrame"] { border: 1px solid #E2E8F0; border-radius: 12px; overflow: hidden; }
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def warn_missing_sections(ob_rows: list[dict], name: str = "") -> None:
    """Operations without a section are never merged — tell the user why."""
    prefix = f"'{name}': " if name else ""
    missing = sum(1 for r in ob_rows if not r.get("section"))
    if not missing:
        return
    if missing == len(ob_rows):
        st.warning(prefix + "This Operation Breakdown has no line sections, so no operations will be merged. "
                   "Re-import it from the original file (Data Import) so sections are detected.")
    else:
        st.warning(f"{prefix}{missing} operation(s) have no section and will not be merged with others.")
