"""
Infers skill-group qualifications that the skill matrix never states
explicitly, from the *wording* of operations.

Two mechanisms, both gated by machine-type compatibility:
  1. Near-match   - an OB operation whose wording is (almost) identical to a
                    skill the employee holds, despite typos/abbreviations.
  2. Composition  - an OB operation made of several operations joined by
                    '&' / '+' ("A & B"): an employee qualifies when they hold
                    EVERY component skill.

Returned qualifications are additive: they are merged into the explicit
skill matrix by core.state.skill_matrix_dict.
"""
from __future__ import annotations

import re
from collections import defaultdict

from rapidfuzz import fuzz

from core.decompose import component_variants, split_components
from core.matching import normalize, squashed

WHOLE_MATCH_THRESHOLD = 90
COMPONENT_MATCH_THRESHOLD = 86
MACHINE_SIMILARITY_THRESHOLD = 80
AMBIGUITY_MARGIN = 3  # accept runner-up skill texts within this many points of the best

# "Related wording" evidence (weaker than a near-match, stronger than machine-only).
MIN_SHARED_TOKENS = 2
RELATED_MIN_COVERAGE = 0.66   # share of the shorter name's words found in the other
TOKEN_TYPO_THRESHOLD = 80
_STOP_TOKENS = {"for", "with", "the", "and", "into", "onto", "from", "time", "times", "after", "before", "all", "round"}
# Words that describe the action or position rather than the part being worked on.
# Sharing ONLY these is not evidence of related skill (e.g. "BACK X ATTACH" vs "BACK Y ATTACH").
_GENERIC_TOKENS = {
    "attach", "top", "make", "stitch", "close", "set", "join", "tack", "tacking",
    "back", "front", "side", "left", "right", "upper", "lower", "inner", "outer",
    "panel", "single", "both", "complete", "marking",
}

# Spelling variants seen in real files, canonicalised before scoring.
_CANONICAL = tuple(
    (re.compile(rf"\b{wrong}\b"), right)
    for wrong, right in (
        ("surge", "serge"),
        ("fornt", "front"),
        ("bartake", "bartack"),
        ("barteck", "bartack"),
        ("linning", "lining"),
        ("lable", "label"),
        ("segrigation", "segregation"),
        ("sefty", "safety"),
        ("pkt", "pocket"),
    )
)


def machine_key(machine) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(machine or "").upper())


def _machines_compatible(a: str, b: str) -> bool:
    ka, kb = machine_key(a), machine_key(b)
    if not ka or not kb or ka == kb:
        return True
    return fuzz.ratio(ka, kb) >= MACHINE_SIMILARITY_THRESHOLD


def _canonical(text: str) -> str:
    out = str(text or "").lower()
    for pattern, replacement in _CANONICAL:
        out = pattern.sub(replacement, out)
    return out


def similarity(a: str, b: str) -> float:
    a, b = _canonical(a), _canonical(b)
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return max(fuzz.token_sort_ratio(na, nb), fuzz.ratio(squashed(a), squashed(b)))


def _best_texts(query: str, vocab: dict, op_machine: str, threshold: float) -> list[tuple]:
    """Vocab keys (machine-compatible) scoring within the margin of the best."""
    scored = [
        (similarity(query, info["text"]), key)
        for key, info in vocab.items()
        if _machines_compatible(op_machine, info["machine"])
    ]
    scored = [s for s in scored if s[0] >= threshold]
    if not scored:
        return []
    top = max(score for score, _ in scored)
    return [key for score, key in scored if score >= top - AMBIGUITY_MARGIN]


def _holders(keys: list[tuple], vocab: dict) -> set:
    return set().union(*(vocab[k]["holders"] for k in keys)) if keys else set()


def build_vocab(skill_pairs) -> dict:
    """{(skill_text, machine_key): {"text", "machine", "holders": set(employee)}}
    Keyed by text AND machine, so the same skill name on two machines stays
    two separate entries with their own holders."""
    vocab: dict = {}
    for _, r in skill_pairs.iterrows():
        text = r.get("skill_text")
        if not text:
            continue
        machine = str(r.get("machine_type") or "")
        entry = vocab.setdefault((text, machine_key(machine)), {"text": text, "machine": machine, "holders": set()})
        entry["holders"].add(str(r["employee"]))
    return vocab


def _meaningful_tokens(text: str) -> list[str]:
    cleaned = normalize(_canonical(text)).replace("&", " ")
    tokens = [t for t in cleaned.split() if len(t) >= 3 and t not in _STOP_TOKENS]
    return list(dict.fromkeys(tokens))


def _same_token(a: str, b: str) -> bool:
    if a == b:
        return True
    return len(a) >= 4 and len(b) >= 4 and fuzz.ratio(a, b) >= TOKEN_TYPO_THRESHOLD


