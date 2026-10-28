import streamlit as st

import core.db as db
from core.state import add_line, init_state, list_lines
from core.ui import page_header

init_state()
page_header("Lines", "Register the lines you work with. Saved permanently and used everywhere in the app.")

with st.container(border=True):
    with st.form("add_line_form", clear_on_submit=True, border=False):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        new_line = c1.text_input("New line", placeholder="e.g. L01, AM-4A-Line3")
        if c2.form_submit_button("Add line", type="primary", use_container_width=True) and new_line.strip():
            add_line(new_line)
            st.toast(f"Added '{new_line.strip()}'")
            st.rerun()

lines = list_lines()
if not lines:
    st.info("No lines added yet.")
else:
    st.caption(f"{len(lines)} line(s)")
    columns = st.columns(4)
    for i, line in enumerate(lines):
        with columns[i % 4].container(border=True):
            c1, c2 = st.columns([3, 1], vertical_alignment="center")
            c1.markdown(f"**{line}**")
            if c2.button("", key=f"remove_line_{i}", icon=":material/delete:", help="Remove line"):
                db.delete_line(line)
                st.rerun()
