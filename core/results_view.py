"""Shared result section for Layout Balancing and Absentee Balancing pages:
summary metrics, the editable table (drag to reorder, per-row employee
picker) and the Excel download."""
from __future__ import annotations

import streamlit as st

from core.state import learn_assignments, save_ob_order

from core.export import to_excel_bytes
from core.evidence import diagnose_unstaffed
from core.learning import learned_qualifications, operation_order
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


_MAX_SUGGESTIONS = 40


def _suggester(evidence, employee_line: dict, pool):
    """Ordered candidates per operation: skilled, then partial, then related
    wording (strongest first), then machine-experienced; same line first."""
    from core.staffing import normalize_machine

    def suggest(skill_group: str, line: str, machine: str) -> list[str]:
        def on_line_first(emps) -> list[str]:
            return sorted(emps, key=lambda e: (employee_line.get(e) != line, e))

        ordered: list[str] = []
        related = evidence.related.get(skill_group, {})
        tiers = (
            on_line_first(evidence.strong.get(skill_group, ())),
            on_line_first(evidence.partial.get(skill_group, ())),
            sorted(related, key=lambda e: (-related[e], employee_line.get(e) != line, e)),
            on_line_first(evidence.machine_candidates({normalize_machine(machine)})),
        )
        for tier in tiers:
            ordered.extend(e for e in tier if e not in ordered and (pool is None or e in pool))
        return ordered[:_MAX_SUGGESTIONS]

    return suggest


def _component_row(r: ResultRow) -> dict:
    return {
        "id": r.id, "line": r.line, "operation": r.operation, "machine": r.machine_type,
        "sam": round(r.sam, 4), "target": round(r.target), "sg": r.skill_group,
        "sys": r.system_employee, "basis": r.basis, "suggest": list(r.suggestions),
    }


def _learn_button(prefix: str, result: RunResult, rows, order, assign) -> None:
    """Persists what the user did to this layout: manual employee choices
    become learned skills; the row sequence becomes the OB's sequence."""
    st.caption("Happy with this layout? Save it so the app learns your manual assignments and operation sequence.")
    if not st.button("🧠 Save layout & learn", key=f"{prefix}_learn"):
        return
    learned = learn_assignments(learned_qualifications(rows, assign))
    new_order = operation_order(rows, order, result.ob_row_ids)
    order_changed = new_order != operation_order(rows, [], result.ob_row_ids)
    if order_changed:
        save_ob_order(new_order)
    st.success(
        f"Learned {learned} employee–operation pair(s)"
        + (" and saved the new operation sequence." if order_changed else ".")
        + " Used automatically from the next run."
    )


def render_results(*, prefix: str, employees_df, file_stem: str) -> None:
    """Renders the result of the last run stored under `prefix`."""
    result: RunResult | None = st.session_state.get(f"{prefix}_result")
    if not result:
        return
    ctx = result.context

    rows = build_rows(result.units, result.line_order, _suggester(ctx.evidence, ctx.employee_line, ctx.pool))
    order, assign = reconcile(rows, st.session_state.get(f"{prefix}_overrides"))

    st.divider()
    summary = st.container()
    st.caption("Drag ⠿ to reorder rows · click an Employee Code to search and change it · same-colour rows share one operator.")

    value = results_table(
        key=f"{prefix}_table_{st.session_state.get(f'{prefix}_run', 0)}",
        rows=[_component_row(r) for r in rows],
        order=order,
        assign=assign,
        employees=employee_payload(employees_df, ctx.profiles, {r.skill_group for r in rows}, ctx.pool),
        palette=PALETTE,
    )
    if value:
        state = {"order": value.get("order", []), "assign": value.get("assign", {})}
        st.session_state[f"{prefix}_overrides"] = state
        order, assign = reconcile(rows, state)

    records = effective_records(rows, order, assign, ctx.employee_names)
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

    diagnosis = diagnose_unstaffed(result.units, ctx.evidence)
    if not diagnosis.empty:
        with st.expander(f"Why are {len(diagnosis)} operation(s) unstaffed by the system?"):
            st.caption("free/total = people with that level of evidence who were still available / in total.")
            st.dataframe(diagnosis, width="stretch", hide_index=True)

    _learn_button(prefix, result, rows, order, assign)

    st.download_button(
        "⬇️ Download Excel",
        to_excel_bytes(records),
        file_name=f"{file_stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
