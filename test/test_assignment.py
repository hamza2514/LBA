from types import SimpleNamespace

from core.assignment import BASIS_MACHINE, BASIS_PARTIAL, BASIS_RELATED, BASIS_SKILL, select_employee
from core.staffing import StaffingEvidence


def _select(evidence, groups, machines=(), lines=("L1",), line_of=None, used=()):
    return select_employee(set(groups), set(machines), set(lines), evidence, line_of or {}, set(used))


def test_bundle_goes_to_someone_holding_at_least_one_operation():
    ev = StaffingEvidence(strong={"A": {"E1"}, "B": set(), "C": set()}, machines={"E9": {"HELPER"}})
    assert _select(ev, {"A", "B", "C"}, {"HELPER"}) == ("E1", BASIS_PARTIAL)


def test_bundle_prefers_whoever_covers_most_operations():
    ev = StaffingEvidence(strong={"A": {"E1", "E2"}, "B": {"E2"}})
    assert _select(ev, {"A", "B"}) == ("E2", BASIS_SKILL)


def test_partial_component_evidence_beats_machine_only():
    ev = StaffingEvidence(partial={"X": {"E2"}}, machines={"E1": {"3TOL"}, "E2": {"3TOL"}})
    assert _select(ev, {"X"}, {"3TOL"}, line_of={"E1": "L1"}) == ("E2", BASIS_PARTIAL)


def test_related_wording_beats_machine_only_and_ranks_by_strength():
    ev = StaffingEvidence(related={"X": {"E1": 0.7, "E2": 1.0}}, machines={"E3": {"SNLS3"}})
    assert _select(ev, {"X"}, {"SNLS3"}) == ("E2", BASIS_RELATED)


def test_machine_type_is_the_last_resort():
    ev = StaffingEvidence(machines={"E1": {"SNLS3"}})
    assert _select(ev, {"X"}, {"SNLS3"}) == ("E1", BASIS_MACHINE)


def test_used_employees_are_skipped_and_nobody_left_is_unstaffed():
    ev = StaffingEvidence(strong={"X": {"E1"}})
    assert _select(ev, {"X"}, used={"E1"}) == (None, "")


def test_same_line_breaks_ties():
    ev = StaffingEvidence(strong={"X": {"E1", "E2"}})
    assert _select(ev, {"X"}, line_of={"E2": "L1", "E1": "L2"})[0] == "E2"


def test_restrict_to_removes_absent_people_from_every_tier():
    ev = StaffingEvidence(
        strong={"X": {"E1", "E2"}}, partial={"X": {"E3"}}, related={"X": {"E4": 1.0}}, machines={"E5": {"M"}}
    ).restrict_to({"E2", "E4"})
    assert ev.strong["X"] == {"E2"} and ev.partial["X"] == set()
    assert ev.related["X"] == {"E4": 1.0} and ev.machines == {}
