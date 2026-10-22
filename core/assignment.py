"""
Turns pooling bins and standalone operations into named employee assignments.

Selection is evidence-ranked (see core.staffing): for every unit of work the
employee with the strongest evidence wins -
    strong (skill)  >  partial skill  >  related wording  >  machine type
- with ties broken by "already on the unit's line", then employee code.
Machine-type experience is only a fallback when nobody has skill evidence.

Units are staffed most-constrained-first (fewest free candidates), so scarce
employees are not consumed by work that has plenty of alternatives.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.formulas import OperationCalc
from core.pooling import Bin
from core.staffing import StaffingEvidence, normalize_machine

BASIS_SKILL = "Skill"
BASIS_PARTIAL = "Partial skill"
BASIS_RELATED = "Related skill"
BASIS_MACHINE = "Machine type"


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
    """One person's work: one or more operations, one (optional) employee."""
    lines: set
    operations: list[OpAssignment]
    total_minutes: float
    employee: str | None = None
    cross_line: bool = False
    understaffed: bool = True
    basis: str = ""

    @property
    def skill_groups(self) -> set:
        return {op.skill_group for op in self.operations if op.skill_group}

    @property
    def machines(self) -> set:
        return {m for m in (normalize_machine(op.machine_type) for op in self.operations) if m}


# ---------------------------------------------------------------- selection
def _basis(strong: int, partial: int, related: float, group_count: int) -> str:
    if group_count and strong == group_count:
        return BASIS_SKILL
    if strong or partial:
        return BASIS_PARTIAL
    if related > 0:
        return BASIS_RELATED
    return BASIS_SKILL if not group_count else BASIS_MACHINE


def select_employee(
    skill_groups: set,
    machines: set,
    lines: set,
    evidence: StaffingEvidence,
    employee_line: dict,
    used: set,
) -> tuple[str | None, str]:
    """Best free employee for a unit of work -> (employee, basis) or (None, "")."""
    candidates = evidence.candidates(skill_groups) - used
    by_machine = False
    if not candidates:
        candidates = evidence.machine_candidates(machines) - used
        by_machine = True
    if not candidates:
        return None, ""

    def rank(emp: str) -> tuple:
        strong, partial, related = evidence.score(emp, skill_groups)
        return (-strong, -partial, -related, employee_line.get(emp) not in lines, emp)

    chosen = min(candidates, key=rank)
    if by_machine:
        return chosen, BASIS_MACHINE
    strong, partial, related = evidence.score(chosen, skill_groups)
    return chosen, _basis(strong, partial, related, len(skill_groups))


# -------------------------------------------------------------- unit builders
def unit_from_bin(bin_: Bin) -> AssignedUnit:
    return AssignedUnit(
        lines=set(bin_.lines),
        operations=[
            OpAssignment(c.line, c.seq, c.operation, c.machine_type, c.sam, c.skill_group,
                         c.section, c.minutes, c.minutes / c.sam if c.sam else 0.0)
            for c in bin_.chunks
        ],
        total_minutes=bin_.total_minutes,
        cross_line=bin_.cross_line,
    )


def units_for_operation(line: str, calc: OperationCalc) -> list[AssignedUnit]:
    """One unit per head needed; each gets an even share of the Target."""
    minutes = calc.work_minutes / calc.head_allocated
    return [
        AssignedUnit(
            lines={line},
            operations=[OpAssignment(line, calc.seq, calc.operation, calc.machine_type, calc.sam,
                                     calc.skill_group, calc.section, minutes, calc.target_per_employee)],
            total_minutes=minutes,
        )
        for _ in range(calc.head_allocated)
    ]


# ------------------------------------------------------------------ assigning
def assign_units(
    units: list[AssignedUnit],
    evidence: StaffingEvidence,
    employee_line: dict,
) -> list[AssignedUnit]:
    """Staffs every unit in place, most-constrained first; returns `units`
    in their original order."""
    used: set = set()
    pool_of = {
        id(u): evidence.candidates(u.skill_groups) or evidence.machine_candidates(u.machines)
        for u in units
    }
    pending = list(units)
    while pending:
        unit = min(pending, key=lambda u: (len(pool_of[id(u)] - used), -len(u.skill_groups)))
        pending.remove(unit)
        chosen, basis = select_employee(
            unit.skill_groups, unit.machines, unit.lines, evidence, employee_line, used
        )
        unit.employee, unit.basis, unit.understaffed = chosen, basis, chosen is None
        if chosen:
            used.add(chosen)
    return units
