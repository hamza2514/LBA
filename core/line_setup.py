"""Per-line style selection for multi-line balancing: each selected line runs
its own Operation Breakdown with its own target and plan efficiency."""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from core.state import get_ob
from core.ui import warn_missing_sections


@dataclass(frozen=True)
class LineSetup:
    line: str
    ob_name: str
    ob: dict
    target: float
    plan_efficiency: float

    @property
    def rows(self) -> list[dict]:
        return self.ob["rows"]

    @property
    def row_ids(self) -> list[int]:
        return [r["id"] for r in self.ob["rows"]]


def combined_rows(setups: list[LineSetup]) -> list[dict]:
    """Operations of every style in use, de-duplicated — what people's
    qualifications are matched against."""
    seen: set = set()
    rows = []
    for setup in setups:
        for r in setup.rows:
            key = (r["operation"], r.get("machine_type"), r["skill_group"])
            if key not in seen:
                seen.add(key)
                rows.append(r)
    return rows


def select_line_styles(
    prefix: str, lines: list[str], obs: list[str], default_ob: str | None = None
) -> tuple[list[LineSetup], float]:
    """UI: one row per line (style, target, efficiency) plus a shared shift time."""
    loaded: dict = {}

    def ob_of(name: str) -> dict:
        if name not in loaded:
            loaded[name] = get_ob(name)
        return loaded[name]

    widths = [0.8, 3.4, 1, 1]
    for column, label in zip(st.columns(widths), ["Line", "Style", "Target / shift", "Plan eff"]):
        column.markdown(f"<span style='color:#64748B;font-size:.74rem;font-weight:700;text-transform:uppercase;"
                        f"letter-spacing:.06em'>{label}</span>", unsafe_allow_html=True)

    setups: list[LineSetup] = []
    for line in lines:
        c0, c1, c2, c3 = st.columns(widths, vertical_alignment="center")
        c0.markdown(f"<div style='padding-top:6px;font-weight:700'>{line}</div>", unsafe_allow_html=True)
        ob_name = c1.selectbox("Style (Operation Breakdown)", options=obs, key=f"{prefix}_ob_{line}_{default_ob}",
                               index=obs.index(default_ob) if default_ob in obs else 0,
                               label_visibility="collapsed")
        ob = ob_of(ob_name)
        target = c2.number_input("Target", min_value=1.0, value=float(ob["target"]),
                                 key=f"{prefix}_target_{line}_{ob_name}", label_visibility="collapsed")
        eff = c3.number_input("Plan Eff", min_value=0.01, max_value=1.0, value=float(ob["plan_efficiency"]),
                              key=f"{prefix}_eff_{line}_{ob_name}", label_visibility="collapsed")
        setups.append(LineSetup(line, ob_name, ob, target, eff))

    for name in dict.fromkeys(s.ob_name for s in setups):
        warn_missing_sections(ob_of(name)["rows"], name)

    first = setups[0].ob if setups else None
    shift_time = st.columns([1.5, 4])[0].number_input(
        "Shift time (min) — shared by all lines", min_value=1.0,
        value=float(first["shift_time"]) if first else 480.0, key=f"{prefix}_shift_multi",
    )
    return setups, shift_time
