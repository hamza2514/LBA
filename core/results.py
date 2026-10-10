"""
Result-table model: turns balancing output (AssignedUnits) into flat,
sequence-ordered rows, and applies the user's live edits (row order,
per-row employee choice) on top.

Colour rule: rows whose effective employee is the same person share a colour,
so merged operations stay visible — automatic merges and manual ones alike.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

PALETTE = [
    "#D9EAD3", "#CFE2F3", "#FFF2CC", "#F4CCCC", "#E1D5F0",
    "#D0E0E3", "#FCE5CD", "#EAD1DC", "#D9D2E9", "#C9DAF8",
]
SYSTEM, MANUAL = "System", "Manual"


@dataclass
class RunResult:
    units: list
    line_order: list[str]


@dataclass(frozen=True)
class ResultRow:
    id: str
    line: str
    seq: int
    operation: str
    machine_type: str
    sam: float
    skill_group: str
    target: float
    system_employee: str
    suggestions: tuple[str, ...] = field(default_factory=tuple)


def build_rows(
    units: list,
    line_order: list[str],
    suggest: Callable[[str, str], list[str]],
) -> list[ResultRow]:
    """One row per operation assignment, ordered line by line in OB sequence.
    suggest(skill_group, line) -> ordered candidate employee codes."""
    counters: dict[tuple, int] = {}
    rows = []
    for unit in units:
        for op in unit.operations:
            n = counters[(op.line, op.seq)] = counters.get((op.line, op.seq), 0) + 1
            rows.append(
                ResultRow(
                    id=f"{op.line}::{op.seq}::{n}",
                    line=op.line, seq=op.seq, operation=op.operation,
                    machine_type=op.machine_type or "", sam=op.sam,
                    skill_group=op.skill_group, target=op.target,
                    system_employee=unit.employee or "",
                    suggestions=tuple(suggest(op.skill_group, op.line)),
                )
            )
    line_rank = {line: i for i, line in enumerate(line_order)}
    rows.sort(key=lambda r: (line_rank.get(r.line, len(line_rank)), r.seq, r.id))
    return rows


def reconcile(rows: list[ResultRow], state: dict | None) -> tuple[list[str], dict[str, str]]:
    """Validates saved table state against the current rows: unknown ids are
    dropped, new ids are appended; returns (order, assignments)."""
    ids = [r.id for r in rows]
    known = set(ids)
    saved_order = [i for i in (state or {}).get("order", []) if i in known]
    order = saved_order + [i for i in ids if i not in set(saved_order)]
    saved_assign = {k: v for k, v in ((state or {}).get("assign") or {}).items() if k in known}
    assign = {r.id: saved_assign.get(r.id, r.system_employee) for r in rows}
    return order, assign


def assign_colors(codes: list[str]) -> dict[str, str]:
    """Colour per employee appearing on 2+ rows, in order of first appearance."""
    counts: dict[str, int] = {}
    for code in codes:
        if code:
            counts[code] = counts.get(code, 0) + 1
    colors: dict[str, str] = {}
    for code in codes:
        if code and counts[code] > 1 and code not in colors:
            colors[code] = PALETTE[len(colors) % len(PALETTE)]
    return colors


def effective_records(
    rows: list[ResultRow], order: list[str], assign: dict[str, str], names: dict[str, str]
) -> list[dict]:
    """Final table rows in the user's order, with employee name, who assigned
    them (System/Manual) and the merge colour."""
    by_id = {r.id: r for r in rows}
    ordered = [by_id[i] for i in order]
    colors = assign_colors([assign[r.id] for r in ordered])
    records = []
    for r in ordered:
        code = assign[r.id]
        records.append({
            "Line": r.line,
            "Operation": r.operation,
            "Machine Type": r.machine_type,
            "SAM": round(r.sam, 4),
            "Employee Code": code,
            "Employee Name": names.get(code, "") if code else "",
            "Target": round(r.target),
            "Assigned By": SYSTEM if code == r.system_employee else MANUAL,
            "_color": colors.get(code),
        })
    return records


def summarize(records: list[dict]) -> dict[str, int]:
    codes = [r["Employee Code"] for r in records if r["Employee Code"]]
    return {
        "rows": len(records),
        "unassigned": sum(1 for r in records if not r["Employee Code"]),
        "operators": len(set(codes)),
        "merged": sum(1 for c in set(codes) if codes.count(c) > 1),
        "manual": sum(1 for r in records if r["Assigned By"] == MANUAL),
    }


def employee_payload(employees_df, profiles: dict, needed_sgs: set, pool: set | None) -> dict:
    """{code: {name, line, by_sg, all}} for the dropdown — only skill groups
    present in the result are sent, keeping the payload small."""
    payload = {}
    for _, e in employees_df.iterrows():
        code = str(e["employee_id"])
        if pool is not None and code not in pool:
            continue
        profile = profiles.get(code, {"by_sg": {}, "all": []})
        payload[code] = {
            "name": str(e["employee_name"] or ""),
            "line": str(e["line"] or ""),
            "by_sg": {sg: t for sg, t in profile["by_sg"].items() if sg in needed_sgs},
            "all": profile["all"][:8],
            "more": max(0, len(profile["all"]) - 8),
        }
    return payload
