import streamlit as st

from core.state import init_state, skill_matrix_dict, employee_line_dict
from core.orchestrate import run_multi_line
from core.render import units_to_table, style_table
from core.importers import read_any

st.set_page_config(page_title="Absentee Balancing", page_icon="🧍", layout="wide")
init_state()
st.title("🧍 Absentee Balancing")
st.caption("Always multi-line, same engine as Layout Balancing's multi-line mode — restricted to whoever's actually present today.")

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

ob_name = st.selectbox("Operation Breakdown", options=list(obs.keys()))
ob = obs[ob_name]
ob_lines = sorted({r["line"] for r in ob["rows"]})
lines = st.multiselect("Lines", options=ob_lines, default=ob_lines)

all_skill_matrix = skill_matrix_dict()
all_employee_line = employee_line_dict()
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

    skill_matrix = {e: sgs for e, sgs in all_skill_matrix.items() if e in present}
    employee_line = {e: line for e, line in all_employee_line.items() if e in present}

    if st.button("Run Absentee Balancing", type="primary", disabled=len(lines) < 2):
        rows_by_line = {line: [r for r in ob["rows"] if r["line"] == line] for line in lines}
        with st.spinner("Balancing across lines with present employees only..."):
            calcs_by_line, units = run_multi_line(
                lines, rows_by_line, float(ob["shift_time"]), float(ob["target"]), float(ob["plan_efficiency"]),
                skill_matrix, employee_line,
            )
        st.session_state["ab_result"] = (calcs_by_line, units)
    if len(lines) < 2:
        st.caption("Pick at least two lines.")

result = st.session_state.get("ab_result")
if result:
    _, units = result
    st.divider()

    unstaffed = [u for u in units if u.understaffed]
    if unstaffed:
        st.error(f"{len(unstaffed)} assignment(s) have no qualified PRESENT employee available.")
    else:
        st.success("Every operation is staffed with present employees.")

    merged = [u for u in units if u.color_key != "unmerged"]
    cross = [u for u in units if u.cross_line]
    st.caption(f"{len(merged)} operator(s) assigned to more than one operation. {len(cross)} working across lines.")

    df, color_map = units_to_table(units)
    st.dataframe(style_table(df, color_map), width='stretch', hide_index=True)

    csv = df.drop(columns=["_color_key"]).to_csv(index=False).encode("utf-8")
    st.download_button("Download result (CSV)", csv, file_name="absentee_balancing_result.csv", mime="text/csv")
