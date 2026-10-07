import pandas as pd

from core.decompose import component_variants, split_components
from core.inference import build_vocab, explain_operation, infer_qualifications, similarity


def _skills(rows):
    return pd.DataFrame(rows, columns=["employee", "skill_text", "machine_type"])


SKILLS = _skills(
    [
        ("E1", "FRONT RISE SERGE", "3TO/L"),
        ("E1", "S/FLY D/FLY SERGE", "3TO/L"),
        ("E2", "FRONT RISE SERGE", "3TO/L"),
        ("E3", "S/FLY D/FLY SERGE", "3TO/L"),
        ("E4", "FRONT RISE SERGE", "SNLS[3]"),
        ("E4", "S/FLY D/FLY SERGE", "SNLS[3]"),
    ]
)


def test_split_on_ampersand_and_plus():
    assert split_components("A B & C D + E F") == ["A B", "C D", "E F"]


def test_split_ignores_parenthetical_notes():
    assert split_components("CUTTING & CHECKING ( YOKE BACK RISE FOA )") == ["CUTTING", "CHECKING"]


def test_variants_inherit_shared_tail():
    variants = component_variants(["S/FLY D/FLY", "FRONT RISE SERGE"])
    assert "S/FLY D/FLY SERGE" in variants[0]
    assert variants[1] == ["FRONT RISE SERGE"]


def test_composition_requires_every_component_and_machine_match():
    result = explain_operation("S/FLY D/FLY & FORNT RISE SURGE", "3T O/L", build_vocab(SKILLS))
    assert result["mode"] == "composition"
    assert result["holders"] == {"E1"}  # E4 holds both but on an incompatible machine


def test_near_match_tolerates_typos():
    assert similarity("FRONT RISE SERGE", "FORNT RISE SURGE") >= 90


def test_front_and_back_are_not_confused():
    assert similarity("FRONT RISE SERGE", "BACK RISE SERGE") < 90


def test_unrelated_operation_gets_no_inference():
    assert explain_operation("BOTTOM HEM RUN STITCH", "SNLS [3]", build_vocab(SKILLS))["mode"] == "none"


def test_infer_qualifications_maps_to_skill_group():
    rows = [{"operation": "S/FLY D/FLY & FORNT RISE SURGE", "machine_type": "3T O/L", "skill_group": "SG-X"}]
    assert infer_qualifications(rows, SKILLS) == {"E1": {"SG-X"}}
