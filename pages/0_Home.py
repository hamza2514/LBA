import streamlit as st

import core.db as db
from core import auth
from core.state import extra_taxonomy_list, list_lines
from core.ui import page_header, stat_cards

user = auth.current_user() or {}
page_header(f"Welcome back, {(user.get('full_name') or user.get('username') or '').split(' ')[0]}",
            "Your production planning workspace.")

summaries = db.list_ob_summaries()
employees = db.list_employees()
pairs = db.list_skill_pairs()
learned = db.list_learned()
lines = list_lines()

stat_cards([
    ("Lines", len(lines)),
    ("Styles (OBs)", len(summaries)),
    ("Employees", 0 if employees is None else len(employees)),
    ("Employee–skill pairs", 0 if pairs is None else len(pairs)),
    ("Learned from you", 0 if learned is None else len(learned)),
])

left, right = st.columns([1.6, 1], gap="large")

with left:
    with st.container(border=True):
        st.subheader("Quick start")
        steps = [
            ("Add your lines", bool(lines), "pages/1_Lines.py", "Lines"),
            ("Upload an Operation Breakdown, employees and skill matrix",
             not summaries.empty and employees is not None and pairs is not None, "pages/2_Data_Import.py", "Data Import"),
            ("Review the OB and arrange the operation sequence", not summaries.empty,
             "pages/3_Operation_Breakdown.py", "Operation Breakdown"),
            ("Balance one or many lines", False, "pages/6_Layout_Balancing.py", "Layout Balancing"),
            ("Re-balance for today's attendance", False, "pages/7_Absentee_Balancing.py", "Absentee Balancing"),
        ]
        for i, (label, done, page, title) in enumerate(steps, start=1):
            c1, c2 = st.columns([4, 1.2], vertical_alignment="center")
            c1.markdown(f"{'✅' if done else f'**{i}.**'}  {label}")
            c2.page_link(page, label="Open", icon=":material/arrow_forward:")

with right:
    with st.container(border=True):
        st.subheader("Recent styles")
        if summaries.empty:
            st.caption("Nothing uploaded yet.")
        for r in summaries.head(6).itertuples():
            st.markdown(f"**{r.name}**  \n<span style='color:#64748B;font-size:.82rem'>"
                        f"{r.operations} operations · SMV {r.total_smv:.2f}</span>", unsafe_allow_html=True)

extra = extra_taxonomy_list()
if extra:
    with st.expander(f"🆕 {len(extra)} new skill group(s) auto-created so far"):
        st.caption("These didn't match the reviewed reference taxonomy closely enough, so new IDs were minted. Worth a periodic review.")
        st.dataframe(extra, hide_index=True, width="stretch")
