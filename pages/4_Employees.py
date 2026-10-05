import streamlit as st

from core.state import init_state
import core.db as db

st.set_page_config(page_title="Employees", page_icon="👥", layout="wide")
init_state()
st.title("👥 Employees")

df = db.list_employees()
if df is None:
    st.warning("No employee list saved yet. Go to Data Import first.")
    st.stop()

c1, c2 = st.columns(2)
with c1:
    search = st.text_input("Search by name or ID")
with c2:
    line_filter = st.selectbox("Filter by line", options=["(all)"] + sorted(df["line"].dropna().unique().tolist()))

view = df.copy()
if search:
    mask = view.apply(
        lambda r: search.lower() in str(r["employee_id"]).lower() or search.lower() in str(r["employee_name"]).lower(),
        axis=1,
    )
    view = view[mask]
if line_filter != "(all)":
    view = view[view["line"] == line_filter]

st.metric("Employees shown", len(view))
st.dataframe(view, width='stretch', hide_index=True)
