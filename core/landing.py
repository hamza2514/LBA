"""Landing page: marketing sections plus the real sign-in form (or, on the very
first run, the create-administrator form)."""
from __future__ import annotations

import streamlit as st

from core import auth
from core import landing_sections as sections
from core.landing_styles import CSS


def _contact_email() -> str | None:
    """Optional CONTACT_EMAIL secret; enables the 'Request access' button."""
    try:
        return st.secrets.get("CONTACT_EMAIL") or None
    except Exception:  # no secrets.toml (local dev)
        return None


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def _card_heading(title: str, subtitle: str) -> None:
    _html(f'<div id="{sections.SIGNIN_ANCHOR}"></div><p class="lp-card-title">{title}</p><p class="lp-card-sub">{subtitle}</p>')


def _sign_in_form() -> None:
    _card_heading("Welcome back", "Sign in with the account your administrator created.")
    with st.form("sign_in", border=False):
        username = st.text_input("Username", placeholder="your.username")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    _html('<p class="lp-card-foot">Forgot your password? Ask your administrator to reset it.</p>')
    if submitted:
        user = auth.authenticate(username, password)
        if user:
            auth.sign_in(user)
            st.rerun()
        st.error("Wrong username or password.")


def _setup_form() -> None:
    _card_heading("Create the administrator account", "First run — this account manages other users.")
    with st.form("first_admin", border=False):
        full_name = st.text_input("Full name")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account & sign in", type="primary", use_container_width=True)
    if not submitted:
        return
    error = auth.validate_new_password(password, confirm) or (None if username.strip() else "Username is required.")
    if error:
        st.error(error)
        return
    auth.create_user(username, password, full_name, role="admin")
    auth.sign_in(auth.authenticate(username, password))
    st.rerun()


def render() -> None:
    _html(f"<style>{CSS}</style>")

    with st.container(key="lp_hero"):
        _html(sections.nav())
        copy, form = st.columns([1.18, 1], gap="large", vertical_alignment="center")
        with copy:
            _html(sections.hero_copy())
        with form, st.container(key="lp_card"):
            _setup_form() if auth.needs_setup() else _sign_in_form()
        _html(sections.scene())

    with st.container(key="lp_why"):
        _html(sections.why())
    with st.container(key="lp_how"):
        _html(sections.how())
    with st.container(key="lp_feat"):
        _html(sections.features())
    with st.container(key="lp_band"):
        _html(sections.band(_contact_email()))
    with st.container(key="lp_footer"):
        _html(sections.footer())
