"""
Real persistence layer (Postgres — Neon, same pattern as the loss-time
tracker). Everything that used to live only in st.session_state and vanish
on reload — Lines, Operation Breakdowns, Employees, Skill Matrix, the
auto-extended taxonomy, and Roles — now lives here and survives across
sessions, deployments, and restarts.

Connection string comes from Streamlit secrets (DATABASE_URL) in
production, falling back to the DATABASE_URL environment variable for
local development/testing.
"""
from __future__ import annotations

import os
import json
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from psycopg2.extras import execute_values

SCHEMA = """
CREATE TABLE IF NOT EXISTS lines (
    name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS operation_breakdowns (
    name TEXT PRIMARY KEY,
    shift_time DOUBLE PRECISION NOT NULL,
    target DOUBLE PRECISION NOT NULL,
    plan_efficiency DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ob_rows (
    id SERIAL PRIMARY KEY,
    ob_name TEXT NOT NULL REFERENCES operation_breakdowns(name) ON DELETE CASCADE,
    operation TEXT NOT NULL,
    machine_type TEXT,
    sam DOUBLE PRECISION NOT NULL,
    skill_group TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    employee_name TEXT,
    line TEXT
);

CREATE TABLE IF NOT EXISTS skill_matrix (
    id SERIAL PRIMARY KEY,
    employee TEXT NOT NULL,
    skill_text TEXT NOT NULL,
    machine_type TEXT,
    skill_group TEXT NOT NULL,
    UNIQUE (employee, skill_text)
);

CREATE TABLE IF NOT EXISTS taxonomy_extra (
    skill_group_id TEXT PRIMARY KEY,
    operation_description TEXT,
    machine_type TEXT,
    sam DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS roles (
    name TEXT PRIMARY KEY,
    machine_types JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS employee_roles (
    employee TEXT NOT NULL,
    role TEXT NOT NULL REFERENCES roles(name) ON DELETE CASCADE,
    PRIMARY KEY (employee, role)
);
"""


@st.cache_resource
def get_engine() -> Engine:
    url = None
    try:
        url = st.secrets.get("DATABASE_URL", None)
    except Exception:
        pass  # no secrets.toml at all (e.g. local dev) — fall through to env var
    if not url:
        url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "No DATABASE_URL found. Set it in Streamlit secrets (production) "
            "or as an environment variable (local development)."
        )
    # force the psycopg2 driver explicitly — SQLAlchemy 2.x may otherwise
    # prefer a different driver depending on what's installed, and a plain
    # Neon connection string (postgresql://...) doesn't specify one
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        for stmt in SCHEMA.strip().split(";\n\n"):
            if stmt.strip():
                conn.execute(text(stmt))
    return engine


# ---------------------------------------------------------------------- Lines
def list_lines() -> list[str]:
    with get_engine().connect() as conn:
        return [r[0] for r in conn.execute(text("SELECT name FROM lines ORDER BY name"))]


def add_line(name: str):
    name = name.strip()
    if not name:
        return
    with get_engine().begin() as conn:
        conn.execute(text("INSERT INTO lines (name) VALUES (:n) ON CONFLICT DO NOTHING"), {"n": name})


def delete_line(name: str):
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM lines WHERE name = :n"), {"n": name})


def ensure_lines_registered(values: list[str]):
    for v in values:
        add_line(str(v))


# ------------------------------------------------------- Operation Breakdowns
def list_obs() -> list[str]:
    with get_engine().connect() as conn:
        return [r[0] for r in conn.execute(text("SELECT name FROM operation_breakdowns ORDER BY name"))]


def save_ob(name: str, shift_time: float, target: float, plan_efficiency: float, rows: list[dict]):
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO operation_breakdowns (name, shift_time, target, plan_efficiency) "
                "VALUES (:name, :st, :tg, :eff) "
                "ON CONFLICT (name) DO UPDATE SET shift_time=:st, target=:tg, plan_efficiency=:eff"
            ),
            {"name": name, "st": shift_time, "tg": target, "eff": plan_efficiency},
        )
        conn.execute(text("DELETE FROM ob_rows WHERE ob_name = :name"), {"name": name})

    if rows:
        raw = get_engine().raw_connection()
        try:
            cur = raw.cursor()
            values = [(name, r["operation"], r.get("machine_type"), r["sam"], r["skill_group"]) for r in rows]
            execute_values(
                cur,
                "INSERT INTO ob_rows (ob_name, operation, machine_type, sam, skill_group) VALUES %s",
                values,
                page_size=500,
            )
            raw.commit()
        finally:
            raw.close()


def get_ob(name: str) -> dict | None:
    with get_engine().connect() as conn:
        meta = conn.execute(
            text("SELECT shift_time, target, plan_efficiency FROM operation_breakdowns WHERE name = :n"),
            {"n": name},
        ).fetchone()
        if not meta:
            return None
        rows = conn.execute(
            text("SELECT operation, machine_type, sam, skill_group FROM ob_rows WHERE ob_name = :n ORDER BY id"),
            {"n": name},
        ).fetchall()
    return {
        "shift_time": meta[0],
        "target": meta[1],
        "plan_efficiency": meta[2],
        "rows": [{"operation": r[0], "machine_type": r[1], "sam": r[2], "skill_group": r[3]} for r in rows],
    }


def delete_ob(name: str):
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM operation_breakdowns WHERE name = :n"), {"n": name})


