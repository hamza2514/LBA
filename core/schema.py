"""Database schema: shared tables, per-company tables, and the one-time
migration of a legacy single-company database into the multi-company layout."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from core.tenancy import tenant_schema

SHARED_DDL = (
    """CREATE TABLE IF NOT EXISTS companies (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now()
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS companies_name_ci ON companies (lower(name))",
    """CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMPTZ DEFAULT now()
    )""",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id)",
    # Skill groups are deliberately shared across companies.
    """CREATE TABLE IF NOT EXISTS taxonomy_extra (
        skill_group_id TEXT PRIMARY KEY,
        operation_description TEXT,
        machine_type TEXT,
        sam DOUBLE PRECISION
    )""",
)

TENANT_DDL = (
    "CREATE TABLE IF NOT EXISTS lines (name TEXT PRIMARY KEY)",
    """CREATE TABLE IF NOT EXISTS operation_breakdowns (
        name TEXT PRIMARY KEY,
        shift_time DOUBLE PRECISION NOT NULL,
        target DOUBLE PRECISION NOT NULL,
        plan_efficiency DOUBLE PRECISION NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS ob_rows (
        id SERIAL PRIMARY KEY,
        ob_name TEXT NOT NULL REFERENCES operation_breakdowns(name) ON DELETE CASCADE,
        operation TEXT NOT NULL,
        machine_type TEXT,
        sam DOUBLE PRECISION NOT NULL,
        skill_group TEXT NOT NULL,
        section TEXT NOT NULL DEFAULT ''
    )""",
    "ALTER TABLE ob_rows ADD COLUMN IF NOT EXISTS section TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE ob_rows ADD COLUMN IF NOT EXISTS position INTEGER",
    """CREATE TABLE IF NOT EXISTS learned_skills (
        employee TEXT NOT NULL,
        skill_text TEXT NOT NULL,
        machine_type TEXT NOT NULL DEFAULT '',
        skill_group TEXT NOT NULL,
        times INTEGER NOT NULL DEFAULT 1,
        updated_at TIMESTAMPTZ DEFAULT now(),
        PRIMARY KEY (employee, skill_text, machine_type)
    )""",
    """CREATE TABLE IF NOT EXISTS employees (
        employee_id TEXT PRIMARY KEY,
        employee_name TEXT,
        line TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS skill_matrix (
        id SERIAL PRIMARY KEY,
        employee TEXT NOT NULL,
        skill_text TEXT NOT NULL,
        machine_type TEXT,
        skill_group TEXT NOT NULL,
        UNIQUE (employee, skill_text)
    )""",
    """CREATE TABLE IF NOT EXISTS roles (
        name TEXT PRIMARY KEY,
        machine_types JSONB NOT NULL DEFAULT '[]'
    )""",
    """CREATE TABLE IF NOT EXISTS employee_roles (
        employee TEXT NOT NULL,
        role TEXT NOT NULL REFERENCES roles(name) ON DELETE CASCADE,
        PRIMARY KEY (employee, role)
    )""",
)

TENANT_TABLES = ("lines", "operation_breakdowns", "ob_rows", "learned_skills",
                 "employees", "skill_matrix", "roles", "employee_roles")

LEGACY_COMPANY_NAME = "Default company"
_MIGRATION_LOCK = 7_204_001  # advisory-lock key: serialises concurrent app starts


def ensure_tenant(conn: Connection, company_id: int) -> None:
    """Creates (or upgrades) one company's schema. Idempotent."""
    schema = tenant_schema(company_id)
    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    conn.execute(text(f"SET LOCAL search_path TO {schema}"))
    for statement in TENANT_DDL:
        conn.execute(text(statement))


def migrate_legacy(conn: Connection) -> None:
    """A pre-multi-company database kept its tenant tables in `public`. Moves
    them (data and all) into the schema of a new default company, and attaches
    existing non-admin users to it."""
    if not conn.execute(text("SELECT to_regclass('public.lines') IS NOT NULL")).scalar():
        return
    company_id = conn.execute(
        text("INSERT INTO companies (name) VALUES (:n) ON CONFLICT DO NOTHING RETURNING id"),
        {"n": LEGACY_COMPANY_NAME},
    ).scalar()
    if company_id is None:
        company_id = conn.execute(text("SELECT id FROM companies WHERE lower(name) = lower(:n)"),
                                  {"n": LEGACY_COMPANY_NAME}).scalar()
    schema = tenant_schema(company_id)
    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    for table in TENANT_TABLES:
        if conn.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": f"public.{table}"}).scalar():
            conn.execute(text(f"ALTER TABLE public.{table} SET SCHEMA {schema}"))
    conn.execute(text("UPDATE users SET company_id = :c WHERE role <> 'admin' AND company_id IS NULL"), {"c": company_id})


def initialise(engine) -> None:
    """Brings any database (empty, legacy or current) to the current layout."""
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _MIGRATION_LOCK})
        for statement in SHARED_DDL:
            conn.execute(text(statement))
        migrate_legacy(conn)
        for (company_id,) in conn.execute(text("SELECT id FROM companies ORDER BY id")).fetchall():
            ensure_tenant(conn, company_id)
