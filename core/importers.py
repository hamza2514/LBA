"""
Flexible import helpers.

Every uploaded file goes through a column-mapping step: defaults are guessed
by name similarity and the user always confirms/overrides before anything
downstream runs.

Operation Breakdown files (Excel/xlsm/CSV/PDF) are additionally parsed for
LINE SECTIONS (Small Parts, Back, Front, Assembly, Dispatch, Pocket Setter,
...). Section header rows are detected, consumed, and turned into a
"Section" column on the operation rows that follow them — in original OB order.
"""
from __future__ import annotations

import re

import pandas as pd
import streamlit as st
from rapidfuzz import fuzz

from core.sections import canonical_section, looks_like_section_label

_SAM_HEADER = re.compile(r"(?:^|[^a-z])(?:sam|smv|s\.a\.m)(?:[^a-z]|$)")
_END_MARKERS = ("grand total", "verified by")
_HEADER_SCAN_ROWS = 40


# ---------------------------------------------------------------- cell helpers
def _cell(value) -> str:
    return "" if value is None or (not isinstance(value, str) and pd.isna(value)) else str(value).strip()


def _norm(value) -> str:
    return re.sub(r"\s+", " ", _cell(value)).lower()


def _to_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(number) else number


def _is_text(value) -> bool:
    text = _cell(value)
    return bool(text) and _to_float(text) is None


# ----------------------------------------------------- header / section parsing
def _is_operation_header(text: str) -> bool:
    return "operation" in text or text == "description"


def _is_sam_header(text: str) -> bool:
    return bool(_SAM_HEADER.search(text)) or "smv" in text


def _find_header_row(grid: pd.DataFrame) -> int | None:
    for i in range(min(_HEADER_SCAN_ROWS, len(grid))):
        cells = [_norm(v) for v in grid.iloc[i]]
        if any(_is_operation_header(c) for c in cells) and any(_is_sam_header(c) for c in cells):
            return i
    return None


def _clean_headers(cells) -> list[str]:
    seen: dict[str, int] = {}
    headers = []
    for i, cell in enumerate(cells):
        name = re.sub(r"\s+", " ", _cell(cell)) or f"Column {i + 1}"
        seen[name] = seen.get(name, 0) + 1
        headers.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return headers


def _pick_header(headers: list[str], predicate) -> str | None:
    return next((h for h in headers if predicate(h.lower())), None)


def _truncate_at_end_marker(body: pd.DataFrame) -> pd.DataFrame:
    for i, row in enumerate(body.itertuples(index=False)):
        if any(m in _norm(v) for v in row for m in _END_MARKERS):
            return body.iloc[:i]
    return body


def _extract_sections(body: pd.DataFrame) -> pd.DataFrame:
    headers = list(body.columns)
    op_col = (
        _pick_header(headers, lambda h: h == "operation")
        or _pick_header(headers, lambda h: "operation" in h)
        or _pick_header(headers, lambda h: "description" in h)
    )
    sam_col = _pick_header(headers, _is_sam_header)
    mt_col = _pick_header(headers, lambda h: "machine" in h or "m/c" in h or "mc type" in h)

    kept, sections, current = [], [], ""
    for _, row in body.iterrows():
        values = list(row)
        if not any(_cell(v) for v in values):
            continue
        texts = [_cell(v) for v in values if _is_text(v)]
        if any("total" in t.lower() for t in texts):
            continue  # sub-total / grand-total rows
        is_header_row = _to_float(row[sam_col]) is None and not (mt_col and _cell(row[mt_col]))
        if is_header_row:
            label = _cell(row[op_col]) if op_col else ""
            label = label or next((t for t in texts), "")
            if label:
                current = canonical_section(label)
            continue
        kept.append(row)
        sections.append(current)

    result = pd.DataFrame(kept).reset_index(drop=True)
    if any(sections):
        name = "Section" if "Section" not in result.columns else "Detected Section"
        result.insert(0, name, sections)
    return result


def _frame_from_grid(grid: pd.DataFrame) -> pd.DataFrame | None:
    """Raw cell grid -> operation DataFrame (header located, sections extracted)."""
    header_row = _find_header_row(grid)
    if header_row is None:
        return None
    body = grid.iloc[header_row + 1:].reset_index(drop=True)
    body.columns = _clean_headers(grid.iloc[header_row])
    return _extract_sections(_truncate_at_end_marker(body))


