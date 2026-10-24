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


def select_line_styles(prefix: str, lines: list[str], obs: list[str]) -> tuple[list[LineSetup], float]:
    """UI: one row per line (style, target, efficiency) plus a shared shift time."""
    loaded: dict = {}

    def ob_of(name: str) -> dict:
        if name not in loaded:
            loaded[name] = get_ob(name)
        return loaded[name]

    setups: list[LineSetup] = []
    for line in lines:
        c0, c1, c2, c3 = st.columns([1, 3, 1.3, 1.3])
        c0.markdown(f"**{line}**")
        ob_name = c1.selectbox("Style (Operation Breakdown)", options=obs, key=f"{prefix}_ob_{line}",
                               label_visibility="collapsed")
        ob = ob_of(ob_name)
        target = c2.number_input("Target", min_value=1.0, value=float(ob["target"]),
                                 key=f"{prefix}_target_{line}_{ob_name}", help="Units/shift for this line")
        eff = c3.number_input("Plan Eff", min_value=0.01, max_value=1.0, value=float(ob["plan_efficiency"]),
                              key=f"{prefix}_eff_{line}_{ob_name}", help="Plan efficiency for this line")
        setups.append(LineSetup(line, ob_name, ob, target, eff))

    for name in dict.fromkeys(s.ob_name for s in setups):
        warn_missing_sections(ob_of(name)["rows"], name)

    first = setups[0].ob if setups else None
    shift_time = st.number_input(
        "Shift Time (minutes) — shared by all lines", min_value=1.0,
        value=float(first["shift_time"]) if first else 480.0, key=f"{prefix}_shift_multi",
    )
    return setups, shift_time
