"""
Ties formulas.py + pooling.py + assignment.py together into the three real
balancing runs the app offers:
  - run_single_line()   Module 2
  - run_multi_line()    Module 3 (and Module 4, Absentee, calls this with a
                         pre-filtered present-only skill_matrix/employee set)
"""
from __future__ import annotations

from core.formulas import compute_ob_table, OperationCalc
from core.pooling import identify_chunks, pack_same_line, pack_multi_line
from core.assignment import assign_bins, assign_standalone, AssignedUnit


def run_single_line(
    line: str,
    ob_rows: list[dict],
    shift_time: float,
    target: float,
    plan_efficiency: float,
    skill_matrix: dict,
    employee_line: dict,
) -> tuple[list[OperationCalc], list[AssignedUnit]]:
    calcs = compute_ob_table(ob_rows, shift_time, target, plan_efficiency)
    chunks = identify_chunks(line, calcs, shift_time)
    bins = pack_same_line(chunks, shift_time)
    units = assign_bins(bins, skill_matrix, employee_line)

    used = {u.employee for u in units if u.employee}
    pooled_op_names = {c.operation for b in bins for c in b.chunks}

    for c in calcs:
        if c.operation in pooled_op_names:
            continue
        units.extend(assign_standalone(line, c, skill_matrix, employee_line, used))

    return calcs, units


def run_multi_line(
    lines: list[str],
    ob_rows_by_line: dict,
    shift_time: float,
    target: float,
    plan_efficiency: float,
    skill_matrix: dict,
    employee_line: dict,
) -> tuple[dict, list[AssignedUnit]]:
    calcs_by_line = {
        line: compute_ob_table(ob_rows_by_line[line], shift_time, target, plan_efficiency)
        for line in lines
    }
    chunks_by_line = {
        line: identify_chunks(line, calcs, shift_time) for line, calcs in calcs_by_line.items()
    }
    bins = pack_multi_line(chunks_by_line, shift_time)
    units = assign_bins(bins, skill_matrix, employee_line)

    used = {u.employee for u in units if u.employee}
    bundled = {(c.line, c.operation) for b in bins for c in b.chunks}

    for line, calcs in calcs_by_line.items():
        for c in calcs:
            if (line, c.operation) in bundled:
                continue
            units.extend(assign_standalone(line, c, skill_matrix, employee_line, used))

    return calcs_by_line, units
