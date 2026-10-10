"""
Operation Breakdown formula engine.

Implements the exact formulas confirmed from formula_references.xlsx.
This is plain arithmetic, not a model — see matching.py for the one place
fuzzy/learned matching actually happens (skill-group identification).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class OperationCalc:
    operation: str
    machine_type: str
    sam: float
    skill_group: str
    shift_target_100: float
    shift_target_eff: float
    manpower_100: float
    manpower_eff: float
    head_allocated: int
    work_minutes: float  # internal only — never shown in the OB view
    target: float = 0.0
    target_per_employee: float = 0.0
    section: str = ""
    seq: int = 0  # position of the operation in the OB (0-based)


def head_allocated_rule(manpower_eff: float) -> int:
    """
    Confirmed rounding rule (NOT plain ceiling):
      - < 1                -> 1 (minimum one person)
      - remainder > 0.3     -> round up
      - remainder <= 0.3    -> round down
    """
    if manpower_eff < 1:
        return 1
    whole = math.floor(manpower_eff)
    remainder = manpower_eff - whole
    return whole + 1 if remainder > 0.3 else whole


def compute_operation(
    operation: str,
    machine_type: str,
    sam: float,
    skill_group: str,
    shift_time: float,
    target: float,
    plan_efficiency: float,
    section: str = "",
    seq: int = 0,
) -> OperationCalc:
    if sam <= 0:
        raise ValueError(f"SAM must be > 0 for operation {operation!r}")

    shift_target_100 = shift_time / sam
    shift_target_eff = shift_target_100 * plan_efficiency
    manpower_100 = target / shift_target_100
    manpower_eff = target / shift_target_eff if shift_target_eff else 0.0
    head = head_allocated_rule(manpower_eff)

    return OperationCalc(
        operation=operation,
        machine_type=machine_type,
        sam=sam,
        skill_group=skill_group,
        shift_target_100=shift_target_100,
        shift_target_eff=shift_target_eff,
        manpower_100=manpower_100,
        manpower_eff=manpower_eff,
        head_allocated=head,
        work_minutes=target * sam,
        target=target,
        target_per_employee=target / head if head else 0.0,
        section=section,
        seq=seq,
    )


def compute_ob_table(rows, shift_time: float, target: float, plan_efficiency: float) -> list[OperationCalc]:
    """rows: ordered iterable of dicts with operation/machine_type/sam/skill_group[/section]."""
    return [
        compute_operation(
            operation=r["operation"],
            machine_type=r["machine_type"],
            sam=float(r["sam"]),
            skill_group=r.get("skill_group") or "",
            shift_time=shift_time,
            target=target,
            plan_efficiency=plan_efficiency,
            section=r.get("section") or "",
            seq=seq,
        )
        for seq, r in enumerate(rows)
    ]
