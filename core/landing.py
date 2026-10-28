"""Landing page with sign-in (and first-run administrator setup)."""
from __future__ import annotations

import streamlit as st

from core import auth
from core.ui import BRAND, TAGLINE

_ILLUSTRATION = """
<svg viewBox="0 0 560 300" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:560px">
  <defs>
    <linearGradient id="a" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6366F1"/><stop offset="1" stop-color="#2DD4BF"/></linearGradient>
    <linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#EEF2FF"/><stop offset="1" stop-color="#CCFBF1"/></linearGradient>
  </defs>
  <rect x="0" y="0" width="560" height="300" rx="28" fill="url(#b)"/>
  <g opacity=".55"><circle cx="500" cy="48" r="70" fill="#C7D2FE"/><circle cx="60" cy="270" r="60" fill="#99F6E4"/></g>
  <g fill="#fff" stroke="#E2E8F0">
    <rect x="40" y="46" width="480" height="64" rx="14"/><rect x="40" y="128" width="480" height="64" rx="14"/>
    <rect x="40" y="210" width="480" height="64" rx="14"/>
  </g>
  <g fill="url(#a)">
    <rect x="56" y="62" width="150" height="32" rx="10"/><rect x="214" y="62" width="110" height="32" rx="10" opacity=".75"/>
    <rect x="332" y="62" width="170" height="32" rx="10" opacity=".5"/>
    <rect x="56" y="144" width="90" height="32" rx="10" opacity=".75"/><rect x="154" y="144" width="190" height="32" rx="10"/>
    <rect x="352" y="144" width="150" height="32" rx="10" opacity=".5"/>
    <rect x="56" y="226" width="200" height="32" rx="10" opacity=".5"/><rect x="264" y="226" width="120" height="32" rx="10"/>
    <rect x="392" y="226" width="110" height="32" rx="10" opacity=".75"/>
  </g>
  <g fill="#0B1020" font-family="Segoe UI,Arial,sans-serif" font-size="12" font-weight="600">
    <text x="70" y="83">Back</text><text x="228" y="83">Front</text><text x="346" y="83">Assembly</text>
    <text x="70" y="165">Small parts</text><text x="168" y="165">Pocket setter</text><text x="366" y="165">Dispatch</text>
  </g>
</svg>
"""


def _sign_in_form() -> None:
    st.markdown("<p class='signin-title'>Welcome back</p><p class='signin-sub'>Sign in to continue</p>",
                unsafe_allow_html=True)
    with st.form("sign_in", border=False):
        username = st.text_input("Username", placeholder="your.username")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    if submitted:
        user = auth.authenticate(username, password)
        if user:
            auth.sign_in(user)
            st.rerun()
        st.error("Wrong username or password.")


def _setup_form() -> None:
    st.markdown("<p class='signin-title'>Create the administrator account</p>"
                "<p class='signin-sub'>First run — this account manages other users.</p>", unsafe_allow_html=True)
    with st.form("first_admin", border=False):
        full_name = st.text_input("Full name")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account & sign in", type="primary", use_container_width=True)
    if submitted:
        error = auth.validate_new_password(password, confirm) or (None if username.strip() else "Username is required.")
        if error:
            st.error(error)
            return
        auth.create_user(username, password, full_name, role="admin")
        auth.sign_in(auth.authenticate(username, password))
        st.rerun()


def render() -> None:
    left, right = st.columns([1.35, 1], gap="large", vertical_alignment="center")
    with left:
        st.markdown(
            f"""
<div class="hero">
  <div class="hero-brand">🧵 {BRAND}</div>
  <h1>{TAGLINE.split('.')[0]}.<br><span>{TAGLINE.split('.')[1].strip()}.</span></h1>
  <p class="lead">Upload any Operation Breakdown and skill matrix. The app reads them, staffs every operation
  with the right operator, and keeps learning from the corrections you make.</p>
  <div class="chips"><span class="chip">Reads any OB &amp; skill file</span><span class="chip t">Learns from your edits</span>
  <span class="chip">Multi-line, multi-style</span><span class="chip t">Absentee-ready</span></div>
</div>
{_ILLUSTRATION}
""",
            unsafe_allow_html=True,
        )
    with right:
        with st.container(border=True):
            if auth.needs_setup():
                _setup_form()
            else:
                _sign_in_form()
