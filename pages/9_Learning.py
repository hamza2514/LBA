import streamlit as st

import core.db as db
from core.ui import page_header
from core.state import employee_names_dict, init_state

init_state()
page_header('Learning', 'Everything learned from the layouts you saved. Used like uploaded skills.')

df = db.list_learned()
if df is None:
    st.info("Nothing learned yet. Adjust a layout, then click 'Save layout & learn' on the result.")
    st.stop()

names = employee_names_dict()
view = df.copy()
view.insert(1, "employee_name", view["employee"].map(names).fillna(""))
st.metric("Learned pairs", len(view))
st.dataframe(view, width="stretch", hide_index=True)

st.divider()
labels = {f"{r.employee} · {r.skill_text} · {r.machine_type or '-'}": r for r in df.itertuples()}
chosen = st.multiselect("Forget specific entries", options=list(labels))
c1, c2 = st.columns(2)
if c1.button("Forget selected", disabled=not chosen):
    for label in chosen:
        r = labels[label]
        db.delete_learned(r.employee, r.skill_text, r.machine_type)
    st.rerun()
if c2.button("Forget everything"):
    db.clear_learned()
    st.rerun()
