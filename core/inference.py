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

# Spelling variants seen in real files, canonicalised before scoring.
_CANONICAL = (
    (re.compile(r"\bsurge\b"), "serge"),
    (re.compile(r"\bfornt\b"), "front"),
    (re.compile(r"\bbartake\b"), "bartack"),
    (re.compile(r"\blinning\b"), "lining"),
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


def explain_operation(operation: str, machine: str, vocab: dict) -> dict:
    """Why an operation was (or was not) matched - used for diagnostics and tests.
    Returns {"mode": "near-match"|"composition"|"none", "texts": [...], "holders": set}"""
    whole = _best_texts(operation, vocab, machine, WHOLE_MATCH_THRESHOLD)
    if whole:
        return {"mode": "near-match", "texts": sorted({vocab[k]["text"] for k in whole}), "holders": _holders(whole, vocab)}

    components = split_components(operation)
    if len(components) < 2:
        return {"mode": "none", "texts": [], "holders": set()}

    matched: list[list[tuple]] = []
    for options in component_variants(components):
        best: list[tuple] = []
        best_score = 0.0
        for option in options:
            keys = _best_texts(option, vocab, machine, COMPONENT_MATCH_THRESHOLD)
            if keys:
                score = max(similarity(option, vocab[k]["text"]) for k in keys)
                if score > best_score:
                    best, best_score = keys, score
        if not best:
            return {"mode": "none", "texts": [], "holders": set()}
        matched.append(best)

    holders = set.intersection(*(_holders(texts, vocab) for texts in matched))
    return {"mode": "composition", "texts": sorted({vocab[k]["text"] for ks in matched for k in ks}), "holders": holders}


def infer_qualifications(ob_rows: list[dict], skill_pairs) -> dict:
    """{employee: set(skill_group)} inferred for the operations in ob_rows."""
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
