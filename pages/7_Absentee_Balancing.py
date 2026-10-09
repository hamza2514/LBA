import streamlit as st

from core.state import init_state, skill_matrix_dict, employee_line_dict, employee_names_dict, list_obs, get_ob, list_lines
from core.evidence import build_staffing_evidence, diagnose_unstaffed
from core.orchestrate import run_multi_line
from core.render import units_to_table, style_table, render_manual_assignment_ui
from core.importers import read_any
import core.db as db

st.set_page_config(page_title="Absentee Balancing", page_icon="🧍", layout="wide")
init_state()
st.title("🧍 Absentee Balancing")
st.caption("Always multi-line, same engine as Layout Balancing's multi-line mode — restricted to whoever's actually present today.")

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

ob_name = st.selectbox("Operation Breakdown", options=obs)
ob = get_ob(ob_name)
ob_lines = list_lines()
lines = st.multiselect("Lines", options=ob_lines, default=ob_lines)

all_skill_matrix = skill_matrix_dict(ob_rows=ob["rows"])
all_evidence = build_staffing_evidence(ob["rows"], all_skill_matrix)
all_employee_line = employee_line_dict()
employee_names = employee_names_dict()
all_employees = sorted(all_employee_line.keys())

st.subheader("Who's present today?")
mode = st.radio("How do you want to mark attendance?", options=["Upload attendance file", "Pick present employees manually"], horizontal=True)

present = None
if mode == "Upload attendance file":
    file = st.file_uploader("Upload attendance (.xlsx or .csv) — any column containing the employee ID marks them present", type=["xlsx", "csv"])
    if file:
        raw = read_any(file)
        st.dataframe(raw.head(10), width='stretch')
        id_col = st.selectbox("Which column has the Employee ID?", options=list(raw.columns))
        present = set(raw[id_col].astype(str))
else:
    present = set(st.multiselect("Present employees", options=all_employees, default=all_employees))

if present is not None:
    st.caption(f"{len(present)} employee(s) marked present out of {len(all_employees)} total.")

    evidence = all_evidence.restrict_to(present)
    employee_line = {e: line for e, line in all_employee_line.items() if e in present}

    if st.button("Run Absentee Balancing", type="primary", disabled=len(lines) < 2):
        rows_by_line = {line: ob["rows"] for line in lines}
        with st.spinner("Balancing across lines with present employees only..."):
            calcs_by_line, units = run_multi_line(
                lines, rows_by_line, float(ob["shift_time"]), float(ob["target"]), float(ob["plan_efficiency"]),
                evidence, employee_line,
            )
        op_lookup = {}
        for calcs in calcs_by_line.values():
            op_lookup.update({c.operation: (c.machine_type, c.sam) for c in calcs})
        st.session_state["ab_result"] = (units, op_lookup, evidence)
        st.session_state["ab_overrides"] = {}
    if len(lines) < 2:
        st.caption("Pick at least two lines.")

result = st.session_state.get("ab_result")
if result:
    units, op_lookup, run_evidence = result
    st.divider()

    overrides = st.session_state.get("ab_overrides") or {}
    merged = [u for u in units if u.color_key != "unmerged"]
    cross = [u for u in units if u.cross_line]

    df, color_map = units_to_table(units, op_lookup, employee_names, manual_overrides=overrides)

    still_unstaffed = (df["Employee Code"] == "").sum()
    if still_unstaffed:
        st.error(f"{still_unstaffed} assignment(s) still have no employee assigned.")
        with st.expander("Why are these unstaffed?"):
            st.dataframe(diagnose_unstaffed(units, op_lookup, run_evidence), width='stretch', hide_index=True)
    else:
        st.success("Every operation is staffed with present employees.")
    st.caption(f"{len(merged)} operator(s) assigned to more than one operation. {len(cross)} working across lines.")

    st.dataframe(style_table(df, color_map), width='stretch', hide_index=True)

    csv = df.drop(columns=["_color_key", "_row_index", "_unit_id"]).to_csv(index=False).encode("utf-8")
    st.download_button("Download result (CSV)", csv, file_name="absentee_balancing_result.csv", mime="text/csv")

    all_employees_df = db.list_employees()
    present_employees_df = all_employees_df[all_employees_df["employee_id"].astype(str).isin(present)]
    render_manual_assignment_ui(df, present_employees_df, "ab_overrides")
