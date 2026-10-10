import streamlit as st

import core.db as db
from core.orchestrate import run_multi_line, run_single_line
from core.results import RunResult
from core.results_view import render_results, store_result
from core.state import (
    employee_line_dict, employee_names_dict, employee_skill_profiles, get_ob,
    init_state, list_lines, list_obs, skill_matrix_dict,
)

st.set_page_config(page_title="Layout Balancing", page_icon="⚖️", layout="wide")
init_state()
st.title("⚖️ Layout Balancing")

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

mode = st.radio("Mode", options=["Single Line", "Multiple Lines"], horizontal=True)
ob_name = st.selectbox("Operation Breakdown", options=obs)
ob = get_ob(ob_name)
ob_lines = list_lines()

skill_matrix = skill_matrix_dict(ob_rows=ob["rows"])
profiles = employee_skill_profiles(ob_rows=ob["rows"])
employee_line = employee_line_dict()
employee_names = employee_names_dict()

c1, c2, c3 = st.columns(3)
with c1:
    shift_time = st.number_input("Shift Time (minutes)", min_value=1.0, value=float(ob["shift_time"]), key="lb_shift")
with c2:
    target = st.number_input("Target (units/shift)", min_value=1.0, value=float(ob["target"]), key="lb_target")
with c3:
    plan_efficiency = st.number_input("Plan Efficiency", min_value=0.01, max_value=1.0, value=float(ob["plan_efficiency"]), key="lb_eff")
st.caption("These can differ from the OB's original defaults — a specific line/run may target different numbers.")

if mode == "Single Line":
    line = st.selectbox("Line", options=ob_lines)
    if st.button("Run Layout Balancing", type="primary"):
        with st.spinner("Balancing..."):
            _, units = run_single_line(line, ob["rows"], shift_time, target, plan_efficiency, skill_matrix, employee_line)
        store_result("lb", RunResult(units=units, line_order=[line]))
else:
    lines = st.multiselect("Lines", options=ob_lines, default=ob_lines)
    if st.button("Run Layout Balancing", type="primary", disabled=len(lines) < 2):
        with st.spinner("Balancing across lines..."):
            _, units = run_multi_line(
                lines, {ln: ob["rows"] for ln in lines}, shift_time, target, plan_efficiency, skill_matrix, employee_line
            )
        store_result("lb", RunResult(units=units, line_order=lines))
    if len(lines) < 2:
        st.caption("Pick at least two lines for multi-line balancing.")

render_results(
    prefix="lb",
    employees_df=db.list_employees(),
    skill_matrix=skill_matrix,
    employee_line=employee_line,
    employee_names=employee_names,
    profiles=profiles,
    file_stem="layout_balancing_result",
)
