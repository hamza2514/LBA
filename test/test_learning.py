from core.learning import learned_qualifications, operation_order
from core.results import ResultRow


def _row(i, seq, system="E1"):
    return ResultRow(id=f"L1::{seq}::1", line="L1", seq=seq, operation=f"OP{seq}", machine_type="SNLS",
                     sam=1.0, skill_group=f"SG{seq}", target=100, system_employee=system)


def test_only_manual_changes_are_learned():
    rows = [_row(0, 0), _row(1, 1)]
    learned = learned_qualifications(rows, {"L1::0::1": "E1", "L1::1::1": "E9"})
    assert learned == [{"employee": "E9", "skill_text": "OP1", "machine_type": "SNLS", "skill_group": "SG1"}]


def test_clearing_an_assignment_learns_nothing():
    assert learned_qualifications([_row(0, 0)], {"L1::0::1": ""}) == []


def test_operation_order_follows_the_arranged_rows():
    rows = [_row(0, 0), _row(1, 1), _row(2, 2)]
    ids = [101, 102, 103]
    assert operation_order(rows, ["L1::2::1", "L1::0::1", "L1::1::1"], {"L1": ids}) == [103, 101, 102]


def test_missing_operations_keep_their_place_at_the_end():
    rows = [_row(0, 0), _row(1, 1), _row(2, 2)]
    assert operation_order(rows, ["L1::1::1"], {"L1": [101, 102, 103]}) == [102, 101, 103]


def test_each_lines_own_style_is_ordered_separately():
    rows = [_row(0, 0), _row(1, 1)]
    rows += [ResultRow(id=f"L2::{s}::1", line="L2", seq=s, operation=f"Q{s}", machine_type="SNLS", sam=1.0,
                       skill_group=f"G{s}", target=1, system_employee="E1") for s in (0, 1)]
    order = ["L1::1::1", "L1::0::1", "L2::0::1", "L2::1::1"]
    assert operation_order(rows, order, {"L1": [1, 2], "L2": [7, 8]}) == [2, 1, 7, 8]
