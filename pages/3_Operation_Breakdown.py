import streamlit as st

from core.formulas import compute_ob_table
from core.ob_component import ob_table
from core.state import get_ob, init_state, list_obs, save_ob_order

st.set_page_config(page_title="Operation Breakdown", page_icon="🧩", layout="wide")
init_state()
st.title("🧩 Operation Breakdown")

obs = list_obs()
if not obs:
    st.warning("No Operation Breakdown saved yet. Go to Data Import first.")
    st.stop()

ob_name = st.selectbox("Operation Breakdown", options=obs)
ob = get_ob(ob_name)

st.caption(
    "Raw formula table — no merging or employee assignment happens here. "
    "Drag ⠿ to change the operation sequence; it is saved automatically and used everywhere."
)

c1, c2, c3 = st.columns(3)
with c1:
    shift_time = st.number_input("Shift Time (minutes)", min_value=1.0, value=float(ob["shift_time"]))
with c2:
    target = st.number_input("Target (units/shift)", min_value=1.0, value=float(ob["target"]))
with c3:
    plan_efficiency = st.number_input("Plan Efficiency", min_value=0.01, max_value=1.0, value=float(ob["plan_efficiency"]))

calcs = compute_ob_table(ob["rows"], shift_time, target, plan_efficiency)
row_ids = [r["id"] for r in ob["rows"]]

COLUMNS = [
    {"key": "operation", "label": "Operation"},
    {"key": "machine", "label": "Machine Type"},
    {"key": "skill_group", "label": "Skill Group"},
    {"key": "sam", "label": "SAM", "num": True},
    {"key": "st100", "label": "Shift Target @100%", "num": True},
    {"key": "stEff", "label": "Shift Target @Plan Eff", "num": True},
    {"key": "mp100", "label": "Manpower @100%", "num": True},
    {"key": "mpEff", "label": "Manpower @Plan Eff", "num": True},
    {"key": "head", "label": "Head Allocated", "num": True},
]
rows = [
    {
        "id": rid, "operation": c.operation, "machine": c.machine_type or "", "skill_group": c.skill_group,
        "sam": round(c.sam, 4), "st100": round(c.shift_target_100, 1), "stEff": round(c.shift_target_eff, 1),
        "mp100": round(c.manpower_100, 3), "mpEff": round(c.manpower_eff, 3), "head": c.head_allocated,
    }
    for rid, c in zip(row_ids, calcs)
]

value = ob_table(
    key=f"ob_table_{ob_name}_{hash(tuple(row_ids))}", columns=COLUMNS, rows=rows, order=row_ids
)
if value and value.get("order") and value["order"] != row_ids:
    save_ob_order(value["order"])
    st.rerun()

st.caption(f"Total Head Allocated: **{sum(c.head_allocated for c in calcs)}**")
