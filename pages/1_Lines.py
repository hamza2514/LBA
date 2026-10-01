import streamlit as st

from core.state import init_state, add_line

st.set_page_config(page_title="Lines", page_icon="🏭", layout="wide")
init_state()
st.title("🏭 Lines")
st.caption("Register the lines you work with here. Used everywhere else in the app — Employees, Operation Breakdown, and both balancing modules all reference these names.")

with st.form("add_line_form", clear_on_submit=True):
    new_line = st.text_input("Line name", placeholder="e.g. L01, AM-4A-Line3")
    submitted = st.form_submit_button("Add Line", type="primary")
    if submitted and new_line.strip():
        add_line(new_line)
        st.success(f"Added '{new_line.strip()}'.")

st.divider()

lines = st.session_state["lines"]
if not lines:
    st.info("No lines added yet.")
else:
    st.subheader(f"{len(lines)} line(s)")
    for i, line in enumerate(lines):
        c1, c2 = st.columns([5, 1])
        c1.write(line)
        if c2.button("Remove", key=f"remove_line_{i}"):
            st.session_state["lines"].remove(line)
            st.rerun()
