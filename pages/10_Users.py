import streamlit as st

import core.db as db
from core import auth
from core.ui import page_header

page_header("Users", "Who can sign in. Only administrators see this page.")

current = auth.current_user() or {}
if current.get("role") != "admin":
    st.error("Administrators only.")
    st.stop()

with st.container(border=True):
    st.markdown("**Add or update a user**")
    with st.form("save_user", clear_on_submit=True, border=False):
        c1, c2, c3, c4 = st.columns([1.3, 1.3, 1.3, 0.9])
        username = c1.text_input("Username")
        full_name = c2.text_input("Full name")
        password = c3.text_input("Password", type="password", help="Min 8 characters. Re-using a username resets that password.")
        role = c4.selectbox("Role", auth.ROLES, index=1)
        if st.form_submit_button("Save user", type="primary"):
            error = auth.validate_new_password(password, password) or (None if username.strip() else "Username is required.")
            if error:
                st.error(error)
            else:
                auth.create_user(username, password, full_name, role)
                st.toast(f"Saved '{username.strip().lower()}'")
                st.rerun()

users = db.list_users()
st.dataframe(users, hide_index=True, width="stretch")

removable = [u for u in users["username"] if u != current["username"]]
c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
target = c1.selectbox("Remove a user", options=removable, index=None, placeholder="Choose a user…")
if c2.button("Remove", disabled=not target, icon=":material/delete:"):
    db.delete_user(target)
    st.rerun()
