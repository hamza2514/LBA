import streamlit as st

import core.db as db
from core.context import build_context
from core.line_setup import combined_rows, select_line_styles
from core.ob_list import pick_ob
from core.orchestrate import run_multi_line, run_single_line
from core.results import RunResult
from core.results_view import render_results, store_result
from core.state import get_ob, init_state, list_lines, list_obs
from core.ui import page_header, stat_cards, warn_missing_sections

init_state()
OPEN_KEY = "lb_open"

if st.session_state.get(OPEN_KEY) not in list_obs():
    st.session_state[OPEN_KEY] = None

# ------------------------------------------------------------------ list view
if st.session_state[OPEN_KEY] is None:
    page_header("Layout Balancing", "Pick the style you want to balance.")
    chosen = pick_ob("lb_list")
    if chosen:
        st.session_state[OPEN_KEY] = chosen
        store_result("lb", None)
        st.rerun()
    st.stop()

# ------------------------------------------------------------------ workspace
ob_name = st.session_state[OPEN_KEY]
obs = list_obs()
ob = get_ob(ob_name)
ob_lines = list_lines()

missing = []
if db.list_employees() is None:
    missing.append("Employees (Data Import)")
if db.list_skill_pairs() is None:
    missing.append("Skill Matrix (Data Import)")
if not ob_lines:
    missing.append("at least one Line (Lines page)")

if st.button("All styles", icon=":material/arrow_back:"):
    st.session_state[OPEN_KEY] = None
    st.rerun()

page_header(ob_name, "Layout balancing workspace")
stat_cards([
    ("Operations", len(ob["rows"])),
    ("Total SMV", f"{sum(r['sam'] for r in ob['rows']):.3f}"),
    ("Default target", f"{ob['target']:,.0f}"),
    ("Plan efficiency", f"{ob['plan_efficiency'] * 100:.0f}%"),
])
if missing:
    st.warning("Still needed:\n\n" + "\n".join(f"- {m}" for m in missing))
    st.stop()
warn_missing_sections(ob["rows"], ob_name)

mode = st.segmented_control("Mode", ["Single line", "Multiple lines"], default="Single line", key="lb_mode")

if mode != "Multiple lines":
    c1, c2, c3, c4, c5 = st.columns([1.2, 1, 1, 1, 1.2], vertical_alignment="bottom")
    line = c1.selectbox("Line", options=ob_lines)
    shift_time = c2.number_input("Shift (min)", min_value=1.0, value=float(ob["shift_time"]), key=f"lb_shift_{ob_name}")
    target = c3.number_input("Target / shift", min_value=1.0, value=float(ob["target"]), key=f"lb_target_{ob_name}")
    plan_efficiency = c4.number_input("Plan eff", min_value=0.01, max_value=1.0, value=float(ob["plan_efficiency"]),
                                      key=f"lb_eff_{ob_name}")
    if c5.button("Run balancing", type="primary", use_container_width=True, icon=":material/play_arrow:"):
        with st.spinner("Balancing..."):
            ctx = build_context(ob["rows"])
            _, units = run_single_line(
                line, ob["rows"], shift_time, target, plan_efficiency, ctx.evidence, ctx.employee_line
            )
        store_result("lb", RunResult(
            units=units, line_order=[line], context=ctx,
            ob_by_line={line: ob_name}, ob_row_ids={line: [r["id"] for r in ob["rows"]]},
        ))
else:
    lines = st.pills("Lines", options=ob_lines, selection_mode="multi", default=ob_lines, key="lb_lines") or []
    if lines:
        st.caption("Style on each line — defaults to this one; target and efficiency start from the style's values.")
        setups, shift_time = select_line_styles("lb", lines, obs, default_ob=ob_name)
    if st.button("Run balancing", type="primary", disabled=len(lines) < 2, icon=":material/play_arrow:"):
        with st.spinner("Balancing across lines..."):
            ctx = build_context(combined_rows(setups))
            _, units = run_multi_line(
                lines, {s.line: s.rows for s in setups}, shift_time,
                {s.line: s.target for s in setups}, {s.line: s.plan_efficiency for s in setups},
                ctx.evidence, ctx.employee_line,
            )
        store_result("lb", RunResult(
            units=units, line_order=lines, context=ctx,
            ob_by_line={s.line: s.ob_name for s in setups}, ob_row_ids={s.line: s.row_ids for s in setups},
        ))
    if len(lines) < 2:
        st.caption("Pick at least two lines for multi-line balancing.")

render_results(prefix="lb", employees_df=db.list_employees(), file_stem="layout_balancing_result")
