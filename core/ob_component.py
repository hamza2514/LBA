"""Python bridge to the Operation Breakdown drag-to-reorder table component."""
from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).resolve().parent.parent / "components" / "ob_table"
_component = components.declare_component("ob_table", path=str(_COMPONENT_DIR))


def ob_table(*, key: str, columns: list[dict], rows: list[dict], order: list[int]):
    """Returns None until the user drops a row, then {"order": [row ids]}."""
    return _component(columns=columns, rows=rows, order=order, key=key, default=None)
