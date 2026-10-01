"""
Turns pooling bins (and any standalone, non-pooled operations) into actual
named employee assignments.

Line-aware rule (confirmed): prefer a qualified employee already on the
operation's line; only look at other lines if nobody on that line qualifies.
For a cross-line bin, the person is inherently working across the lines
involved, so candidates are drawn from either of those lines first.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.pooling import Bin


@dataclass
class AssignedUnit:
    lines: set
    operations: list          # list of (line, operation, skill_group, minutes)
    total_minutes: float
    employee: str | None
    cross_line: bool
    color_key: str            # shared key for operations bundled onto the same person
    understaffed: bool = False


def _qualified_employees(skill_groups: set, skill_matrix: dict) -> set:
    """skill_matrix: {employee: set(skill_groups)}. Returns employees
    qualified for ALL given skill groups (a merged bin needs one person who
    can do every operation bundled into it)."""
    qualified = None
    for sg in skill_groups:
        holders = {emp for emp, sgs in skill_matrix.items() if sg in sgs}
        qualified = holders if qualified is None else (qualified & holders)
        if not qualified:
            return set()
    return qualified or set()


def assign_bins(
    bins: list[Bin],
    skill_matrix: dict,          # {employee: set(skill_group)}
    employee_line: dict,         # {employee: line}
    used_employees: set | None = None,
) -> list[AssignedUnit]:
    used = used_employees if used_employees is not None else set()
    results = []

    # largest / most-constrained bins first so scarce specialists aren't
    # accidentally used up on an easy bin before a hard one needs them
    ordered = sorted(bins, key=lambda b: -len(b.skill_groups))

    for i, b in enumerate(ordered):
        sgs = b.skill_groups
        candidates = _qualified_employees(sgs, skill_matrix) - used
        bin_lines = b.lines

        same_line = {e for e in candidates if employee_line.get(e) in bin_lines}
        chosen = None
        if same_line:
            chosen = sorted(same_line)[0]
        elif candidates:
            chosen = sorted(candidates)[0]  # had to borrow from another line

        if chosen:
            used.add(chosen)

        results.append(
            AssignedUnit(
                lines=set(bin_lines),
                operations=[(c.line, c.operation, c.skill_group, c.minutes) for c in b.chunks],
                total_minutes=b.total_minutes,
                employee=chosen,
                cross_line=b.cross_line,
                color_key=f"bin{i}" if len(b.chunks) > 1 else "unmerged",
                understaffed=chosen is None,
            )
        )

    return results


def assign_standalone(
    line: str,
    operation: str,
    skill_group: str,
    minutes: float,
    skill_matrix: dict,
    employee_line: dict,
    used_employees: set,
) -> AssignedUnit:
    """For operations that weren't part of any pooling bin — normal
    one-operation-one-person assignment, still line-aware."""
    holders = {emp for emp, sgs in skill_matrix.items() if skill_group in sgs} - used_employees
    same_line = {e for e in holders if employee_line.get(e) == line}
    chosen = sorted(same_line)[0] if same_line else (sorted(holders)[0] if holders else None)
    if chosen:
        used_employees.add(chosen)
    return AssignedUnit(
        lines={line},
        operations=[(line, operation, skill_group, minutes)],
        total_minutes=minutes,
        employee=chosen,
        cross_line=False,
        color_key="unmerged",
        understaffed=chosen is None,
    )
