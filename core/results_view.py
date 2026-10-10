"""Shared result section for Layout Balancing and Absentee Balancing pages:
summary metrics, the editable table (drag to reorder, per-row employee
picker) and the Excel download."""
from __future__ import annotations

import streamlit as st

from core.export import to_excel_bytes
from core.results import (
    PALETTE, ResultRow, RunResult, build_rows, effective_records,
    employee_payload, reconcile, summarize,
)
from core.table_component import results_table


def store_result(prefix: str, result: RunResult) -> None:
    """Saves a fresh run and resets any edits made to the previous one."""
    st.session_state[f"{prefix}_result"] = result
    st.session_state[f"{prefix}_overrides"] = None
    st.session_state[f"{prefix}_run"] = st.session_state.get(f"{prefix}_run", 0) + 1


def _suggester(skill_matrix: dict, employee_line: dict, pool: set | None):
    def suggest(skill_group: str, line: str) -> list[str]:
        qualified = [e for e, sgs in skill_matrix.items() if skill_group in sgs and (pool is None or e in pool)]
        return sorted(qualified, key=lambda e: (employee_line.get(e) != line, e))
    return suggest


def _component_row(r: ResultRow) -> dict:
    return {
        "id": r.id, "line": r.line, "operation": r.operation, "machine": r.machine_type,
        "sam": round(r.sam, 4), "target": round(r.target), "sg": r.skill_group,
        "sys": r.system_employee, "suggest": list(r.suggestions),
    }


def render_results(
    *,
    prefix: str,
    employees_df,
    skill_matrix: dict,
    employee_line: dict,
    employee_names: dict,
    profiles: dict,
    file_stem: str,
    pool: set | None = None,
) -> None:
    """pool: employee codes allowed in the dropdown (None = everyone)."""
    result: RunResult | None = st.session_state.get(f"{prefix}_result")
    if not result:
        return

    rows = build_rows(result.units, result.line_order, _suggester(skill_matrix, employee_line, pool))
    order, assign = reconcile(rows, st.session_state.get(f"{prefix}_overrides"))

    st.divider()
    summary = st.container()
    st.caption("Drag ⠿ to reorder rows · click an Employee Code to search and change it · same-colour rows share one operator.")

    value = results_table(
        key=f"{prefix}_table_{st.session_state.get(f'{prefix}_run', 0)}",
        rows=[_component_row(r) for r in rows],
        order=order,
        assign=assign,
        employees=employee_payload(employees_df, profiles, {r.skill_group for r in rows}, pool),
        palette=PALETTE,
    )
    if value:
        state = {"order": value.get("order", []), "assign": value.get("assign", {})}
        st.session_state[f"{prefix}_overrides"] = state
        order, assign = reconcile(rows, state)

    records = effective_records(rows, order, assign, employee_names)
    stats = summarize(records)
    with summary:
        cols = st.columns(5)
        cols[0].metric("Operations", stats["rows"])
        cols[1].metric("Operators used", stats["operators"])
        cols[2].metric("Operators on 2+ rows", stats["merged"])
        cols[3].metric("Unassigned", stats["unassigned"])
        cols[4].metric("Manual changes", stats["manual"])
        if stats["unassigned"]:
            st.error(f"{stats['unassigned']} operation(s) still have no employee assigned.")
        else:
            st.success("Every operation is staffed.")

    st.download_button(
        "⬇️ Download Excel",
        to_excel_bytes(records),
        file_name=f"{file_stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
