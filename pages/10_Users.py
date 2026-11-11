import streamlit as st

import core.db as db
from core import auth
from core.ui import page_header

page_header("Users & companies", "Add a company first, then the people who work in it. Each company's data is kept completely separate.")

current = auth.current_user() or {}
if current.get("role") != "admin":
    st.error("Administrators only.")
    st.stop()

companies = db.list_companies()

# ------------------------------------------------------------------ companies
with st.container(border=True):
    st.markdown("**1 · Companies**")
    with st.form("add_company", clear_on_submit=True, border=False):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        company_name = c1.text_input("New company", placeholder="e.g. Nizam Apparel")
        if c2.form_submit_button("Add company", type="primary", use_container_width=True):
            try:
                db.create_company(company_name)
            except ValueError as error:
                st.error(str(error))
            else:
                st.toast(f"Added '{company_name.strip()}'")
                st.rerun()

    if companies.empty:
        st.info("No companies yet. Add one to start creating users.")
    else:
        st.dataframe(companies[["name", "users", "created_at"]].rename(columns={"name": "Company", "users": "Users", "created_at": "Added"}),
                     hide_index=True, width="stretch")
        names = dict(zip(companies["id"], companies["name"]))
        with st.expander("Rename a company"):
            r1, r2, r3 = st.columns([2, 2, 1], vertical_alignment="bottom")
            target = r1.selectbox("Company", options=list(names), format_func=names.get, key="rename_target")
            new_name = r2.text_input("New name", key="rename_value")
            if r3.button("Rename", disabled=not new_name.strip()):
                try:
                    db.rename_company(target, new_name)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.rerun()

# ---------------------------------------------------------------------- users
with st.container(border=True):
    st.markdown("**2 · Users**")
    if companies.empty:
        st.caption("Add a company above first.")
    else:
        names = dict(zip(companies["id"], companies["name"]))
        with st.form("save_user", clear_on_submit=True, border=False):
            c1, c2, c3, c4, c5 = st.columns([1.5, 1.2, 1.2, 1.2, 0.9])
            company_id = c1.selectbox("Company", options=list(names), format_func=names.get)
            username = c2.text_input("Username")
            full_name = c3.text_input("Full name")
            password = c4.text_input("Password", type="password", help="Min 8 characters. Re-using a username resets that password.")
            role = c5.selectbox("Role", auth.ROLES, index=1, help="'admin' is a platform administrator and belongs to no company.")
            if st.form_submit_button("Save user", type="primary"):
                error = auth.validate_new_password(password, password) or (None if username.strip() else "Username is required.")
                if error:
                    st.error(error)
                else:
                    auth.create_user(username, password, full_name, role, company_id)
                    st.toast(f"Saved '{username.strip().lower()}'")
                    st.rerun()

    users = db.list_users()
    st.dataframe(users.assign(company=users["company"].fillna("— all (platform admin)")), hide_index=True, width="stretch")

    removable = [u for u in users["username"] if u != current["username"]]
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    target = c1.selectbox("Remove a user", options=removable, index=None, placeholder="Choose a user…")
    if c2.button("Remove", disabled=not target, icon=":material/delete:"):
        db.delete_user(target)
        st.rerun()
