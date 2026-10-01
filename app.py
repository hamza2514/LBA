import streamlit as st

from core.state import init_state

st.set_page_config(page_title="Line Balancing", page_icon="🧵", layout="wide")
init_state()

st.title("🧵 Line Balancing")
st.caption("Upload once, balance any line, any number of lines — across factories, not just one.")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.subheader("Lines")
    st.metric("Registered", len(st.session_state["lines"]))

with col2:
    st.subheader("Operation Breakdowns")
    st.metric("Saved", len(st.session_state["obs"]))

with col3:
    st.subheader("Employees")
    edf = st.session_state["employees_df"]
    st.metric("Loaded", len(edf) if edf is not None else 0)

with col4:
    st.subheader("Skill Matrix")
    sdf = st.session_state["skill_matrix_long"]
    st.metric("Employee-skill pairs", len(sdf) if sdf is not None else 0)

st.divider()
st.markdown(
    """
**Get started, in order:**
1. **Lines** — add the line names you work with.
2. **Data Import** — upload an Operation Breakdown (with Line per operation), your Employee list
   (with Line per employee), and the Skill Matrix.
3. **Operation Breakdown** — review the calculated manpower table for any saved OB.
4. **Layout Balancing** — run single-line or multi-line balancing.
5. **Absentee Balancing** — same as multi-line, restricted to who's actually present today.

*New operations that don't match the reference skill taxonomy are matched automatically, or a new
Skill Group is created on the spot — nothing blocks on an unrecognized operation.*
"""
)

if st.session_state["extra_taxonomy"]:
    with st.expander(f"🆕 {len(st.session_state['extra_taxonomy'])} new skill group(s) auto-created this session"):
        st.caption("These didn't match the reviewed reference taxonomy closely enough, so new IDs were minted. Worth a periodic review.")
        st.table(st.session_state["extra_taxonomy"])
