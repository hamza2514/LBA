"""Python bridge to the results-table frontend component (no build step)."""
from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).resolve().parent.parent / "components" / "results_table"
_component = components.declare_component("results_table", path=str(_COMPONENT_DIR))


def results_table(*, key: str, rows: list[dict], order: list[str], assign: dict, employees: dict, palette: list[str]):
    """Renders the editable result table. Returns None until the user edits,
    then {"order": [...], "assign": {row_id: employee_code}}."""
    return _component(
        rows=rows, order=order, assign=assign, employees=employees, palette=palette,
        key=key, default=None,
    )
