"""
Ties formulas.py + pooling.py + assignment.py together into the real
balancing runs the app offers:
  - run_single_line()   Layout Balancing, single line
  - run_multi_line()    Layout Balancing multi-line, and Absentee Balancing
                        (called with a pre-filtered present-only pool)
"""
from __future__ import annotations

from core.assignment import AssignedUnit, assign_bins, assign_standalone
from core.formulas import OperationCalc, compute_ob_table
from core.pooling import identify_chunks, pack_multi_line, pack_same_line


def run_single_line(
    line: str,
    ob_rows: list[dict],
    shift_time: float,
    target: float,
    plan_efficiency: float,
    skill_matrix: dict,
    employee_line: dict,
    employee_machines: dict | None = None,
) -> tuple[list[OperationCalc], list[AssignedUnit]]:
    calcs = compute_ob_table(ob_rows, shift_time, target, plan_efficiency)
    bins = pack_same_line(identify_chunks(line, calcs, shift_time), shift_time)
    units = assign_bins(bins, skill_matrix, employee_line, employee_machines=employee_machines)

    used = {u.employee for u in units if u.employee}
    pooled_ops = {c.operation for b in bins for c in b.chunks}

    for c in calcs:
        if c.operation not in pooled_ops:
            units.extend(assign_standalone(line, c, skill_matrix, employee_line, used, employee_machines))

    return calcs, units


def run_multi_line(
    lines: list[str],
    ob_rows_by_line: dict,
    shift_time: float,
    target: float,
    plan_efficiency: float,
    skill_matrix: dict,
    employee_line: dict,
    employee_machines: dict | None = None,
) -> tuple[dict, list[AssignedUnit]]:
    calcs_by_line = {
        line: compute_ob_table(ob_rows_by_line[line], shift_time, target, plan_efficiency)
        for line in lines
    }
    chunks_by_line = {line: identify_chunks(line, calcs, shift_time) for line, calcs in calcs_by_line.items()}
    bins = pack_multi_line(chunks_by_line, shift_time)
    units = assign_bins(bins, skill_matrix, employee_line, employee_machines=employee_machines)

    used = {u.employee for u in units if u.employee}
    bundled = {(c.line, c.operation) for b in bins for c in b.chunks}

    for line, calcs in calcs_by_line.items():
        for c in calcs:
            if (line, c.operation) not in bundled:
                units.extend(assign_standalone(line, c, skill_matrix, employee_line, used, employee_machines))

    return calcs_by_line, units
