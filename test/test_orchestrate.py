import pandas as pd

from core.evidence import diagnose_unstaffed
from core.inference import infer_weak_evidence
from core.orchestrate import run_multi_line, run_single_line
from core.results import build_rows, effective_records, reconcile
from core.staffing import StaffingEvidence, normalize_machine

OB = [
    {"operation": "A OP", "machine_type": "SNLS", "sam": 1.0, "skill_group": "SG-A", "section": "Back"},
    {"operation": "B OP", "machine_type": "SNLS", "sam": 1.0, "skill_group": "SG-B", "section": "Back"},
    {"operation": "C OP", "machine_type": "3T O/L", "sam": 1.0, "skill_group": "SG-C", "section": "Front"},
]


def _evidence():
    return StaffingEvidence(
        strong={"SG-A": {"E1"}, "SG-B": {"E1", "E2"}},
        machines={"E3": {normalize_machine("3TO/L")}},
    )


def test_scarce_employee_is_not_consumed_by_flexible_work():
    # E1 is the only holder of SG-A; SG-B also accepts E2. Both must be staffed.
    _, units = run_single_line("L1", OB, 480, 480, 1.0, _evidence(), {})
    staffed = {op.operation: u.employee for u in units for op in u.operations}
    assert staffed["A OP"] == "E1" and staffed["B OP"] == "E2"


def test_machine_fallback_staffs_unlisted_operation():
    _, units = run_single_line("L1", OB, 480, 480, 1.0, _evidence(), {})
    unit = next(u for u in units if u.operations[0].operation == "C OP")
    assert (unit.employee, unit.basis) == ("E3", "Machine type")


def test_every_head_is_a_separate_named_row_and_basis_reaches_the_table():
    _, units = run_single_line("L1", OB[:1], 480, 960, 1.0, _evidence(), {})
    rows = build_rows(units, ["L1"], lambda sg, line, machine: [])
    order, assign = reconcile(rows, None)
    records = effective_records(rows, order, assign, {})
    assert len(records) == 2 and records[0]["Assigned By"] == "Skill"
    assert records[1]["Employee Code"] == ""  # second head: nobody left
    assert len(diagnose_unstaffed(units, _evidence())) == 1


def test_multi_line_uses_each_person_once():
    _, units = run_multi_line(["L1", "L2"], {"L1": OB, "L2": OB}, 480, 480, 1.0, _evidence(), {})
    people = [u.employee for u in units if u.employee]
    assert len(people) == len(set(people))