# ------------------------------------------------------------------ Employees
def list_employees():
    import pandas as pd
    with get_engine().connect() as conn:
        rows = conn.execute(text("SELECT employee_id, employee_name, line FROM employees ORDER BY employee_id")).fetchall()
    return pd.DataFrame(rows, columns=["employee_id", "employee_name", "line"]) if rows else None


def upsert_employees(df):
    if df.empty:
        return
    raw = get_engine().raw_connection()
    try:
        cur = raw.cursor()
        values = [(str(r["employee_id"]), r["employee_name"], str(r["line"])) for _, r in df.iterrows()]
        execute_values(
            cur,
            "INSERT INTO employees (employee_id, employee_name, line) VALUES %s "
            "ON CONFLICT (employee_id) DO UPDATE SET employee_name = EXCLUDED.employee_name, line = EXCLUDED.line",
            values,
            page_size=500,
        )
        raw.commit()
    finally:
        raw.close()


# --------------------------------------------------------------- Skill Matrix
def list_skill_pairs():
    import pandas as pd
    with get_engine().connect() as conn:
        rows = conn.execute(text("SELECT employee, skill_text, machine_type, skill_group FROM skill_matrix")).fetchall()
    return pd.DataFrame(rows, columns=["employee", "skill_text", "machine_type", "skill_group"]) if rows else None


def add_skill_pairs(df):
    """
    Bulk upsert via execute_values — ONE network round trip per ~500 rows
    instead of one per row. This is the single biggest speed fix: a skill
    matrix with hundreds of employees x several skills each can easily be
    1,000+ pairs, and the old row-by-row loop meant 1,000+ individual
    round trips to the (remote, Neon) database — easily minutes of wall
    time even though each statement itself is fast.
    """
    if df.empty:
        return
    raw = get_engine().raw_connection()
    try:
        cur = raw.cursor()
        values = [
            (r["employee"], r["skill_text"], r.get("machine_type"), r["skill_group"])
            for _, r in df.iterrows()
        ]
        execute_values(
            cur,
            "INSERT INTO skill_matrix (employee, skill_text, machine_type, skill_group) VALUES %s "
            "ON CONFLICT (employee, skill_text) DO UPDATE SET "
            "machine_type = EXCLUDED.machine_type, skill_group = EXCLUDED.skill_group",
            values,
            page_size=500,
        )
        raw.commit()
    finally:
        raw.close()


def clear_skill_matrix():
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM skill_matrix"))


# ------------------------------------------------------------- Taxonomy Extra
def list_taxonomy_extra() -> list[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT skill_group_id, operation_description, machine_type, sam FROM taxonomy_extra")
        ).fetchall()
    return [
        {"skill_group_id": r[0], "operation_description": r[1], "machine_type": r[2], "sam": r[3]}
        for r in rows
    ]


def add_taxonomy_extra_bulk(new_rows: list[dict]):
    """Same fix as add_skill_pairs — batch newly auto-created skill groups
    into one round trip instead of one insert per new group found during
    an import."""
    if not new_rows:
        return
    raw = get_engine().raw_connection()
    try:
        cur = raw.cursor()
        values = [
            (r["skill_group_id"], r["operation_description"], r.get("machine_type"), r.get("sam"))
            for r in new_rows
        ]
        execute_values(
            cur,
            "INSERT INTO taxonomy_extra (skill_group_id, operation_description, machine_type, sam) "
            "VALUES %s ON CONFLICT DO NOTHING",
            values,
            page_size=500,
        )
        raw.commit()
    finally:
        raw.close()


def add_taxonomy_extra(new_row: dict):
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO taxonomy_extra (skill_group_id, operation_description, machine_type, sam) "
                "VALUES (:sg, :desc, :mt, :sam) ON CONFLICT DO NOTHING"
            ),
            {
                "sg": new_row["skill_group_id"],
                "desc": new_row["operation_description"],
                "mt": new_row.get("machine_type"),
                "sam": new_row.get("sam"),
            },
        )


# ------------------------------------------------------------------- Roles
def list_roles() -> dict:
    """{role_name: [machine_type, ...]}"""
    with get_engine().connect() as conn:
        rows = conn.execute(text("SELECT name, machine_types FROM roles ORDER BY name")).fetchall()
    out = {}
    for name, mts in rows:
        out[name] = mts if isinstance(mts, list) else json.loads(mts)
    return out


def save_role(name: str, machine_types: list[str]):
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO roles (name, machine_types) VALUES (:n, :mt) "
                "ON CONFLICT (name) DO UPDATE SET machine_types = :mt"
            ),
            {"n": name, "mt": json.dumps(machine_types)},
        )


def delete_role(name: str):
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM roles WHERE name = :n"), {"n": name})


def list_employee_roles() -> dict:
    """{employee: [role_name, ...]}"""
    with get_engine().connect() as conn:
        rows = conn.execute(text("SELECT employee, role FROM employee_roles")).fetchall()
    out: dict = {}
    for emp, role in rows:
        out.setdefault(emp, []).append(role)
    return out


def set_employee_roles(employee: str, role_names: list[str]):
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM employee_roles WHERE employee = :e"), {"e": employee})
        for role in role_names:
            conn.execute(
                text("INSERT INTO employee_roles (employee, role) VALUES (:e, :r) ON CONFLICT DO NOTHING"),
                {"e": employee, "r": role},
            )
