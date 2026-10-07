"""
Turns pooling bins (and any standalone, non-pooled operations) into actual
named employee assignments.

Selection is tiered, strongest evidence first:
  1. SKILL    - employee holds the exact Skill Group(s) required.
  2. MACHINE  - employee has demonstrated experience on the required
                Machine Type(s) (explicit skill, role, or any skill group
                that lives on that machine in the active OB).
Within a tier, an employee already on the operation's line is preferred.
Ties are broken alphabetically (deterministic).

Each row an AssignedUnit carries in `operations` is a 5-tuple:
    (line, operation, skill_group, minutes, target)
"""
from __future__ import annotations

from dataclasses import dataclass

from core.formulas import OperationCalc
from core.pooling import Bin

BASIS_SKILL = "skill"
BASIS_MACHINE = "machine"


@dataclass
class AssignedUnit:
    lines: set
    operations: list          # list of (line, operation, skill_group, minutes, target)
    total_minutes: float
    employee: str | None
    cross_line: bool
    color_key: str            # shared key for operations bundled onto the same person
    understaffed: bool = False
    basis: str = ""           # BASIS_SKILL | BASIS_MACHINE | "" (unstaffed)


def normalize_machine(machine_type) -> str:
    """Canonical machine-type key: whitespace-collapsed, upper-case."""
    return " ".join(str(machine_type or "").split()).upper()


def _qualified_by_skill(skill_groups: set, skill_matrix: dict) -> set:
    """Employees qualified for ALL given skill groups (a merged bin needs
    one person who can do everything bundled into it)."""
    qualified = None
    for sg in skill_groups:
        holders = {emp for emp, sgs in skill_matrix.items() if sg in sgs}
        qualified = holders if qualified is None else qualified & holders
        if not qualified:
            return set()
    return qualified or set()


def _qualified_by_machine(machines: set, employee_machines: dict) -> set:
    """Employees with experience on ALL given machine types."""
    machines = {m for m in machines if m}
    if not machines:
        return set()
    return {emp for emp, ms in employee_machines.items() if machines <= ms}


def _prefer_lines(pool: set, lines: set, employee_line: dict) -> str:
    same_line = {e for e in pool if employee_line.get(e) in lines}
    return sorted(same_line or pool)[0]


def select_employee(
    skill_groups: set,
    machines: set,
    lines: set,
    skill_matrix: dict,
    employee_machines: dict,
    employee_line: dict,
    used: set,
) -> tuple[str | None, str]:
    """Returns (employee, basis) or (None, "") when nobody is available."""
    tiers = (
        (_qualified_by_skill(skill_groups, skill_matrix), BASIS_SKILL),
        (_qualified_by_machine(machines, employee_machines), BASIS_MACHINE),
    )
    for pool, basis in tiers:
        available = pool - used
        if available:
            return _prefer_lines(available, lines, employee_line), basis
    return None, ""


def assign_bins(
    bins: list[Bin],
    skill_matrix: dict,                      # {employee: set(skill_group)}
    employee_line: dict,                     # {employee: line}
    used_employees: set | None = None,
    employee_machines: dict | None = None,   # {employee: set(normalized machine type)}
) -> list[AssignedUnit]:
    used = used_employees if used_employees is not None else set()
    employee_machines = employee_machines or {}
    results = []

    for i, b in enumerate(sorted(bins, key=lambda b: -len(b.skill_groups))):
        chosen, basis = select_employee(
            b.skill_groups,
            {normalize_machine(c.machine_type) for c in b.chunks},
            b.lines,
            skill_matrix,
            employee_machines,
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
    skill_matrix: dict,
    employee_line: dict,
    used_employees: set,
    employee_machines: dict | None = None,
) -> list[AssignedUnit]:
    """One unit per head needed, each a separately named (or unstaffed)
    employee. An operation needing 3 heads yields 3 units, each carrying
    an even share of the operation's Target."""
    employee_machines = employee_machines or {}
    machines = {normalize_machine(calc.machine_type)}
    minutes_each = calc.work_minutes / calc.head_allocated
    units = []
    for _ in range(calc.head_allocated):
        chosen, basis = select_employee(
            {calc.skill_group}, machines, {line},
            skill_matrix, employee_machines, employee_line, used_employees,
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
