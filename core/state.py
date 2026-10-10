"""
Central data-access layer backed by Postgres (core/db.py).

st.session_state is used only for ephemeral per-run UI state (the last
balancing result, manual table edits) — never for anything that should
outlive a single balancing run.
"""
from __future__ import annotations

import streamlit as st

import core.db as db
from core.ui import apply_theme

_EPHEMERAL_KEYS = ("lb_result", "lb_overrides", "ab_result", "ab_overrides", "skill_pairs_preview")


def init_state():
    """Verifies the DB connection (creating/migrating the schema on first run),
    initialises per-session keys and applies the app theme."""
    db.get_engine()
    for key in _EPHEMERAL_KEYS:
        st.session_state.setdefault(key, None)
    apply_theme()


# ------------------------------------------------------------------- Lines
def add_line(name: str):
    db.add_line(name)


def ensure_lines_registered(values: list[str]):
    db.ensure_lines_registered(values)


def list_lines() -> list[str]:
    return db.list_lines()


# --------------------------------------------------------------- Employees
def employee_line_dict() -> dict:
    edf = db.list_employees()
    return {} if edf is None else dict(zip(edf["employee_id"].astype(str), edf["line"].astype(str)))


def employee_names_dict() -> dict:
    edf = db.list_employees()
    return {} if edf is None else dict(zip(edf["employee_id"].astype(str), edf["employee_name"].astype(str)))


# ----------------------------------------------------------- Taxonomy extra
def extra_taxonomy_list() -> list[dict]:
    """Shaped as matching.get_or_create_skill_group expects."""
    return db.list_taxonomy_extra()


def record_taxonomy_extra(new_row: dict):
    db.add_taxonomy_extra(new_row)


def record_taxonomy_extra_bulk(new_rows: list[dict]):
    db.add_taxonomy_extra_bulk(new_rows)


# ------------------------------------------------------------- Roles layer
def list_roles() -> dict:
    """{role_name: [machine_type, ...]} — a Role qualifies an employee for every
    operation on any of its machine types, whatever the operation is called."""
    return db.list_roles()


def save_role(name: str, machine_types: list[str]):
    db.save_role(name, machine_types)


def delete_role(name: str):
    db.delete_role(name)


def employee_roles_dict() -> dict:
    """{employee: [role_name, ...]}"""
    return db.list_employee_roles()


def set_employee_roles(employee: str, role_names: list[str]):
    db.set_employee_roles(employee, role_names)


# --------------------------------------------------------------- Operations
def list_obs() -> list[str]:
    return db.list_obs()


def save_ob(name: str, shift_time: float, target: float, plan_efficiency: float, rows: list[dict]):
    db.save_ob(name, shift_time, target, plan_efficiency, rows)


def get_ob(name: str) -> dict | None:
    return db.get_ob(name)


def delete_ob(name: str):
    db.delete_ob(name)


# ----------------------------------------------------------- Skill matrix
def _resolved_skill_rows(ob_rows: list | None) -> list[tuple[str, str, str]]:
    """[(employee, skill_text, skill_group)] with each entry re-resolved against
    the active OB's own operations first (so identical text always maps to the
    exact skill group the OB uses), falling back to the stored resolution."""
    from core.matching import match_against_rows

    sdf = db.list_skill_pairs()
    if sdf is None:
        return []
    cache: dict = {}
    resolved = []
    for emp, text, stored in zip(sdf["employee"], sdf["skill_text"], sdf["skill_group"]):
        sg = str(stored)
        if ob_rows and isinstance(text, str) and text:
            if text not in cache:
                matched, _ = match_against_rows(text, ob_rows)
                cache[text] = matched or sg
            sg = cache[text]
        resolved.append((str(emp), str(text), sg))
    return resolved


def _role_grants(ob_rows: list | None) -> dict:
    """{employee: {skill_group: role_name}} — skill groups an employee is
    qualified for through a Role (machine-type match) in THIS OB."""
    roles, emp_roles = db.list_roles(), db.list_employee_roles()
    if not (ob_rows and roles and emp_roles):
        return {}
    machine_to_sgs: dict = {}
    for row in ob_rows:
        machine_to_sgs.setdefault(row.get("machine_type"), set()).add(row.get("skill_group"))

    grants: dict = {}
    for emp, role_names in emp_roles.items():
        for role_name in role_names:
            for machine in roles.get(role_name, []):
                for sg in machine_to_sgs.get(machine, ()):
                    grants.setdefault(emp, {}).setdefault(sg, role_name)
    return grants


def skill_matrix_dict(ob_rows: list | None = None) -> dict:
    """{employee: set(skill_group)} from explicit skill-matrix entries plus Roles."""
    out: dict = {}
    for emp, _, sg in _resolved_skill_rows(ob_rows):
        out.setdefault(emp, set()).add(sg)
    for emp, by_sg in _role_grants(ob_rows).items():
        out.setdefault(emp, set()).update(by_sg)
    return out


def employee_skill_profiles(ob_rows: list | None = None) -> dict:
    """{employee: {"by_sg": {skill_group: skill text}, "all": [skill text, ...]}}
    — what each employee is qualified in, in human-readable form (used to show
    the relevant skill next to each candidate in the assignment dropdown)."""
    profiles: dict = {}
    for emp, text, sg in _resolved_skill_rows(ob_rows):
        profile = profiles.setdefault(emp, {"by_sg": {}, "all": []})
        profile["by_sg"].setdefault(sg, text)
        if text not in profile["all"]:
            profile["all"].append(text)
    for emp, by_sg in _role_grants(ob_rows).items():
        profile = profiles.setdefault(emp, {"by_sg": {}, "all": []})
        for sg, role_name in by_sg.items():
            profile["by_sg"].setdefault(sg, f"Role: {role_name}")
        for label in {f"Role: {r}" for r in by_sg.values()}:
            if label not in profile["all"]:
                profile["all"].append(label)
    return profiles
