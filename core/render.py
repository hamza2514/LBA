"""Turns a list of AssignedUnit into the requested results table:
Sr#, Line, Operation, Machine Type, SAM, Employee Code, Employee Name,
Target — with merged/pooled operations color-coded so it's visible at a
glance which operations share one person."""
from __future__ import annotations

import pandas as pd

PALETTE = [
    "#D9EAD3", "#CFE2F3", "#FFF2CC", "#F4CCCC", "#E1D5F0",
    "#D0E0E3", "#FCE5CD", "#EAD1DC", "#D9D2E9", "#C9DAF8",
]


def units_to_table(units, op_lookup: dict, employee_names: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """
    op_lookup: {operation_name: (machine_type, sam)} — built from the
    computed OperationCalc list, since AssignedUnit rows only carry
    operation/skill_group/minutes/target, not machine/SAM.
    employee_names: {employee_id: employee_name}
    """
    employee_names = employee_names or {}

    color_keys = [u.color_key for u in units if u.color_key != "unmerged"]
    unique_keys = list(dict.fromkeys(color_keys))
    color_map = {k: PALETTE[i % len(PALETTE)] for i, k in enumerate(unique_keys)}

    rows = []
    for u in units:
        for (line, operation, skill_group, minutes, target) in u.operations:
            machine_type, sam = op_lookup.get(operation, ("", None))
            emp_code = u.employee or ""
            emp_name = employee_names.get(u.employee, "") if u.employee else "⚠️ UNSTAFFED"
            rows.append(
                {
                    "Line": line,
                    "Operation": operation,
                    "Machine Type": machine_type,
                    "SAM": round(sam, 4) if sam is not None else "",
                    "Employee Code": emp_code,
                    "Employee Name": emp_name,
                    "Target": round(target) if target else 0,
                    "Cross-Line": "Yes" if u.cross_line else "",
                    "_color_key": u.color_key,
                }
            )
    df = pd.DataFrame(rows)
    if not df.empty:
        df.insert(0, "Sr#", range(1, len(df) + 1))
    return df, color_map


def style_table(df: pd.DataFrame, color_map: dict):
    def highlight(row):
        key = row["_color_key"]
        color = color_map.get(key)
        return [f"background-color: {color}" if color else "" for _ in row]

    styled = df.style.apply(highlight, axis=1).hide(axis="columns", subset=["_color_key"])
    return styled
