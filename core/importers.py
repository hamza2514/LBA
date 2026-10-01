"""
Flexible import helpers.

This is the piece that turns the tool from "built for one factory's file
format" into "works for any factory's file format" — the single most
important productization step identified early on. Every uploaded file goes
through a column-mapping step: we guess sensible defaults by name
similarity, but the user always confirms/overrides before anything downstream
runs.
"""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st
from rapidfuzz import fuzz


def read_any(uploaded_file) -> pd.DataFrame:
    """Reads an uploaded .xlsx or .csv into a DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def _best_guess(target: str, columns: list[str]) -> str | None:
    if not columns:
        return None
    scored = [(fuzz.token_sort_ratio(target.lower(), c.lower()), c) for c in columns]
    scored.sort(reverse=True)
    best_score, best_col = scored[0]
    return best_col if best_score >= 40 else None


def column_mapper(df: pd.DataFrame, required_fields: dict[str, str], key_prefix: str) -> dict[str, str]:
    """
    Renders a mapping UI: for each required_field -> friendly label, shows a
    selectbox defaulting to the best-guess matching column in df. Returns a
    dict of {required_field: actual_column_name}.
    """
    st.caption("Map this file's columns to what the app needs — every factory's file looks a little different.")
    columns = list(df.columns)
    mapping = {}
    cols = st.columns(min(3, len(required_fields)) or 1)
    for i, (field, label) in enumerate(required_fields.items()):
        guess = _best_guess(label, columns)
        default_idx = columns.index(guess) + 1 if guess in columns else 0
        with cols[i % len(cols)]:
            choice = st.selectbox(
                label,
                options=["(none)"] + columns,
                index=default_idx,
                key=f"{key_prefix}_{field}",
            )
        mapping[field] = None if choice == "(none)" else choice
    return mapping


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Returns a new DataFrame with only the mapped columns, renamed to the
    internal field names."""
    out = pd.DataFrame()
    for field, col in mapping.items():
        out[field] = df[col] if col else None
    return out


def wide_skill_matrix_to_long(df: pd.DataFrame, employee_col: str) -> pd.DataFrame:
    """
    Converts a wide skill matrix (employees as rows, one column per
    operation/skill, any non-empty cell = qualified) into long format:
    one row per (employee, skill_group).
    """
    skill_cols = [c for c in df.columns if c != employee_col]
    records = []
    for _, row in df.iterrows():
        emp = row[employee_col]
        for col in skill_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip() not in ("", "0"):
                records.append({"employee": emp, "skill_group": col})
    return pd.DataFrame(records)
