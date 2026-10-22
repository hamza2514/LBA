import streamlit as st

import core.db as db
from core.context import build_context
from core.importers import read_any
from core.orchestrate import run_multi_line
from core.results import RunResult
from core.results_view import render_results, store_result
from core.state import employee_line_dict, get_ob, init_state, list_lines, list_obs

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

all_employees = sorted(employee_line_dict())

st.subheader("Who's present today?")
mode = st.radio(
    "How do you want to mark attendance?",
    options=["Upload attendance file", "Pick present employees manually"],
    horizontal=True,
)

present: set | None = None
if mode == "Upload attendance file":
    file = st.file_uploader("Upload attendance (.xlsx or .csv) — any column containing the employee ID marks them present", type=["xlsx", "csv"])
    if file:
        raw = read_any(file)
        st.dataframe(raw.head(10), width="stretch")
        id_col = st.selectbox("Which column has the Employee ID?", options=list(raw.columns))
        present = set(raw[id_col].astype(str))
else:
    present = set(st.multiselect("Present employees", options=all_employees, default=all_employees))

if present is not None:
    st.caption(f"{len(present)} employee(s) marked present out of {len(all_employees)} total.")

    if st.button("Run Absentee Balancing", type="primary", disabled=len(lines) < 2):
        with st.spinner("Balancing across lines with present employees only..."):
            ctx = build_context(ob["rows"], present=present)
            _, units = run_multi_line(
                lines, {ln: ob["rows"] for ln in lines},
                float(ob["shift_time"]), float(ob["target"]), float(ob["plan_efficiency"]),
                ctx.evidence, ctx.employee_line,
            )
        store_result("ab", RunResult(units=units, line_order=lines, context=ctx))
    if len(lines) < 2:
        st.caption("Pick at least two lines.")

    render_results(prefix="ab", employees_df=db.list_employees(), file_stem="absentee_balancing_result")
