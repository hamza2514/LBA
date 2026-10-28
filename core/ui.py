"""Shared look & feel: one stylesheet injected on every run, plus small
layout helpers (page header, stat cards) so every page looks the same."""
from __future__ import annotations

from html import escape

import streamlit as st

BRAND = "LineSense"
TAGLINE = "Balance every line. Every shift."

_CSS = """
<style>
:root {
  --primary:#4F46E5; --primary-dark:#4338CA; --teal:#14B8A6; --ink:#0F172A; --muted:#64748B;
  --line:#E2E8F0; --bg:#F5F7FB; --card:#FFFFFF;
}
html, body, [data-testid="stAppViewContainer"] { background: var(--bg); }
.block-container { padding-top: 1.6rem; max-width: 1500px; }
[data-testid="stHeader"] { background: transparent; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { background: linear-gradient(180deg,#0B1020 0%,#1E1B4B 100%); border-right: 0; }
[data-testid="stSidebar"] * { color: #CBD5E1; }
[data-testid="stSidebarNav"] a, [data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] {
  border-radius: 10px; margin: 1px 6px; padding: 6px 10px;
}
[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]:hover { background: rgba(255,255,255,.07); }
[data-testid="stSidebar"] a[aria-current="page"] {
  background: linear-gradient(90deg, rgba(99,102,241,.55), rgba(20,184,166,.35)); color:#fff; font-weight:600;
}
[data-testid="stSidebar"] a[aria-current="page"] * { color:#fff; }
[data-testid="stSidebarNavSeparator"] { opacity:.5; }
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] .stCaption { color:#94A3B8; }
.user-chip { display:flex; gap:10px; align-items:center; padding:10px 12px; margin:8px 6px; border-radius:12px;
  background: rgba(255,255,255,.07); }
.user-chip .av { width:34px; height:34px; border-radius:50%; background:linear-gradient(135deg,#818CF8,#2DD4BF);
  display:flex; align-items:center; justify-content:center; font-weight:700; color:#0B1020 !important; }
.user-chip .nm { font-weight:600; color:#fff !important; line-height:1.1; }
.user-chip .rl { font-size:.72rem; color:#94A3B8 !important; text-transform:uppercase; letter-spacing:.06em; }

/* ---------- typography ---------- */
h1, h2, h3 { color: var(--ink); letter-spacing: -0.02em; }
.page-head { display:flex; align-items:flex-end; justify-content:space-between; margin: 0 0 1rem 0; }
.page-head h1 { margin:0; font-size:1.7rem; font-weight:750; padding:0; }
.page-head p { margin:.15rem 0 0 0; color: var(--muted); font-size:.92rem; }

/* ---------- cards ---------- */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; border-color: var(--line); background: var(--card);
  box-shadow: 0 1px 2px rgba(15,23,42,.04); }
.stat-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 0 0 1rem 0; }
.stat { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:12px 16px;
  box-shadow:0 1px 2px rgba(15,23,42,.04); position:relative; overflow:hidden; }
.stat::before { content:""; position:absolute; left:0; top:0; bottom:0; width:4px;
  background: linear-gradient(180deg,var(--primary),var(--teal)); }
.stat .lb { color:var(--muted); font-size:.74rem; text-transform:uppercase; letter-spacing:.06em; font-weight:600; }
.stat .vl { color:var(--ink); font-size:1.45rem; font-weight:750; line-height:1.25; }
.stat .ht { color:var(--muted); font-size:.76rem; }
[data-testid="stMetric"] { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 12px 16px;
  box-shadow: 0 1px 2px rgba(15,23,42,.04); }
[data-testid="stMetricLabel"] p { color: var(--muted); font-size: .78rem; }

/* ---------- controls ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 10px; font-weight: 600; border: 1px solid var(--line); }
.stButton > [data-testid="stBaseButton-primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"],
[data-testid="stFormSubmitButton"] > [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, var(--primary), #6366F1); border: 0; color:#fff;
  box-shadow: 0 4px 12px rgba(79,70,229,.28); }
.stButton > [data-testid="stBaseButton-primary"]:hover { background: linear-gradient(135deg, var(--primary-dark), var(--primary)); }
.stButton > [data-testid="stBaseButton-tertiary"] { justify-content: flex-start; text-align: left; font-weight: 650;
  color: var(--ink); border: 0; padding-left: 6px; }
.stButton > [data-testid="stBaseButton-tertiary"] > div { justify-content: flex-start; width: 100%; }
.stButton > [data-testid="stBaseButton-tertiary"] p { text-align: left; }
.stButton > [data-testid="stBaseButton-tertiary"]:hover { color: var(--primary); background: #EEF2FF; }
[data-testid="stSidebar"] .stButton > button { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.14); }
[data-testid="stSidebar"] .stButton > button * { color: #E2E8F0; }
[data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,.16); }
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] { box-shadow: none; }
[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input { border-radius: 10px; min-height: 38px; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: 8px 14px; }
div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }

/* ---------- landing ---------- */
.hero-brand { display:flex; align-items:center; gap:10px; font-weight:750; font-size:1.25rem; color:var(--ink); }
.hero h1 { font-size: 3rem; line-height:1.05; font-weight: 800; margin: 1.2rem 0 .8rem 0; letter-spacing:-0.035em; padding:0; }
.hero h1 span { background: linear-gradient(90deg,var(--primary),var(--teal)); -webkit-background-clip:text;
  -webkit-text-fill-color:transparent; }
.hero p.lead { color: var(--muted); font-size:1.08rem; max-width: 560px; }
.chips { display:flex; flex-wrap:wrap; gap:8px; margin: 1rem 0 1.4rem 0; }
.chip { background:#EEF2FF; color:var(--primary-dark); border-radius:999px; padding:6px 14px; font-weight:600; font-size:.85rem; }
.chip.t { background:#CCFBF1; color:#0F766E; }
.signin-title { font-size:1.35rem; font-weight:750; margin:0; }
.signin-sub { color:var(--muted); margin:.1rem 0 .6rem 0; font-size:.9rem; }
</style>
"""

_HIDE_SIDEBAR = "<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] { display:none; }</style>"


def apply_theme(hide_sidebar: bool = False) -> None:
    st.markdown(_CSS + (_HIDE_SIDEBAR if hide_sidebar else ""), unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(f"<div class='page-head'><div><h1>{escape(title)}</h1>{sub}</div></div>", unsafe_allow_html=True)


def stat_cards(items: list[tuple]) -> None:
    """items: (label, value[, hint]) tuples rendered as a responsive card row."""
    cards = "".join(
        f"<div class='stat'><div class='lb'>{escape(str(i[0]))}</div><div class='vl'>{escape(str(i[1]))}</div>"
        + (f"<div class='ht'>{escape(str(i[2]))}</div>" if len(i) > 2 else "")
        + "</div>"
        for i in items
    )
    st.markdown(f"<div class='stat-grid'>{cards}</div>", unsafe_allow_html=True)


def warn_missing_sections(ob_rows: list[dict], name: str = "") -> None:
    """Operations without a section are never merged — tell the user why."""
    prefix = f"'{name}': " if name else ""
    missing = sum(1 for r in ob_rows if not r.get("section"))
    if not missing:
        return
    if missing == len(ob_rows):
        st.warning(prefix + "This Operation Breakdown has no line sections, so no operations will be merged. "
                   "Re-import it from the original file (Data Import) so sections are detected.")
    else:
        st.warning(f"{prefix}{missing} operation(s) have no section and will not be merged with others.")
