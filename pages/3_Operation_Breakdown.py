import streamlit as st

import core.db as db
from core.formulas import compute_ob_table
from core.ob_component import ob_table
from core.ob_list import pick_ob
from core.state import get_ob, init_state, list_obs, save_ob_order
from core.ui import page_header, stat_cards

init_state()
OPEN_KEY = "ob_open"

if st.session_state.get(OPEN_KEY) not in list_obs():
    st.session_state[OPEN_KEY] = None

# ------------------------------------------------------------------ list view
if st.session_state[OPEN_KEY] is None:
    page_header("Operation Breakdown", "Every uploaded style. Click one to open it.")
    chosen = pick_ob("ob_list")
    if chosen:
        st.session_state[OPEN_KEY] = chosen
        st.rerun()
    st.stop()

# ---------------------------------------------------------------- detail view
ob_name = st.session_state[OPEN_KEY]
ob = get_ob(ob_name)

back, _, delete = st.columns([1.3, 6, 1.2], vertical_alignment="center")
if back.button("All styles", icon=":material/arrow_back:"):
    st.session_state[OPEN_KEY] = None
    st.rerun()
if delete.button("Delete", icon=":material/delete:", help="Delete this Operation Breakdown"):
    db.delete_ob(ob_name)
    st.session_state[OPEN_KEY] = None
    st.rerun()

page_header(ob_name, "Raw formula table — no merging or employee assignment happens here.")

c1, c2, c3, _ = st.columns([1, 1, 1, 3])
shift_time = c1.number_input("Shift (min)", min_value=1.0, value=float(ob["shift_time"]), key=f"ob_shift_{ob_name}")
target = c2.number_input("Target / shift", min_value=1.0, value=float(ob["target"]), key=f"ob_target_{ob_name}")
plan_efficiency = c3.number_input("Plan efficiency", min_value=0.01, max_value=1.0,
                                  value=float(ob["plan_efficiency"]), key=f"ob_eff_{ob_name}")

calcs = compute_ob_table(ob["rows"], shift_time, target, plan_efficiency)
row_ids = [r["id"] for r in ob["rows"]]
sections = sorted({r["section"] for r in ob["rows"] if r["section"]})

stat_cards([
    ("Operations", len(calcs)),
    ("Total SMV", f"{sum(c.sam for c in calcs):.3f}"),
    ("Head allocated", sum(c.head_allocated for c in calcs)),
    ("Sections", len(sections), ", ".join(sections) if sections else "none detected"),
])

st.caption("Drag ⠿ to change the operation sequence — saved automatically and used everywhere.")
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
value = ob_table(key=f"ob_table_{ob_name}_{hash(tuple(row_ids))}", columns=COLUMNS, rows=rows, order=row_ids)
if value and value.get("order") and value["order"] != row_ids:
    save_ob_order(value["order"])
    st.rerun()
