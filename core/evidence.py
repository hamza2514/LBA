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
