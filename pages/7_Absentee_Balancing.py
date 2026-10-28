import streamlit as st

import core.db as db
from core.context import build_context
from core.importers import read_any
from core.line_setup import combined_rows, select_line_styles
from core.orchestrate import run_multi_line
from core.results import RunResult
from core.results_view import render_results, store_result
from core.state import employee_line_dict, init_state, list_lines, list_obs
from core.ui import page_header

init_state()
page_header("Absentee Balancing", "Re-balance multiple lines using only the people present today.")

obs = list_obs()
missing = []
if not obs:
    missing.append("an Operation Breakdown (Data Import)")
if db.list_employees() is None:
    missing.append("Employees (Data Import)")
if db.list_skill_pairs() is None:
    missing.append("Skill Matrix (Data Import)")
if not list_lines():
    missing.append("at least one Line (Lines page)")
if missing:
    st.warning("Still needed:\n\n" + "\n".join(f"- {m}" for m in missing))
    st.stop()

ob_lines = list_lines()
all_employees = sorted(employee_line_dict())

with st.container(border=True):
    st.markdown("**1 · Lines and styles**")
    lines = st.pills("Lines", options=ob_lines, selection_mode="multi", default=ob_lines, key="ab_lines") or []
    setups, shift_time = select_line_styles("ab", lines, obs) if lines else ([], 480.0)

with st.container(border=True):
    st.markdown("**2 · Who is present today?**")
    mode = st.segmented_control("Attendance", ["Upload attendance file", "Pick manually"],
                                default="Pick manually", key="ab_attendance_mode")
    present: set | None = None
    if mode == "Upload attendance file":
        file = st.file_uploader("Attendance (.xlsx or .csv) — any row in the chosen ID column counts as present",
                                type=["xlsx", "csv"])
        if file:
            raw = read_any(file)
            id_col = st.selectbox("Employee ID column", options=list(raw.columns))
            present = set(raw[id_col].astype(str))
    else:
        present = set(st.multiselect("Present employees", options=all_employees, default=all_employees))

if present is not None:
    st.caption(f"{len(present)} of {len(all_employees)} employees marked present.")
    if st.button("Run absentee balancing", type="primary", disabled=len(lines) < 2, icon=":material/play_arrow:"):
        with st.spinner("Balancing across lines with present employees only..."):
            ctx = build_context(combined_rows(setups), present=present)
            _, units = run_multi_line(
                lines, {s.line: s.rows for s in setups}, shift_time,
                {s.line: s.target for s in setups}, {s.line: s.plan_efficiency for s in setups},
                ctx.evidence, ctx.employee_line,
            )
        store_result("ab", RunResult(
            units=units, line_order=lines, context=ctx,
            ob_by_line={s.line: s.ob_name for s in setups}, ob_row_ids={s.line: s.row_ids for s in setups},
        ))
    if len(lines) < 2:
        st.caption("Pick at least two lines.")

    render_results(prefix="ab", employees_df=db.list_employees(), file_stem="absentee_balancing_result")
