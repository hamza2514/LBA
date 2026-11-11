"""Decides which company's data a signed-in user is working in, and keeps the
session from carrying one company's state into another."""
from __future__ import annotations

import streamlit as st

import core.db as db

_ADMIN_PICK_KEY = "admin_company_id"
_ACTIVE_KEY = "_workspace_company"
_KEEP_KEYS = {"auth_user", _ADMIN_PICK_KEY, _ACTIVE_KEY}


def _reset_session_for(company_id: int | None) -> None:
    """Drops every per-company UI state (open styles, last results, uploads) on a company switch."""
    if st.session_state.get(_ACTIVE_KEY, company_id) != company_id:
        for key in [k for k in st.session_state if k not in _KEEP_KEYS]:
            del st.session_state[key]
    st.session_state[_ACTIVE_KEY] = company_id


def _admin_picker(companies) -> int | None:
    """Sidebar company switcher for the platform administrator (company names are unique)."""
    if companies.empty:
        return None
    ids = dict(zip(companies["name"], companies["id"]))
    return ids[st.sidebar.selectbox("Working in company", options=list(ids), key=_ADMIN_PICK_KEY)]


def activate(user: dict) -> int | None:
    """Binds the company for this script run and returns its id (None = no company yet)."""
    companies = db.list_companies()
    company_id = _admin_picker(companies) if user["role"] == "admin" else user.get("company_id")
    _reset_session_for(company_id)
    db.use_company(company_id)
    return company_id
