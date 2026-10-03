import streamlit as st

from core.state import init_state, skill_matrix_dict, employee_line_dict, employee_names_dict
from core.orchestrate import run_single_line, run_multi_line
from core.render import units_to_table, style_table, render_manual_assignment_ui

st.set_page_config(page_title="Layout Balancing", page_icon="⚖️", layout="wide")
init_state()
st.title("⚖️ Layout Balancing")

obs = st.session_state["obs"]
missing = []
if not obs:
    missing.append("an Operation Breakdown (Data Import)")
if st.session_state["employees_df"] is None:
    missing.append("Employees (Data Import)")
if st.session_state["skill_matrix_long"] is None:
    missing.append("Skill Matrix (Data Import)")
if not st.session_state["lines"]:
    missing.append("at least one Line (Lines page)")

if missing:
    st.warning("Still needed:\n\n" + "\n".join(f"- {m}" for m in missing))
    st.stop()

mode = st.radio("Mode", options=["Single Line", "Multiple Lines"], horizontal=True)

ob_name = st.selectbox("Operation Breakdown", options=list(obs.keys()))
ob = obs[ob_name]
ob_lines = st.session_state["lines"]

skill_matrix = skill_matrix_dict(ob_rows=ob["rows"])
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
        rows = ob["rows"]
        with st.spinner("Balancing..."):
            calcs, units = run_single_line(line, rows, shift_time, target, plan_efficiency, skill_matrix, employee_line)
        op_lookup = {c.operation: (c.machine_type, c.sam) for c in calcs}
        st.session_state["lb_result"] = (units, op_lookup)
        st.session_state["lb_overrides"] = {}

else:
    lines = st.multiselect("Lines", options=ob_lines, default=ob_lines)
    if st.button("Run Layout Balancing", type="primary", disabled=len(lines) < 2):
        rows_by_line = {line: ob["rows"] for line in lines}
        with st.spinner("Balancing across lines..."):
            calcs_by_line, units = run_multi_line(lines, rows_by_line, shift_time, target, plan_efficiency, skill_matrix, employee_line)
        op_lookup = {}
        for calcs in calcs_by_line.values():
            op_lookup.update({c.operation: (c.machine_type, c.sam) for c in calcs})
        st.session_state["lb_result"] = (units, op_lookup)
        st.session_state["lb_overrides"] = {}
    if len(lines) < 2:
        st.caption("Pick at least two lines for multi-line balancing.")

result = st.session_state.get("lb_result")
if result:
    units, op_lookup = result
    st.divider()

    overrides = st.session_state.get("lb_overrides", {})
    merged = [u for u in units if u.color_key != "unmerged"]
    cross = [u for u in units if u.cross_line]

    df, color_map = units_to_table(units, op_lookup, employee_names, manual_overrides=overrides)

    still_unstaffed = (df["Employee Code"] == "").sum()
    if still_unstaffed:
        st.error(f"{still_unstaffed} assignment(s) still have no employee assigned.")
    else:
        st.success("Every operation is staffed.")
    st.caption(f"{len(merged)} operator(s) assigned to more than one operation. {len(cross)} working across lines.")

    st.dataframe(style_table(df, color_map), width='stretch', hide_index=True)

    csv = df.drop(columns=["_color_key", "_row_index", "_unit_id"]).to_csv(index=False).encode("utf-8")
    st.download_button("Download result (CSV)", csv, file_name="layout_balancing_result.csv", mime="text/csv")

    render_manual_assignment_ui(df, st.session_state.get("employees_df"), "lb_overrides")
