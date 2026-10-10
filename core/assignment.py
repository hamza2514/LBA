"""
Turns pooling bins (and standalone, non-pooled operations) into named
employee assignments.

Line-aware rule: prefer a qualified employee already on the operation's
line; only look at other lines if nobody there qualifies. For a cross-line
bin, candidates from either of its lines come first.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.formulas import OperationCalc
from core.pooling import Bin


@dataclass(frozen=True)
class OpAssignment:
    """One result-table row's worth of work."""
    line: str
    seq: int              # position of the operation in the OB
    operation: str
    machine_type: str
    sam: float
    skill_group: str
    section: str
    minutes: float
    target: float


@dataclass
class AssignedUnit:
    lines: set
    operations: list[OpAssignment]
    total_minutes: float
    employee: str | None
    cross_line: bool
    understaffed: bool = False


def qualified_employees(skill_groups: set, skill_matrix: dict) -> set:
    """Employees qualified for ALL given skill groups."""
    qualified = None
    for sg in skill_groups:
        holders = {emp for emp, sgs in skill_matrix.items() if sg in sgs}
        qualified = holders if qualified is None else (qualified & holders)
        if not qualified:
            return set()
    return qualified or set()


def _pick(candidates: set, preferred_lines: set, employee_line: dict) -> str | None:
    same_line = {e for e in candidates if employee_line.get(e) in preferred_lines}
    pool = same_line or candidates
    return min(pool) if pool else None


def assign_bins(
    bins: list[Bin],
    skill_matrix: dict,
    employee_line: dict,
    used_employees: set | None = None,
) -> list[AssignedUnit]:
    used = used_employees if used_employees is not None else set()
    results = []

    for b in sorted(bins, key=lambda b: -len(b.skill_groups)):
        candidates = qualified_employees(b.skill_groups, skill_matrix) - used
        chosen = _pick(candidates, b.lines, employee_line)
        if chosen:
            used.add(chosen)
        results.append(
            AssignedUnit(
                lines=set(b.lines),
                operations=[
                    OpAssignment(c.line, c.seq, c.operation, c.machine_type, c.sam,
                                 c.skill_group, c.section, c.minutes,
                                 c.minutes / c.sam if c.sam else 0.0)
                    for c in b.chunks
                ],
                total_minutes=b.total_minutes,
                employee=chosen,
                cross_line=b.cross_line,
                understaffed=chosen is None,
            )
        )
    return results


def assign_standalone(
    line: str,
    calc: OperationCalc,
    skill_matrix: dict,
    employee_line: dict,
    used_employees: set,
) -> list[AssignedUnit]:
    """One unit per head needed, each a separate named (or unstaffed)
    employee, still line-aware; each gets an even share of the Target."""
    holders_all = {emp for emp, sgs in skill_matrix.items() if calc.skill_group in sgs}
    minutes = calc.work_minutes / calc.head_allocated
    units = []
    for _ in range(calc.head_allocated):
        chosen = _pick(holders_all - used_employees, {line}, employee_line)
        if chosen:
            used_employees.add(chosen)
        units.append(
            AssignedUnit(
                lines={line},
                operations=[
                    OpAssignment(line, calc.seq, calc.operation, calc.machine_type, calc.sam,
                                 calc.skill_group, calc.section, minutes, calc.target_per_employee)
                ],
                total_minutes=minutes,
                employee=chosen,
                cross_line=False,
                understaffed=chosen is None,
            )
        )
    return units
