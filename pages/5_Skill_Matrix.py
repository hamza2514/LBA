import streamlit as st

from core.state import init_state
import core.db as db

st.set_page_config(page_title="Skill Matrix", page_icon="🎯", layout="wide")
init_state()
st.title("🎯 Skill Matrix")

df = db.list_skill_pairs()
if df is None:
    st.warning("No skill matrix saved yet. Go to Data Import first.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Skills per employee")
    per_emp = df.groupby("employee")["skill_group"].nunique().sort_values(ascending=False)
    st.dataframe(per_emp.rename("Skill Count"), width='stretch')

with col2:
    st.subheader("Coverage per skill group")
    st.caption("Fewest qualified employees = your staffing risk.")
    per_skill = df.groupby("skill_group")["employee"].nunique().sort_values()
    st.dataframe(per_skill.rename("Qualified Employees"), width='stretch')

st.divider()
st.subheader("Full matrix (long format)")
st.dataframe(df, width='stretch', hide_index=True)
