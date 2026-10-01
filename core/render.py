"""Turns a list of AssignedUnit into a color-coded, per-operation table for
display. Every merged bin (color_key != 'unmerged') gets its own color;
different combos never share a color; unmerged rows stay plain."""
from __future__ import annotations

import pandas as pd

PALETTE = [
    "#D9EAD3", "#CFE2F3", "#FFF2CC", "#F4CCCC", "#E1D5F0",
    "#D0E0E3", "#FCE5CD", "#EAD1DC", "#D9D2E9", "#C9DAF8",
]


def units_to_table(units) -> tuple[pd.DataFrame, dict]:
    color_keys = [u.color_key for u in units if u.color_key != "unmerged"]
    unique_keys = list(dict.fromkeys(color_keys))
    color_map = {k: PALETTE[i % len(PALETTE)] for i, k in enumerate(unique_keys)}

    rows = []
    for u in units:
        for (line, operation, skill_group, minutes) in u.operations:
            rows.append(
                {
                    "Line": line,
                    "Operation": operation,
                    "Skill Group": skill_group,
                    "Minutes": round(minutes, 1),
                    "Assigned To": u.employee or "⚠️ UNSTAFFED",
                    "Cross-Line": "Yes" if u.cross_line else "",
                    "_color_key": u.color_key,
                }
            )
    df = pd.DataFrame(rows)
    return df, color_map


def style_table(df: pd.DataFrame, color_map: dict):
    def highlight(row):
        key = row["_color_key"]
        color = color_map.get(key)
        return [f"background-color: {color}" if color else "" for _ in row]

    display_df = df.drop(columns=["_color_key"])
    styled = df.style.apply(highlight, axis=1).hide(axis="columns", subset=["_color_key"])
    return styled