# ------------------------------------------------------------------------ PDF
def _looks_like_sno_table(table: list[list]) -> bool:
    """Real operation rows start with a plain integer Sr. No and have enough
    columns to be a data table (not a totals scrap or a header block)."""
    if not table or len(table[0] or []) < 5:
        return False
    first_cells = [(row[0] or "").strip() for row in table if row]
    numeric = [c for c in first_cells if c.replace(".", "", 1).isdigit()]
    return len(numeric) >= max(2, len(first_cells) // 2)


def _page_section_labels(page) -> list[tuple[float, str]]:
    """(vertical position, canonical section) for every section caption on the page."""
    try:
        lines = page.extract_text_lines()
    except AttributeError:  # older pdfplumber: degrade to "no sections"
        return []
    return [
        (line["top"], canonical_section(line["text"]))
        for line in lines
        if len(line["text"]) <= 45 and looks_like_section_label(line["text"])
    ]


def _table_to_records(table: list[list], section: str) -> list[dict]:
    records = []
    for r in table:
        cell0 = (r[0] or "").strip()
        if not cell0.replace(".", "", 1).isdigit():
            continue  # stray "Sub Total:" / header rows mixed into a table
        operation = re.sub(r"\s+", " ", (r[1] or "")).strip() if len(r) > 1 else ""
        if not operation:
            continue
        records.append({
            "Sr.No": cell0,
            "Operation Description": operation,
            "Machine Type": (r[2] or "").strip() if len(r) > 2 else "",
            "SAM": (r[4] or "").strip() if len(r) > 4 else "",
            "Section": section,
        })
    return records


def _extract_numbered_operation_rows(pdf) -> pd.DataFrame | None:
    """
    Multi-column ERP-style OB reports (e.g. Style Bulletin) with NO header row:
    Sr.No, Operation, Machine Type, A.S.C.T, SAM, ... Section captions
    ("FRONT SECTION") sit above each table; the last caption seen (even from a
    previous page) applies to the tables that follow it.
    """
    records: list[dict] = []
    current = ""
    for page in pdf.pages:
        events = [(top, "label", name) for top, name in _page_section_labels(page)]
        events += [(t.bbox[1], "table", t) for t in page.find_tables()]
        for _, kind, payload in sorted(events, key=lambda e: e[0]):
            if kind == "label":
                current = payload
                continue
            table = payload.extract()
            if _looks_like_sno_table(table):
                records.extend(_table_to_records(table, current))

    if len(records) < 2:
        return None
    frame = pd.DataFrame(records)
    return frame if frame["Section"].any() else frame.drop(columns="Section")


def read_pdf_tables(uploaded_file) -> pd.DataFrame:
    """
    Best-effort extraction of an Operation Breakdown from a text-based PDF.
    Tries the position-aware numbered-row parser first, then falls back to
    plain header-based table extraction. No OCR.
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
                    header, body = table[0], table[1:]
                else:
                    body = table[1:] if table[0] == header else table
                all_rows.extend(body)

    if header is None:
        raise ValueError(
            "No tables could be found in this PDF. This only works for text-based "
            "PDFs with real table structure — not scanned/image-only pages."
        )
    return pd.DataFrame(all_rows, columns=header).dropna(how="all")


# ------------------------------------------------------------------ public API
def read_any(uploaded_file) -> pd.DataFrame:
    """Reads an uploaded .xlsx/.xlsm, .csv, or .pdf into a plain DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith(".pdf"):
        return read_pdf_tables(uploaded_file)
    return pd.read_excel(uploaded_file)


def read_ob_file(uploaded_file) -> pd.DataFrame:
    """
    Reads an Operation Breakdown of any supported type. For Excel/CSV the
    header row is located automatically (title blocks above it are skipped),
    the right sheet is chosen in multi-sheet workbooks, and line sections are
    extracted into a "Section" column.
    """
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return read_pdf_tables(uploaded_file)

    if name.endswith(".csv"):
        grids = {"csv": pd.read_csv(uploaded_file, header=None, dtype=object)}
    else:
        grids = pd.read_excel(uploaded_file, sheet_name=None, header=None)

    best: pd.DataFrame | None = None
    for grid in grids.values():
        frame = _frame_from_grid(grid)
        if frame is not None and (best is None or len(frame) > len(best)):
            best = frame
    if best is not None and not best.empty:
        return best

    uploaded_file.seek(0)  # no recognisable header: plain first-sheet read
    return read_any(uploaded_file)


def _best_guess(target: str, columns: list[str]) -> str | None:
    if not columns:
        return None
    scored = sorted(((fuzz.token_sort_ratio(target.lower(), c.lower()), c) for c in columns), reverse=True)
    best_score, best_col = scored[0]
    return best_col if best_score >= 40 else None


def column_mapper(df: pd.DataFrame, required_fields: dict[str, str], key_prefix: str) -> dict[str, str]:
    """Mapping UI: one selectbox per field, defaulting to the best-guess column."""
    st.caption("Map this file's columns to what the app needs — every factory's file looks a little different.")
    columns = [str(c) for c in df.columns]
    mapping = {}
    cols = st.columns(min(4, len(required_fields)) or 1)
    for i, (field, label) in enumerate(required_fields.items()):
        guess = _best_guess(label, columns)
        default_idx = columns.index(guess) + 1 if guess in columns else 0
        with cols[i % len(cols)]:
            choice = st.selectbox(label, options=["(none)"] + columns, index=default_idx, key=f"{key_prefix}_{field}")
        mapping[field] = None if choice == "(none)" else choice
    return mapping


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """New DataFrame with only the mapped columns, renamed to internal field names."""
    out = pd.DataFrame(index=df.index)
    for field, col in mapping.items():
        out[field] = df[col] if col else None
    return out


def wide_skill_matrix_to_long(df: pd.DataFrame, employee_col: str, exclude_cols: list[str] | None = None) -> pd.DataFrame:
    """Wide skill matrix (one column per skill, any non-empty cell = qualified)
    -> long format: one row per (employee, skill_text)."""
    exclude = set(exclude_cols or [])
    skill_cols = [c for c in df.columns if c != employee_col and c not in exclude]
    records = []
    for _, row in df.iterrows():
        for col in skill_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip() not in ("", "0"):
                records.append({"employee": row[employee_col], "skill_text": col})
    return pd.DataFrame(records)


def long_skill_file_to_pairs(df: pd.DataFrame, employee_col: str, skill_col: str) -> pd.DataFrame:
    """Already-long skill files — rename to the standard shape."""
    out = df[[employee_col, skill_col]].copy()
    out.columns = ["employee", "skill_text"]
    return out.dropna(subset=["employee", "skill_text"])
