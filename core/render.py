"""Turns a list of AssignedUnit into the requested results table:
Sr#, Line, Operation, Machine Type, SAM, Employee Code, Employee Name,
Assigned By, Target - with merged/pooled operations color-coded so it's
visible at a glance which operations share one person."""
from __future__ import annotations

import pandas as pd

PALETTE = [
    "#D9EAD3", "#CFE2F3", "#FFF2CC", "#F4CCCC", "#E1D5F0",
    "#D0E0E3", "#FCE5CD", "#EAD1DC", "#D9D2E9", "#C9DAF8",
]

BASIS_LABELS = {
    "skill": "Skill",
    "partial": "Partial skill",
    "related": "Related skill",
    "machine": "Machine type",
}


def units_to_table(units, op_lookup: dict, employee_names: dict | None = None, manual_overrides: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """
    op_lookup: {operation_name: (machine_type, sam)} - built from the
    computed OperationCalc list, since AssignedUnit rows only carry
    operation/skill_group/minutes/target, not machine/SAM.
    employee_names: {employee_id: employee_name}
    manual_overrides: {unit_id: (employee_code, employee_name)} - applied on
    top of the automatic assignment, for units the user filled in by hand.
    """
    employee_names = employee_names or {}
    manual_overrides = manual_overrides or {}

    color_keys = [u.color_key for u in units if u.color_key != "unmerged"]
    unique_keys = list(dict.fromkeys(color_keys))
    color_map = {k: PALETTE[i % len(PALETTE)] for i, k in enumerate(unique_keys)}

    rows = []
    idx = 0
    for unit_id, u in enumerate(units):
        is_manual = (not u.employee) and (unit_id in manual_overrides)
        emp_code, emp_name = (u.employee or ""), (employee_names.get(u.employee, "") if u.employee else "⚠️ UNSTAFFED")
        assigned_by = BASIS_LABELS.get(u.basis, "")
        if is_manual:
            emp_code, emp_name = manual_overrides[unit_id]
            emp_name = emp_name + " (manual)"
            assigned_by = "Manual"
        for (line, operation, skill_group, minutes, target) in u.operations:
            machine_type, sam = op_lookup.get(operation, ("", None))
            rows.append(
                {
                    "Line": line,
                    "Operation": operation,
                    "Machine Type": machine_type,
                    "SAM": round(sam, 4) if sam is not None else "",
                    "Employee Code": emp_code,
                    "Employee Name": emp_name,
                    "Assigned By": assigned_by,
                    "Target": round(target) if target else 0,
                    "Cross-Line": "Yes" if u.cross_line else "",
                    "_color_key": u.color_key,
                    "_row_index": idx,
                    "_unit_id": unit_id,
                }
            )
            idx += 1
    df = pd.DataFrame(rows)
    if not df.empty:
        df.insert(0, "Sr#", range(1, len(df) + 1))
    return df, color_map


def render_manual_assignment_ui(df: pd.DataFrame, employees_df, overrides_key: str):
    """
    Renders a small form letting the user manually assign an employee to
    any UNIT (a single operation, or a merged/cross-line bin) the automatic
    engine couldn't staff - one choice per unit, applied to every row that
    unit covers. Suggestions are sorted so employees already on that unit's
    line(s) come first. Writes choices into st.session_state[overrides_key]
    ({unit_id: (code, name)}) and reruns so the table picks them up.
    """
    import streamlit as st

    if employees_df is None or df.empty:
        return

    unstaffed_rows = df[(df["Employee Code"] == "") & (~df["Employee Name"].str.contains("(manual)", regex=False))]
    if unstaffed_rows.empty:
        return

    unstaffed_units = unstaffed_rows.groupby("_unit_id").agg(
        lines=("Line", lambda s: sorted(set(s))),
        label=("Operation", lambda s: " + ".join(sorted(set(s)))),
    ).reset_index()

    st.divider()
    st.subheader(f"✍️ Manually assign {len(unstaffed_units)} unstaffed operation(s)")
    st.caption("Nobody matched these - pick someone yourself. Same-line employees are listed first. A merged/cross-line operation gets ONE assignment covering all its lines.")

    emp_options_cache: dict = {}
    names = dict(zip(employees_df["employee_id"], employees_df["employee_name"]))

    def options_for_lines(lines):
        key = tuple(lines)
        if key in emp_options_cache:
            return emp_options_cache[key]
        same = employees_df[employees_df["line"].isin(lines)]
        other = employees_df[~employees_df["line"].isin(lines)]
        ordered = list(same["employee_id"]) + list(other["employee_id"])
        labels = ["-- Select --"] + [f"{code} - {names.get(code, '')}" for code in ordered]
        emp_options_cache[key] = labels
        return labels

    if overrides_key not in st.session_state:
        st.session_state[overrides_key] = {}

    with st.form(f"{overrides_key}_form"):
        choices = {}
        for _, row in unstaffed_units.iterrows():
            labels = options_for_lines(row["lines"])
            line_str = " & ".join(row["lines"])
            choice = st.selectbox(
                f"{row['label']} - {line_str}",
                options=labels,
                key=f"{overrides_key}_{row['_unit_id']}",
            )
            if choice != "-- Select --":
                code = choice.split(" - ")[0]
                choices[int(row["_unit_id"])] = (code, names.get(code, ""))
        submitted = st.form_submit_button("Apply manual assignments", type="primary")
        if submitted and choices:
            st.session_state[overrides_key].update(choices)
            st.rerun()


def style_table(df: pd.DataFrame, color_map: dict):
    def highlight(row):
        key = row["_color_key"]
        color = color_map.get(key)
        return [f"background-color: {color}" if color else "" for _ in row]

    hide_cols = [c for c in ["_color_key", "_row_index", "_unit_id"] if c in df.columns]
    return df.style.apply(highlight, axis=1).hide(axis="columns", subset=hide_cols)
