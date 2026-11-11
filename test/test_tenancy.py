"""Company isolation, run against a real Postgres (skipped when none is configured).
    DATABASE_URL=postgresql://user:pw@localhost/lb_test pytest test/test_tenancy.py
"""
import os

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="needs DATABASE_URL (Postgres)")


@pytest.fixture()
def db_module():
    import core.db as db
    engine = db.get_engine()
    with engine.begin() as conn:
        for (cid,) in conn.execute(text("SELECT id FROM companies")).fetchall():
            conn.execute(text(f"DROP SCHEMA IF EXISTS co_{cid} CASCADE"))
        conn.execute(text("DELETE FROM users"))
        conn.execute(text("DELETE FROM companies"))
    db.use_company(None)
    yield db
    db.use_company(None)


def test_each_company_only_sees_its_own_data(db_module):
    db = db_module
    a, b = db.create_company("Alpha Apparel"), db.create_company("Beta Denim")
    db.use_company(a)
    db.add_line("A-L1")
    db.save_ob("A-style", 480, 1000, 0.85, [{"operation": "Hem", "machine_type": "SNLS", "sam": 1.0, "skill_group": "SG-1"}])
    db.add_learned([{"employee": "E1", "skill_text": "Hem", "machine_type": "SNLS", "skill_group": "SG-1"}])
    db.use_company(b)
    assert db.list_lines() == [] and db.list_obs() == [] and db.list_learned() is None
    db.add_line("B-L1")
    db.use_company(a)
    assert db.list_lines() == ["A-L1"] and db.list_obs() == ["A-style"]


def test_skill_groups_are_shared_between_companies(db_module):
    db = db_module
    a, b = db.create_company("Alpha"), db.create_company("Beta")
    db.use_company(a)
    db.add_taxonomy_extra({"skill_group_id": "SG-AUTO-0001", "operation_description": "x", "machine_type": "SNLS", "sam": 1})
    db.use_company(b)
    assert [r["skill_group_id"] for r in db.list_taxonomy_extra()] == ["SG-AUTO-0001"]


def test_no_company_bound_fails_instead_of_leaking(db_module):
    db_module.create_company("Alpha")
    db_module.use_company(None)
    with pytest.raises(Exception, match="lines"):
        db_module.list_lines()


def test_company_names_are_unique_ignoring_case(db_module):
    db_module.create_company("Alpha")
    with pytest.raises(ValueError):
        db_module.create_company("  alpha ")


def test_users_belong_to_a_company(db_module):
    from core import auth
    db = db_module
    cid = db.create_company("Alpha")
    auth.create_user("Sara", "longenough1", "Sara K", "user", cid)
    user = auth.authenticate("sara", "longenough1")
    assert user["company_id"] == cid and user["company_name"] == "Alpha"
    with pytest.raises(ValueError):
        auth.create_user("orphan", "longenough1", "", "user", None)
    auth.create_user("root", "longenough1", "", "admin", cid)  # admins never belong to a company
    assert auth.authenticate("root", "longenough1")["company_id"] is None


def test_legacy_single_company_database_is_migrated_with_its_data():
    from core import schema, tenancy
    url = os.environ["DATABASE_URL"].rsplit("/", 1)[0].replace("postgresql://", "postgresql+psycopg2://") + "/lb_legacy"
    engine = create_engine(url)
    with engine.begin() as conn:
        for (leftover,) in conn.execute(text("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'co\\_%'")).fetchall():
            conn.execute(text(f"DROP SCHEMA {leftover} CASCADE"))
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
        conn.execute(text("CREATE TABLE lines (name TEXT PRIMARY KEY)"))
        conn.execute(text("INSERT INTO lines VALUES ('Old-L1')"))
        conn.execute(text("CREATE TABLE users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, "
                          "full_name TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'user', created_at TIMESTAMPTZ DEFAULT now())"))
        conn.execute(text("INSERT INTO users (username, password_hash, role) VALUES ('boss','x','admin'),('planner','x','user')"))
    from core import db
    migrated = db.build_engine(url)
    with migrated.connect() as conn:
        company = conn.execute(text("SELECT id FROM companies WHERE name = :n"), {"n": schema.LEGACY_COMPANY_NAME}).scalar()
        schema_name = tenancy.tenant_schema(company)
        assert conn.execute(text(f"SELECT name FROM {schema_name}.lines")).scalar() == "Old-L1"
        assert conn.execute(text("SELECT to_regclass('public.lines') IS NULL")).scalar()
        rows = dict(conn.execute(text("SELECT username, company_id FROM users")).fetchall())
        assert rows == {"boss": None, "planner": company}
        assert conn.execute(text(f"SELECT to_regclass('{schema_name}.ob_rows') IS NOT NULL")).scalar()
    db.build_engine(url)  # running the migration again changes nothing
