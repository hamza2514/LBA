"""Entrypoint: landing/sign-in for visitors, grouped navigation for signed-in users."""
from __future__ import annotations

from html import escape

import streamlit as st

from core import auth, landing
from core.state import init_state
from core.ui import BRAND, apply_theme

st.set_page_config(page_title=f"{BRAND} · Line Balancing", page_icon="🧵", layout="wide")

try:
    init_state()
except Exception as e:
    apply_theme(hide_sidebar=True)
    st.error(
        "Couldn't connect to the database. Set DATABASE_URL in your app's Secrets "
        "(Settings → Secrets on Streamlit Cloud) to a Postgres connection string, e.g. "
        "from a free Neon project."
    )
    st.caption(f"Technical detail: {e}")
    st.stop()

user = auth.current_user()
if not user:
    apply_theme(hide_sidebar=True)
    st.navigation([st.Page(landing.render, title="Sign in", url_path="signin")], position="hidden").run()
    st.stop()

apply_theme()
st.logo("assets/logo.svg", icon_image="assets/icon.svg")


def _page(path: str, title: str, icon: str, **kwargs) -> st.Page:
    return st.Page(f"pages/{path}", title=title, icon=f":material/{icon}:", **kwargs)


setup_pages = [_page("1_Lines.py", "Lines", "factory")]
if user["role"] == "admin":
    setup_pages.append(_page("10_Users.py", "Users", "admin_panel_settings"))

navigation = st.navigation(
    {
        "Planning": [
            _page("0_Home.py", "Home", "home", default=True),
            _page("3_Operation_Breakdown.py", "Operation Breakdown", "account_tree"),
            _page("6_Layout_Balancing.py", "Layout Balancing", "tune"),
            _page("7_Absentee_Balancing.py", "Absentee Balancing", "person_off"),
        ],
        "Data": [
            _page("2_Data_Import.py", "Data Import", "upload_file"),
            _page("4_Employees.py", "Employees", "groups"),
            _page("5_Skill_Matrix.py", "Skill Matrix", "hub"),
            _page("8_Roles.py", "Roles", "badge"),
            _page("9_Learning.py", "Learning", "psychology"),
        ],
        "Setup": setup_pages,
    }
)

with st.sidebar:
    name = user["full_name"] or user["username"]
    st.markdown(
        f"<div class='user-chip'><div class='av'>{escape(name[:1].upper())}</div>"
        f"<div><div class='nm'>{escape(name)}</div><div class='rl'>{escape(user['role'])}</div></div></div>",
        unsafe_allow_html=True,
    )
    if st.button("Sign out", icon=":material/logout:", use_container_width=True):
        auth.sign_out()
        st.rerun()

navigation.run()
