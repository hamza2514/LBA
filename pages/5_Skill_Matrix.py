import streamlit as st

import core.db as db
from core import auth
from core.state import init_state
from core.ui import page_header

init_state()
page_header('Skill Matrix', 'Coverage per employee and per skill.')

df = db.list_skill_pairs()
if df is None:
    st.warning("No skill matrix saved yet. Go to Data Import first.")
    st.stop()

# Skill-group ids are an internal detail: company users see skills by name.
group_col = "skill_group" if auth.is_admin() else "skill_text"
label = "skill group" if auth.is_admin() else "skill"

col1, col2 = st.columns(2)
with col1:
    st.subheader("Skills per employee")
    per_emp = df.groupby("employee")[group_col].nunique().sort_values(ascending=False)
    st.dataframe(per_emp.rename("Skill Count"), width='stretch')

with col2:
    st.subheader(f"Coverage per {label}")
    st.caption("Fewest qualified employees = your staffing risk.")
    per_skill = df.groupby(group_col)["employee"].nunique().sort_values()
    st.dataframe(per_skill.rename("Qualified Employees"), width='stretch')

st.divider()
st.subheader("Full matrix (long format)")
st.dataframe(df if auth.is_admin() else df.drop(columns="skill_group"), width='stretch', hide_index=True)
