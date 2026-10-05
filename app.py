import streamlit as st

from core.state import init_state, list_lines, list_obs, extra_taxonomy_list
import core.db as db

st.set_page_config(page_title="Line Balancing", page_icon="🧵", layout="wide")

try:
    init_state()
except Exception as e:
    st.error(
        "Couldn't connect to the database. Set DATABASE_URL in your app's Secrets "
        "(Settings → Secrets on Streamlit Cloud) to a Postgres connection string, e.g. "
        "from a free Neon project — same pattern as the loss-time tracker."
    )
    st.caption(f"Technical detail: {e}")
    st.stop()

st.title("🧵 Line Balancing")
st.caption("Upload once, balance any line, any number of lines — across factories, not just one. Everything here is saved permanently.")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.subheader("Lines")
    st.metric("Registered", len(list_lines()))

with col2:
    st.subheader("Operation Breakdowns")
    st.metric("Saved", len(list_obs()))

with col3:
    st.subheader("Employees")
    edf = db.list_employees()
    st.metric("Loaded", len(edf) if edf is not None else 0)

with col4:
    st.subheader("Skill Matrix")
    sdf = db.list_skill_pairs()
    st.metric("Employee-skill pairs", len(sdf) if sdf is not None else 0)

st.divider()
st.markdown(
    """
**Get started, in order:**
1. **Lines** — add the line names you work with.
2. **Data Import** — upload an Operation Breakdown, your Employee list, and the Skill Matrix.
3. **Roles** — teach the tool general-purpose roles (e.g. "Presser" = qualified for every operation on
   any press-family machine) so employees don't need every individual operation spelled out.
4. **Operation Breakdown** — review the calculated manpower table for any saved OB.
5. **Layout Balancing** — run single-line or multi-line balancing.
6. **Absentee Balancing** — same as multi-line, restricted to who's actually present today.

*New operations that don't match the reference skill taxonomy are matched automatically, or a new
Skill Group is created on the spot — nothing blocks on an unrecognized operation. Everything you
teach it (Lines, Roles, Skill Matrix, auto-created Skill Groups) is now saved permanently in the
database — it will still be here next time you open the app.*
"""
)

extra = extra_taxonomy_list()
if extra:
    with st.expander(f"🆕 {len(extra)} new skill group(s) auto-created so far"):
        st.caption("These didn't match the reviewed reference taxonomy closely enough, so new IDs were minted. Worth a periodic review.")
        st.table(extra)
