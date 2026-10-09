"""
Turns pooling bins (and any standalone, non-pooled operations) into actual
named employee assignments.

Selection is evidence-ranked (see core.staffing.StaffingEvidence):
  1. Skill-based evidence, strongest first. A pooled bin spanning several
     operations goes to whoever covers the MOST of them (holding at least one
     is enough; covering all is best), then partial-component evidence, then
     related-wording evidence.
  2. Machine-type experience, only when nobody has any skill-based evidence.
Ties prefer an employee already on the unit's line, then alphabetical.

Each row an AssignedUnit carries in `operations` is a 5-tuple:
    (line, operation, skill_group, minutes, target)
"""
from __future__ import annotations

from dataclasses import dataclass

from core.formulas import OperationCalc
from core.pooling import Bin
from core.staffing import StaffingEvidence, normalize_machine  # noqa: F401  (re-exported)

BASIS_SKILL = "skill"          # holds every required skill
BASIS_PARTIAL = "partial"      # holds some of the required skills / component skills
BASIS_RELATED = "related"      # holds similarly-worded skills
BASIS_MACHINE = "machine"      # same machine type only


@dataclass
class AssignedUnit:
    lines: set
    operations: list          # list of (line, operation, skill_group, minutes, target)
    total_minutes: float
    employee: str | None
    cross_line: bool
    color_key: str            # shared key for operations bundled onto the same person
    understaffed: bool = False
    basis: str = ""           # BASIS_* constant, "" when unstaffed


def _basis_for(score: tuple, group_count: int) -> str:
    strong, partial, _related = score
    if strong == group_count:
        return BASIS_SKILL
    if strong or partial:
        return BASIS_PARTIAL
    return BASIS_RELATED


def select_employee(
    skill_groups: set,
    machines: set,
    lines: set,
    evidence: StaffingEvidence,
    employee_line: dict,
    used: set,
) -> tuple[str | None, str]:
    """Returns (employee, basis) or (None, "") when nobody is available."""

    def rank(emp: str, score: tuple) -> tuple:
        negated = tuple(-x for x in score)
        return (negated, employee_line.get(emp) not in lines, emp)

    scored = {
        emp: evidence.score(emp, skill_groups)
        for emp in evidence.candidates(skill_groups) - used
    }
    scored = {emp: s for emp, s in scored.items() if any(s)}
    if scored:
        best = min(scored, key=lambda e: rank(e, scored[e]))
        return best, _basis_for(scored[best], len(skill_groups))

    fallback = evidence.machine_candidates(machines) - used
    if fallback:
        best = min(fallback, key=lambda e: (employee_line.get(e) not in lines, e))
        return best, BASIS_MACHINE
    return None, ""


def assign_bins(
    bins: list[Bin],
    evidence: StaffingEvidence,
    employee_line: dict,
    used_employees: set | None = None,
) -> list[AssignedUnit]:
    used = used_employees if used_employees is not None else set()
    results = []

    for i, b in enumerate(sorted(bins, key=lambda b: -len(b.skill_groups))):
        chosen, basis = select_employee(
            b.skill_groups,
            {normalize_machine(c.machine_type) for c in b.chunks},
            b.lines,
            evidence,
            employee_line,
            used,
        )
        if chosen:
            used.add(chosen)

        results.append(
            AssignedUnit(
                lines=set(b.lines),
                operations=[
                    (c.line, c.operation, c.skill_group, c.minutes, (c.minutes / c.sam if c.sam else 0.0))
                    for c in b.chunks
                ],
                total_minutes=b.total_minutes,
                employee=chosen,
                cross_line=b.cross_line,
                color_key=f"bin{i}" if len(b.chunks) > 1 else "unmerged",
                understaffed=chosen is None,
                basis=basis,
            )
        )
    return results


def assign_standalone(
    line: str,
    calc: OperationCalc,
    evidence: StaffingEvidence,
    employee_line: dict,
    used_employees: set,
) -> list[AssignedUnit]:
    """One unit per head needed, each a separately named (or unstaffed)
    employee. An operation needing 3 heads yields 3 units, each carrying
    an even share of the operation's Target."""
    machines = {normalize_machine(calc.machine_type)}
    minutes_each = calc.work_minutes / calc.head_allocated
    units = []
    for _ in range(calc.head_allocated):
        chosen, basis = select_employee(
            {calc.skill_group}, machines, {line}, evidence, employee_line, used_employees,
        )
        if chosen:
            used_employees.add(chosen)
        units.append(
            AssignedUnit(
                lines={line},
                operations=[(line, calc.operation, calc.skill_group, minutes_each, calc.target_per_employee)],
                total_minutes=minutes_each,
                employee=chosen,
                cross_line=False,
                color_key="unmerged",
                understaffed=chosen is None,
                basis=basis,
            )
        )
    return units
