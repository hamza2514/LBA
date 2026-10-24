"""
Learning from what the user does on the result table.

Pure functions (no I/O). The caller persists what they return:
  - learned_qualifications(): every manual employee choice becomes a learned
    skill (employee + operation wording + machine + skill group). Because it
    joins the skill vocabulary, it also generalises to similarly worded
    operations through the normal wording inference.
  - operation_order(): the sequence the user arranged the rows in, as OB row
    ids, so the Operation Breakdown itself adopts that order.
"""
from __future__ import annotations

from core.results import ResultRow


def learned_qualifications(rows: list[ResultRow], assign: dict[str, str]) -> list[dict]:
    """Manual choices only: rows whose employee differs from the system's."""
    return [
        {
            "employee": assign[r.id],
            "skill_text": r.operation,
            "machine_type": r.machine_type,
            "skill_group": r.skill_group,
        }
        for r in rows
        if assign.get(r.id) and assign[r.id] != r.system_employee
    ]


def operation_order(rows: list[ResultRow], order: list[str], ob_row_ids: list[int]) -> list[int]:
    """OB row ids in the user's arranged sequence (first appearance of each
    operation wins; operations not shown keep their place at the end)."""
    seq_of = {r.id: r.seq for r in rows}
    seqs: list[int] = []
    for row_id in order:
        seq = seq_of.get(row_id)
        if seq is not None and seq not in seqs and 0 <= seq < len(ob_row_ids):
            seqs.append(seq)
    seqs += [s for s in range(len(ob_row_ids)) if s not in seqs]
    return [ob_row_ids[s] for s in seqs]
