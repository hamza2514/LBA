import pandas as pd
import streamlit as st

from core.state import init_state
from core.formulas import compute_ob_table

st.set_page_config(page_title="Operation Breakdown", page_icon="🧩", layout="wide")
init_state()
st.title("🧩 Operation Breakdown")

obs = st.session_state["obs"]
if not obs:
    st.warning("No Operation Breakdown loaded yet. Go to Data Import first.")
    st.stop()

ob_name = st.selectbox("Operation Breakdown", options=list(obs.keys()))
ob = obs[ob_name]

st.caption("This view is the raw formula table — no merging or employee assignment happens here (that's Layout/Absentee Balancing).")

c1, c2, c3 = st.columns(3)
with c1:
    shift_time = st.number_input("Shift Time (minutes)", min_value=1.0, value=float(ob["shift_time"]))
with c2:
    target = st.number_input("Target (units/shift)", min_value=1.0, value=float(ob["target"]))
with c3:
    plan_efficiency = st.number_input("Plan Efficiency", min_value=0.01, max_value=1.0, value=float(ob["plan_efficiency"]))

line_filter = st.selectbox("Line", options=["(all)"] + sorted({r["line"] for r in ob["rows"]}))
rows = ob["rows"] if line_filter == "(all)" else [r for r in ob["rows"] if r["line"] == line_filter]

calcs = compute_ob_table(rows, shift_time, target, plan_efficiency)

table = pd.DataFrame(
    [
        {
            "Sr#": i + 1,
            "Operation": c.operation,
            "Machine Type": c.machine_type,
            "Skill Group": c.skill_group,
            "SAM": round(c.sam, 4),
            "Shift Target @100%": round(c.shift_target_100, 1),
            "Shift Target @Plan Eff": round(c.shift_target_eff, 1),
            "Manpower @100%": round(c.manpower_100, 3),
            "Manpower @Plan Eff": round(c.manpower_eff, 3),
            "Head Allocated": c.head_allocated,
        }
        for i, c in enumerate(calcs)
    ]
)

st.dataframe(table, width='stretch', hide_index=True)
st.caption(f"Total Head Allocated: **{table['Head Allocated'].sum()}**")
