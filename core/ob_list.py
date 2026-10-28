"""Compact, searchable list of saved Operation Breakdowns; clicking a row opens it."""
from __future__ import annotations

import streamlit as st

import core.db as db

_WIDTHS = [4.2, 1, 1.1, 1, 1, 1, 1.3, 0.5]
_HEADERS = ["Style / Operation Breakdown", "Ops", "SMV", "Sections", "Target", "Eff", "Saved", ""]
_PAGE_SIZE = 10


def _cell(column, text: str) -> None:
    column.markdown(f"<span style='color:#475569;font-size:.9rem'>{text}</span>", unsafe_allow_html=True)


def pick_ob(key: str, *, empty_hint: str = "No Operation Breakdown yet — upload one in Data Import.") -> str | None:
    """Renders the list; returns the name of the OB the user clicked (or None)."""
    summaries = db.list_ob_summaries()
    if summaries.empty:
        st.info(empty_hint)
        return None

    search = st.text_input("Search styles", placeholder="Search by style name…", key=f"{key}_search",
                           label_visibility="collapsed", icon=":material/search:")
    if search.strip():
        summaries = summaries[summaries["name"].str.contains(search.strip(), case=False, regex=False)]
    if summaries.empty:
        st.caption("No style matches that search.")
        return None

    show_all = st.session_state.get(f"{key}_all", False)
    visible = summaries if show_all else summaries.head(_PAGE_SIZE)

    header = st.columns(_WIDTHS)
    for column, label in zip(header, _HEADERS):
        column.markdown(f"<span style='color:#64748B;font-size:.74rem;font-weight:700;text-transform:uppercase;"
                        f"letter-spacing:.06em'>{label}</span>", unsafe_allow_html=True)

    chosen = None
    for i, r in enumerate(visible.itertuples()):
        with st.container(border=True):
            cols = st.columns(_WIDTHS, vertical_alignment="center")
            if cols[0].button(r.name, key=f"{key}_open_{i}", type="tertiary", use_container_width=True):
                chosen = r.name
            _cell(cols[1], str(r.operations))
            _cell(cols[2], f"{r.total_smv:.2f}")
            _cell(cols[3], str(r.sections))
            _cell(cols[4], f"{r.target:,.0f}")
            _cell(cols[5], f"{r.plan_efficiency * 100:.0f}%")
            _cell(cols[6], r.created_at.strftime("%d %b %Y") if r.created_at is not None else "")
            if cols[7].button("", key=f"{key}_go_{i}", type="tertiary", icon=":material/chevron_right:"):
                chosen = r.name

    if len(summaries) > _PAGE_SIZE:
        label = "Show fewer" if show_all else f"Show all {len(summaries)} styles"
        if st.button(label, key=f"{key}_toggle", type="tertiary"):
            st.session_state[f"{key}_all"] = not show_all
            st.rerun()
    st.caption(f"{len(summaries)} style(s) — click a style to open it.")
    return chosen