def token_overlap(a: str, b: str) -> float:
    """
    0..1 strength of wording overlap between two operation names, based on
    the words of the SHORTER name that also appear (typo-tolerant) in the
    longer one. Returns 0 unless at least two words are shared and at least
    one of them names a part/object rather than just an action or position.
        "BACK LABLE ATTACH"      ~ "CENTER BACK LABEL ATTACH"  -> 1.0
        "BOTTOM HEM RUN STITCH"  ~ "BOTTOM HEM (SNLS)"         -> 1.0
    """
    ta, tb = _meaningful_tokens(a), _meaningful_tokens(b)
    if not ta or not tb:
        return 0.0
    small, large = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    shared = [t for t in small if any(_same_token(t, u) for u in large)]
    if len(shared) < MIN_SHARED_TOKENS or all(t in _GENERIC_TOKENS for t in shared):
        return 0.0
    coverage = len(shared) / len(small)
    return coverage if coverage >= RELATED_MIN_COVERAGE else 0.0


def related_holders(operation: str, machine: str, vocab: dict) -> dict:
    """{employee: strength} for people holding a skill with related wording
    on a compatible machine. Strength = best overlap over their skills."""
    out: dict = {}
    for info in vocab.values():
        if not _machines_compatible(machine, info["machine"]):
            continue
        strength = token_overlap(operation, info["text"])
        if strength <= 0:
            continue
        for emp in info["holders"]:
            out[emp] = max(out.get(emp, 0.0), strength)
    return out


def explain_operation(operation: str, machine: str, vocab: dict) -> dict:
    """
    Why an operation was (or was not) matched.
    Returns {"mode": "near-match"|"composition"|"partial"|"none",
             "texts": [...], "holders": set, "partial": set}
      holders - qualified outright (whole name or EVERY component)
      partial - hold at least one component of a compound operation
    """
    whole = _best_texts(operation, vocab, machine, WHOLE_MATCH_THRESHOLD)
    if whole:
        return {"mode": "near-match", "texts": sorted({vocab[k]["text"] for k in whole}),
                "holders": _holders(whole, vocab), "partial": set()}

    components = split_components(operation)
    none = {"mode": "none", "texts": [], "holders": set(), "partial": set()}
    if len(components) < 2:
        return none

    matched: list[list[tuple]] = []
    all_matched = True
    for options in component_variants(components):
        best: list[tuple] = []
        best_score = 0.0
        for option in options:
            keys = _best_texts(option, vocab, machine, COMPONENT_MATCH_THRESHOLD)
            if keys:
                score = max(similarity(option, vocab[k]["text"]) for k in keys)
                if score > best_score:
                    best, best_score = keys, score
        if best:
            matched.append(best)
        else:
            all_matched = False

    if not matched:
        return none

    holder_sets = [_holders(keys, vocab) for keys in matched]
    texts = sorted({vocab[k]["text"] for ks in matched for k in ks})
    union = set().union(*holder_sets)
    if all_matched:
        everyone = set.intersection(*holder_sets)
        return {"mode": "composition", "texts": texts, "holders": everyone, "partial": union - everyone}
    return {"mode": "partial", "texts": texts, "holders": set(), "partial": union}


def infer_qualifications(ob_rows: list[dict], skill_pairs) -> dict:
    """{employee: set(skill_group)} qualified outright for the operations in ob_rows."""
    if skill_pairs is None or not ob_rows:
        return {}
    vocab = build_vocab(skill_pairs)
    cache: dict = {}
    out: dict = defaultdict(set)
    for row in ob_rows:
        key = (row["operation"], row.get("machine_type") or "")
        if key not in cache:
            cache[key] = explain_operation(key[0], key[1], vocab)["holders"]
        for emp in cache[key]:
            out[emp].add(row["skill_group"])
    return dict(out)


def infer_weak_evidence(ob_rows: list[dict], skill_pairs) -> tuple[dict, dict]:
    """
    Evidence weaker than a qualification, per Skill Group:
      partial: {skill_group: set(employee)}          holds some component skills
      related: {skill_group: {employee: strength}}   holds similarly-worded skills
    """
    partial: dict = defaultdict(set)
    related: dict = defaultdict(dict)
    if skill_pairs is None or not ob_rows:
        return {}, {}
    vocab = build_vocab(skill_pairs)
    cache: dict = {}
    for row in ob_rows:
        key = (row["operation"], row.get("machine_type") or "")
        if key not in cache:
            cache[key] = (
                explain_operation(key[0], key[1], vocab)["partial"],
                related_holders(key[0], key[1], vocab),
            )
        part, rel = cache[key]
        sg = row["skill_group"]
        partial[sg] |= part
        for emp, strength in rel.items():
            related[sg][emp] = max(related[sg].get(emp, 0.0), strength)
    return dict(partial), dict(related)
