"""Per-company data isolation.

Every company owns a Postgres schema (`co_<id>`) holding its own lines, styles,
employees, skill matrix, roles and learned skills. Shared tables (companies,
users, auto-created skill groups) live in `public`.

The active company is bound per script run with `use_company`; a pool listener
then points each checked-out connection's `search_path` at that company's
schema. With no company bound, tenant tables simply do not resolve, so a missed
binding fails loudly instead of leaking another company's data.
"""
from __future__ import annotations

from contextvars import ContextVar

from sqlalchemy import event
from sqlalchemy.engine import Engine

_active_company: ContextVar[int | None] = ContextVar("active_company", default=None)


def tenant_schema(company_id: int) -> str:
    """Schema name for a company (int-cast: never interpolates raw input)."""
    return f"co_{int(company_id)}"


def use_company(company_id: int | None) -> None:
    """Binds the company whose data the current script run may touch."""
    _active_company.set(None if company_id is None else int(company_id))


def active_company() -> int | None:
    return _active_company.get()


def search_path_sql() -> str:
    company = _active_company.get()
    return f"SET search_path TO {tenant_schema(company)}, public" if company is not None else "SET search_path TO public"


def install(engine: Engine) -> None:
    """Applies the active company's search_path to every connection handed out."""

    @event.listens_for(engine, "checkout")
    def _bind_search_path(dbapi_connection, _record, _proxy):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(search_path_sql())
        finally:
            cursor.close()
