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


def _looks_like_sno_table(table: list[list]) -> bool:
    """Heuristic for 'Style Bulletin'-style OB reports: real operation rows
    start with a plain integer Sr. No and have enough columns to be a real
    data table (not a 2-column totals scrap or a garbled header block)."""
    if not table or len(table[0] or []) < 5:
        return False
    first_cells = [(row[0] or "").strip() for row in table if row]
    numeric = [c for c in first_cells if c.replace(".", "", 1).isdigit()]
    return len(numeric) >= max(2, len(first_cells) // 2)


def _extract_numbered_operation_rows(pdf) -> pd.DataFrame | None:
    """
    Handles multi-column ERP-style OB reports (e.g. Artistic Milliners'
    Style Bulletin) that have NO header row at all — data starts directly
    at row 1. Column order in these reports, confirmed against a real
    sample: Sr.No, Operation Description, Machine Type, A.S.C.T(sec), SAM,
    Target/Hr, Target/Day, then several repeated manpower-scenario columns
    we don't need (the app derives its own Head Allocated).
    Skips junk tables (garbled summary headers, stray totals).
    """
    rows = []
    for page in pdf.pages:
        for table in page.extract_tables():
            if not _looks_like_sno_table(table):
                continue
            for r in table:
                cell0 = (r[0] or "").strip()
                if not cell0.replace(".", "", 1).isdigit():
                    continue  # skip stray "Sub Total:" / section-header rows mixed into a table
                operation = (r[1] or "").strip() if len(r) > 1 else ""
                machine = (r[2] or "").strip() if len(r) > 2 else ""
                sam = (r[4] or "").strip() if len(r) > 4 else ""
                if not operation:
                    continue
                rows.append({"Sr.No": cell0, "Operation Description": operation, "Machine Type": machine, "SAM": sam})

    if len(rows) < 2:
        return None
    return pd.DataFrame(rows)


def read_pdf_tables(uploaded_file) -> pd.DataFrame:
    """
    Best-effort extraction of tabular data from a PDF Operation Breakdown.
    Tries the position-aware "numbered operation rows" parser first (handles
    real multi-section ERP-style bulletins with no header row), then falls
    back to simple header-based table extraction for plainer bordered-table
    PDFs. Does NOT do OCR — a scanned/image-only PDF will yield nothing.
    """
    import pdfplumber

    with pdfplumber.open(uploaded_file) as pdf:
        structured = _extract_numbered_operation_rows(pdf)
        if structured is not None:
            return structured

        all_rows: list[list] = []
        header: list | None = None
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table:
                    continue
                if header is None:
                    header = table[0]
                    body = table[1:]
                else:
                    body = table[1:] if table[0] == header else table
                all_rows.extend(body)

    if header is None:
        raise ValueError(
            "No tables could be found in this PDF. This only works for text-based "
            "PDFs with real table structure — not scanned/image-only pages."
        )

    df = pd.DataFrame(all_rows, columns=header)
    df = df.dropna(how="all")
    return df


def read_any(uploaded_file) -> pd.DataFrame:
    """Reads an uploaded .xlsx, .csv, or .pdf into a DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith(".pdf"):
        return read_pdf_tables(uploaded_file)
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


def wide_skill_matrix_to_long(df: pd.DataFrame, employee_col: str, exclude_cols: list[str] | None = None) -> pd.DataFrame:
    """
    Converts a wide skill matrix (employees as rows, one column per
    operation/skill, any non-empty cell = qualified) into long format:
    one row per (employee, skill_text). exclude_cols lets the caller drop
    non-skill columns (like Employee Name) that would otherwise be
    misread as bogus skill columns.
    """
    exclude = set(exclude_cols or [])
    skill_cols = [c for c in df.columns if c != employee_col and c not in exclude]
    records = []
    for _, row in df.iterrows():
        emp = row[employee_col]
        for col in skill_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip() not in ("", "0"):
                records.append({"employee": emp, "skill_text": col})
    return pd.DataFrame(records)


def long_skill_file_to_pairs(df: pd.DataFrame, employee_col: str, skill_col: str) -> pd.DataFrame:
    """Already-long skill files (one row per employee-skill pair, e.g.
    Employee_Code + Skill columns) — just rename to the standard shape."""
    out = df[[employee_col, skill_col]].copy()
    out.columns = ["employee", "skill_text"]
    out = out.dropna(subset=["employee", "skill_text"])
    return out
