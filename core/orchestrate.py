"""
Ties formulas + pooling + assignment together into the balancing runs:
  - run_single_line()   single-line Layout Balancing
  - run_multi_line()    multi-line Layout Balancing (Absentee Balancing calls
                        this with evidence restricted to present employees)
"""
from __future__ import annotations

from core.assignment import AssignedUnit, assign_units, unit_from_bin, units_for_operation
from core.formulas import OperationCalc, compute_ob_table
from core.pooling import Bin, identify_chunks, pack_multi_line, pack_same_line
from core.staffing import StaffingEvidence


def _build_units(calcs_by_line: dict, bins: list[Bin]) -> list[AssignedUnit]:
    units = [unit_from_bin(b) for b in bins]
    bundled = {(c.line, c.seq) for b in bins for c in b.chunks}
    for line, calcs in calcs_by_line.items():
        for c in calcs:
            if (line, c.seq) not in bundled:
                units.extend(units_for_operation(line, c))
    return units


def run_single_line(
    line: str,
    ob_rows: list[dict],
    shift_time: float,
    target: float,
    plan_efficiency: float,
    evidence: StaffingEvidence,
    employee_line: dict,
) -> tuple[list[OperationCalc], list[AssignedUnit]]:
    calcs = compute_ob_table(ob_rows, shift_time, target, plan_efficiency)
    bins = pack_same_line(identify_chunks(line, calcs, shift_time), shift_time)
    units = assign_units(_build_units({line: calcs}, bins), evidence, employee_line)
    return calcs, units


def run_multi_line(
    lines: list[str],
    ob_rows_by_line: dict,
    shift_time: float,
    target: float,
    plan_efficiency: float,
    evidence: StaffingEvidence,
    employee_line: dict,
) -> tuple[dict, list[AssignedUnit]]:
    calcs_by_line = {
        line: compute_ob_table(ob_rows_by_line[line], shift_time, target, plan_efficiency)
        for line in lines
    }
    chunks_by_line = {line: identify_chunks(line, calcs, shift_time) for line, calcs in calcs_by_line.items()}
    bins = pack_multi_line(chunks_by_line, shift_time)
    units = assign_units(_build_units(calcs_by_line, bins), evidence, employee_line)
    return calcs_by_line, units
