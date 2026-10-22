"""Everything a balancing run needs about people, computed once per run."""
from __future__ import annotations

from dataclasses import dataclass

from core.evidence import build_staffing_evidence
from core.staffing import StaffingEvidence
from core.state import employee_line_dict, employee_names_dict, employee_skill_profiles, skill_matrix_dict


@dataclass(frozen=True)
class RunContext:
    evidence: StaffingEvidence
    profiles: dict
    employee_line: dict
    employee_names: dict
    pool: frozenset | None = None  # employees allowed in the dropdown (None = everyone)


def build_context(ob_rows: list[dict], present: set | None = None) -> RunContext:
    """present: restrict staffing (and the dropdown) to these employees."""
    skill_matrix = skill_matrix_dict(ob_rows=ob_rows)
    evidence = build_staffing_evidence(ob_rows, skill_matrix)
    employee_line = employee_line_dict()
    if present is not None:
        evidence = evidence.restrict_to(present)
        employee_line = {e: ln for e, ln in employee_line.items() if e in present}
    return RunContext(
        evidence=evidence,
        profiles=employee_skill_profiles(ob_rows=ob_rows),
        employee_line=employee_line,
        employee_names=employee_names_dict(),
        pool=frozenset(present) if present is not None else None,
    )
