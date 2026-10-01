"""
Skill-group matching engine.

Matches a newly uploaded operation (description + machine type) against the
reference skill taxonomy that was built up over several rounds of manual
review. This is what lets a brand-new factory's Operation Breakdown get
useful Skill Group suggestions on day one, instead of starting from a blank
sheet like the very first factory did.

Two lessons learned from the manual taxonomy-building process are baked in
here on purpose:
  1. Machine type is usually the strongest signal for "same skill" — see
     STRONG_MACHINE_MATCH below.
  2. Spacing differences ("Inseam" vs "In seam") should not count as a real
     difference. We compare both the normally-spaced and the
     space-collapsed form and take the best score.
"""
from __future__ import annotations

import re
import functools
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skill_taxonomy.csv"

STOP_WORDS = {"for", "at", "with", "the", "a", "an", "to", "of", "and", "on"}

MATCH_THRESHOLD = 90  # conservative on purpose — see round 3/5 notes in chat history


def clean(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def normalize(desc: str) -> str:
    """Strip SAM-variant suffixes (-2, -3, 14SPI, parenthetical notes,
    'with ...' clauses) so operations that differ only by pass-count or
    stitch detail compare as the same base operation."""
    d = clean(desc).lower()
    d = re.sub(r"\(.*?\)", "", d)
    d = re.split(r"\bwith\b", d)[0]
    d = re.sub(r"\d+\s*spi", "", d)
    d = re.sub(r"-\s*\d+\b", "", d)
    d = re.sub(r"\b\d+\b", "", d)
    d = re.sub(r"[^a-z& ]", " ", d)
    d = re.sub(r"\s+", " ", d).strip()
    return d


def squashed(desc: str) -> str:
    """Space-collapsed form, so 'In seam' and 'Inseam' compare as identical.
    Learned from a real correction during the taxonomy review — see chat."""
    return normalize(desc).replace(" ", "")


def word_set(desc: str) -> set[str]:
    n = normalize(desc)
    return {w for w in n.split() if w and w not in STOP_WORDS and len(w) > 2}


def best_text_score(a: str, b: str) -> float:
    """Best of normal-form and squashed-form comparison."""
    norm_score = fuzz.token_sort_ratio(normalize(a), normalize(b))
    squash_score = fuzz.ratio(squashed(a), squashed(b))
    return max(norm_score, squash_score)


@dataclass
class TaxonomyRow:
    description: str
    machine_type: str
    sam: float | None
    skill_group_id: str
    norm: str
    squashed: str


@functools.lru_cache(maxsize=1)
def load_taxonomy() -> list[TaxonomyRow]:
    df = pd.read_csv(TAXONOMY_PATH)
    rows = []
    for _, r in df.iterrows():
        desc = clean(r.get("operation_description"))
        if not desc:
            continue
        rows.append(
            TaxonomyRow(
                description=desc,
                machine_type=clean(r.get("machine_type")),
                sam=r.get("sam"),
                skill_group_id=clean(r.get("skill_group_id")),
                norm=normalize(desc),
                squashed=squashed(desc),
            )
        )
    return rows


def taxonomy_by_machine() -> dict[str, list[TaxonomyRow]]:
    taxonomy = load_taxonomy()
    by_mach: dict[str, list[TaxonomyRow]] = {}
    for row in taxonomy:
        by_mach.setdefault(row.machine_type, []).append(row)
    return by_mach


def match_operation(
    description: str,
    machine_type: str | None = None,
    threshold: int = MATCH_THRESHOLD,
):
    """
    Try to match one uploaded operation against the taxonomy.

    If machine_type is given, search is restricted to taxonomy rows on that
    same machine first (cheap and much more accurate — machine type is the
    dominant signal for "same skill", per the round-3 finding). If nothing
    clears the threshold within that machine, falls back to a full search.

    Returns (skill_group_id, score, matched_description) or (None, 0, None).
    """
    taxonomy = load_taxonomy()
    if not taxonomy or not clean(description):
        return None, 0, None

    candidates = taxonomy
    if machine_type:
        by_mach = taxonomy_by_machine()
        same_machine = by_mach.get(clean(machine_type))
        if same_machine:
            candidates = same_machine

    norm_q = normalize(description)
    squash_q = squashed(description)

    best_row, best_score = None, 0
    for row in candidates:
        score = max(
            fuzz.token_sort_ratio(norm_q, row.norm),
            fuzz.ratio(squash_q, row.squashed),
        )
        if score > best_score:
            best_row, best_score = row, score

    if best_row and best_score >= threshold:
        return best_row.skill_group_id, best_score, best_row.description

    # fall back to full-database search if machine-restricted search found nothing
    if machine_type and candidates is not taxonomy:
        return match_operation(description, machine_type=None, threshold=threshold)

    return None, 0, None


def match_dataframe(df: pd.DataFrame, desc_col: str, machine_col: str | None) -> pd.DataFrame:
    """Vectorized-ish helper for the Operation Breakdown page: adds
    suggested_skill_group / match_score / matched_reference columns."""
    out = df.copy()
    sg_ids, scores, refs = [], [], []
    for _, r in out.iterrows():
        desc = r.get(desc_col)
        mach = r.get(machine_col) if machine_col else None
        sg, score, ref = match_operation(desc, mach)
        sg_ids.append(sg)
        scores.append(score)
        refs.append(ref)
    out["suggested_skill_group"] = sg_ids
    out["match_score"] = scores
    out["matched_reference"] = refs
    return out


# ---------------------------------------------------------------------------
# Dynamic (session-time) taxonomy extension.
#
# The base taxonomy in data/skill_taxonomy.csv is the carefully hand-reviewed
# reference. Operations uploaded during real use that don't match anything in
# it are NOT rejected or left blank — per the standing rule, they get matched
# against whatever's been added THIS session too, and if still nothing fits,
# a brand-new Skill Group ID is minted automatically so the tool never blocks
# on an unrecognized operation. New IDs use an "SG-AUTO-" prefix so they're
# easy to spot and review later, distinct from the reviewed "SG-####" ones.
# ---------------------------------------------------------------------------

AUTO_PREFIX = "SG-AUTO-"


def _extra_to_rows(extra_taxonomy: list[dict]) -> list[TaxonomyRow]:
    rows = []
    for e in extra_taxonomy:
        desc = clean(e.get("operation_description"))
        if not desc:
            continue
        rows.append(
            TaxonomyRow(
                description=desc,
                machine_type=clean(e.get("machine_type")),
                sam=e.get("sam"),
                skill_group_id=clean(e.get("skill_group_id")),
                norm=normalize(desc),
                squashed=squashed(desc),
            )
        )
    return rows


def next_auto_id(extra_taxonomy: list[dict]) -> str:
    max_n = 0
    for e in extra_taxonomy:
        sg = clean(e.get("skill_group_id"))
        if sg.startswith(AUTO_PREFIX):
            try:
                max_n = max(max_n, int(sg[len(AUTO_PREFIX):]))
            except ValueError:
                pass
    return f"{AUTO_PREFIX}{max_n + 1:04d}"


def match_operation_dynamic(
    description: str,
    machine_type: str | None,
    extra_taxonomy: list[dict],
    threshold: int = MATCH_THRESHOLD,
):
    """Same as match_operation, but also searches session-added entries
    (extra_taxonomy) first — so operations added earlier in this session are
    immediately reusable, not just the static reference file."""
    extra_rows = _extra_to_rows(extra_taxonomy)
    if extra_rows and clean(description):
        norm_q = normalize(description)
        squash_q = squashed(description)
        candidates = extra_rows
        if machine_type:
            same_mach = [r for r in extra_rows if r.machine_type == clean(machine_type)]
            if same_mach:
                candidates = same_mach
        best_row, best_score = None, 0
        for row in candidates:
            score = max(
                fuzz.token_sort_ratio(norm_q, row.norm),
                fuzz.ratio(squash_q, row.squashed),
            )
            if score > best_score:
                best_row, best_score = row, score
        if best_row and best_score >= threshold:
            return best_row.skill_group_id, best_score, best_row.description

    return match_operation(description, machine_type, threshold)


def get_or_create_skill_group(
    description: str,
    machine_type: str,
    sam,
    extra_taxonomy: list[dict],
    threshold: int = MATCH_THRESHOLD,
):
    """
    The core "never blocks" rule: try to match (static reference + this
    session's additions); if nothing clears the threshold, mint a new
    SG-AUTO-#### id and return the new row to be appended to extra_taxonomy
    by the caller (kept out of this function so it stays a pure lookup and
    the caller controls session-state mutation).

    Returns (skill_group_id, created: bool, new_row_or_None, score).
    """
    sg, score, ref = match_operation_dynamic(description, machine_type, extra_taxonomy, threshold)
    if sg:
        return sg, False, None, score

    new_id = next_auto_id(extra_taxonomy)
    new_row = {
        "operation_description": clean(description),
        "machine_type": clean(machine_type),
        "sam": sam,
        "skill_group_id": new_id,
    }
    return new_id, True, new_row, 0

