"""
Central data-access layer, backed by real persistence (core/db.py).

st.session_state is still used for genuinely ephemeral, per-run UI state
(the last balancing result, manual-override selections mid-form) - never
for anything that should outlive a single balancing run.
"""
from __future__ import annotations

import streamlit as st
import core.db as db


def init_state():
    """Verifies the DB connection works (and creates the schema if this is
    the very first run) before any page tries to use it."""
    db.get_engine()
    for k in ("lb_result", "lb_overrides", "ab_result", "ab_overrides", "skill_pairs_preview"):
        if k not in st.session_state:
            st.session_state[k] = None


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
    if edf is None:
        return {}
    return {str(r["employee_id"]): str(r["line"]) for _, r in edf.iterrows()}


def employee_names_dict() -> dict:
    edf = db.list_employees()
    if edf is None:
        return {}
    return {str(r["employee_id"]): str(r["employee_name"]) for _, r in edf.iterrows()}


# ----------------------------------------------------------- Taxonomy extra
def extra_taxonomy_list() -> list[dict]:
    """Shaped exactly like matching.get_or_create_skill_group expects:
    operation_description / machine_type / sam / skill_group_id."""
    return db.list_taxonomy_extra()


def record_taxonomy_extra(new_row: dict):
    db.add_taxonomy_extra(new_row)


def record_taxonomy_extra_bulk(new_rows: list[dict]):
    db.add_taxonomy_extra_bulk(new_rows)


# ------------------------------------------------------------- Roles layer
def list_roles() -> dict:
    """{role_name: [machine_type, ...]} - a Role grants qualification for
    every operation on any of its listed machine types."""
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
def skill_matrix_dict(ob_rows: list | None = None) -> dict:
    """
    {employee: set(skill_group)} - combines THREE sources of qualification:
      1. Explicit skill-matrix entries, re-resolved against the active OB's
         own operations first when ob_rows is given.
      2. Roles: an employee holding a Role qualifies for every OB operation
         whose Machine Type is in that Role's machine-type list.
      3. Inferred from wording (core.inference): near-matches despite
         typos/abbreviations, and compound operations ("A & B") where the
         employee holds every component skill.
    """
    from core.matching import match_against_rows
    from core.inference import infer_qualifications

    sdf = db.list_skill_pairs()
    roles = db.list_roles()
    emp_roles = db.list_employee_roles()

    out: dict = {}

    if sdf is not None:
        cache: dict = {}
        for _, r in sdf.iterrows():
            text = r.get("skill_text")
            stored_sg = str(r["skill_group"])
            sg = stored_sg
            if ob_rows and text:
                if text not in cache:
                    matched_sg, _score = match_against_rows(text, ob_rows)
                    cache[text] = matched_sg or stored_sg
                sg = cache[text]
            out.setdefault(str(r["employee"]), set()).add(sg)

    if ob_rows and roles and emp_roles:
        machine_to_skillgroups: dict = {}
        for row in ob_rows:
            machine_to_skillgroups.setdefault(row.get("machine_type"), set()).add(row.get("skill_group"))

        for emp, role_names in emp_roles.items():
            granted: set = set()
            for role_name in role_names:
                for mt in roles.get(role_name, []):
                    granted |= machine_to_skillgroups.get(mt, set())
            if granted:
                out.setdefault(emp, set()).update(granted)

    if ob_rows and sdf is not None:
        for emp, sgs in infer_qualifications(ob_rows, sdf).items():
            out.setdefault(emp, set()).update(sgs)

    return out
