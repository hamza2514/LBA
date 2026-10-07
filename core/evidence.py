"""Machine-type evidence per employee, used by the fallback tier in assignment.py."""
from __future__ import annotations

import core.db as db

def employee_machine_types_dict(ob_rows: list[dict], skill_matrix: dict) -> dict:
    """
    {employee: set(normalized machine type)} - the evidence behind the
    machine-type fallback in assignment.py. Sources, in order:
      1. Every Skill Group the employee holds (already resolved against the
         active OB) -> the machine types those groups sit on in THIS OB.
      2. Skill-matrix text that did not resolve exactly: fuzzy-matched
         (lower threshold) against the OB's own operations.
      3. Machine Type given explicitly in the uploaded skill file.
      4. Roles: every machine type of every role the employee holds.
    """
    from core.assignment import normalize_machine
    from core.matching import match_against_rows

    FUZZY_THRESHOLD = 75

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

    sdf = db.list_skill_pairs()
    if sdf is not None:
        text_cache: dict = {}
        for _, r in sdf.iterrows():
            emp = str(r["employee"])
            grant(emp, {normalize_machine(r.get("machine_type"))})
            text = r.get("skill_text")
            if ob_rows and text:
                if text not in text_cache:
                    sg, _ = match_against_rows(text, ob_rows, threshold=FUZZY_THRESHOLD)
                    text_cache[text] = sg_to_machines.get(sg, set()) if sg else set()
                grant(emp, text_cache[text])

    roles = db.list_roles()
    for emp, role_names in db.list_employee_roles().items():
        for role_name in role_names:
            grant(emp, {normalize_machine(m) for m in roles.get(role_name, [])})

    return out


def diagnose_unstaffed(units: list, op_lookup: dict, skill_matrix: dict, employee_machines: dict):
    """
    One row per unstaffed operation explaining WHY nobody was found:
    how many employees hold the skill / machine experience at all, and how
    many of them are still free (not already assigned elsewhere).
    """
    import pandas as pd
    from core.assignment import normalize_machine

    used = {u.employee for u in units if u.employee}
    rows = []
    for u in units:
        if u.employee:
            continue
        for (line, operation, skill_group, _minutes, _target) in u.operations:
            machine, _sam = op_lookup.get(operation, ("", None))
            machine_key = normalize_machine(machine)
            skilled = {e for e, sgs in skill_matrix.items() if skill_group in sgs}
            experienced = {e for e, ms in employee_machines.items() if machine_key in ms}
            rows.append(
                {
                    "Line": line,
                    "Operation": operation,
                    "Machine Type": machine,
                    "Skill Group": skill_group,
                    "Skilled (total)": len(skilled),
                    "Skilled (free)": len(skilled - used),
                    "Machine-experienced (total)": len(experienced),
                    "Machine-experienced (free)": len(experienced - used),
                }
            )
    return pd.DataFrame(rows)
