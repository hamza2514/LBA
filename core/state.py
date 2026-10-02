"""Central session-state shape, so every page reads/writes the same keys."""
from __future__ import annotations

import streamlit as st


def init_state():
    defaults = {
        "lines": [],              # list[str]
        "obs": {},                # {ob_name: {"rows": [...], "shift_time", "target", "plan_efficiency"}}
        "employees_df": None,     # DataFrame: employee_id, employee_name, line
        "skill_matrix_long": None,  # DataFrame: employee, skill_group
        "extra_taxonomy": [],     # list[dict] — session-added skill groups (see matching.py)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def skill_matrix_dict() -> dict:
    """{employee: set(skill_group)} built from the long-format upload."""
    sdf = st.session_state.get("skill_matrix_long")
    if sdf is None:
        return {}
    out: dict = {}
    for _, r in sdf.iterrows():
        out.setdefault(str(r["employee"]), set()).add(str(r["skill_group"]))
    return out


def employee_line_dict() -> dict:
    """{employee: line} built from the employee list."""
    edf = st.session_state.get("employees_df")
    if edf is None:
        return {}
    return {str(r["employee_id"]): str(r["line"]) for _, r in edf.iterrows()}


def employee_names_dict() -> dict:
    """{employee_id: employee_name} built from the employee list."""
    edf = st.session_state.get("employees_df")
    if edf is None:
        return {}
    return {str(r["employee_id"]): str(r["employee_name"]) for _, r in edf.iterrows()}


def add_line(name: str):
    name = name.strip()
    if name and name not in st.session_state["lines"]:
        st.session_state["lines"].append(name)


def ensure_lines_registered(values: list[str]):
    """Auto-register any line names seen in an upload that aren't in the
    Lines list yet, so the two never silently drift apart."""
    for v in values:
        add_line(str(v))
