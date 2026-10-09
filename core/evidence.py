"""
Builds the StaffingEvidence for one Operation Breakdown from the database:
who is strongly qualified, partially qualified, related-skilled, and
machine-experienced for each Skill Group in that OB.
"""
from __future__ import annotations

import core.db as db
from core.inference import infer_weak_evidence
from core.staffing import StaffingEvidence, normalize_machine

_FUZZY_MACHINE_INFERENCE_THRESHOLD = 75


def _invert(skill_matrix: dict) -> dict:
    """{employee: set(sg)} -> {sg: set(employee)}"""
    out: dict = {}
    for emp, sgs in skill_matrix.items():
        for sg in sgs:
            out.setdefault(sg, set()).add(emp)
    return out


def _employee_machines(ob_rows: list[dict], skill_matrix: dict, skill_pairs) -> dict:
    """
    {employee: set(normalized machine type)}. Sources:
      1. Machine types of every Skill Group the employee holds, in THIS OB.
      2. Skill text that did not resolve exactly: fuzzy-matched against the
         OB's own operations.
      3. Machine Type given explicitly in the uploaded skill file.
      4. Roles: every machine type of every role the employee holds.
    """
    from core.matching import match_against_rows

    sg_to_machines: dict = {}
    for row in ob_rows or []:
        sg_to_machines.setdefault(row.get("skill_group"), set()).add(normalize_machine(row.get("machine_type")))

    out: dict = {}

    def grant(emp: str, machines) -> None:
        machines = {m for m in machines if m}
        if machines:
            out.setdefault(emp, set()).update(machines)

    for emp, sgs in skill_matrix.items():
        for sg in sgs:
            grant(emp, sg_to_machines.get(sg, ()))

    if skill_pairs is not None:
        text_cache: dict = {}
        for _, r in skill_pairs.iterrows():
            emp = str(r["employee"])
            grant(emp, {normalize_machine(r.get("machine_type"))})
            text = r.get("skill_text")
            if ob_rows and text:
                if text not in text_cache:
                    sg, _score = match_against_rows(text, ob_rows, threshold=_FUZZY_MACHINE_INFERENCE_THRESHOLD)
                    text_cache[text] = sg_to_machines.get(sg, set()) if sg else set()
                grant(emp, text_cache[text])

    roles = db.list_roles()
    for emp, role_names in db.list_employee_roles().items():
        for role_name in role_names:
            grant(emp, {normalize_machine(m) for m in roles.get(role_name, [])})

    return out


def build_staffing_evidence(ob_rows: list[dict], skill_matrix: dict) -> StaffingEvidence:
    """skill_matrix: {employee: set(skill_group)} from core.state.skill_matrix_dict."""
    skill_pairs = db.list_skill_pairs()
    partial, related = infer_weak_evidence(ob_rows, skill_pairs)
    return StaffingEvidence(
        strong=_invert(skill_matrix),
        partial=partial,
        related=related,
        machines=_employee_machines(ob_rows, skill_matrix, skill_pairs),
    )


def diagnose_unstaffed(units: list, op_lookup: dict, evidence: StaffingEvidence):
    """One row per unstaffed operation explaining how much evidence existed
    and how much of it was already used elsewhere."""
    import pandas as pd

    used = {u.employee for u in units if u.employee}
    rows = []
    for u in units:
        if u.employee:
            continue
        for (line, operation, skill_group, _minutes, _target) in u.operations:
            machine, _sam = op_lookup.get(operation, ("", None))
            strong = set(evidence.strong.get(skill_group, ()))
            partial = set(evidence.partial.get(skill_group, ()))
            related = set(evidence.related.get(skill_group, {}))
            experienced = evidence.machine_candidates({normalize_machine(machine)})
            rows.append(
                {
                    "Line": line,
                    "Operation": operation,
                    "Machine Type": machine,
                    "Skilled (free/total)": f"{len(strong - used)}/{len(strong)}",
                    "Partial (free/total)": f"{len(partial - used)}/{len(partial)}",
                    "Related (free/total)": f"{len(related - used)}/{len(related)}",
                    "Machine-experienced (free/total)": f"{len(experienced - used)}/{len(experienced)}",
                }
            )
    return pd.DataFrame(rows)
