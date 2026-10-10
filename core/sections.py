"""
Line-section recognition (Small Parts, Back, Front, Assembly[-1/-2],
Dispatch, Pocket Setter, ...).

Section names vary between factories ("Back", "Back Section", "BACK SECTION"),
so every name is reduced to one canonical label. Only operations that share
the same canonical section may be merged onto one employee.
"""
from __future__ import annotations

import re

_NOISE = re.compile(r"\bsection\b|[^a-z0-9 ]")

_ASSEMBLY = re.compile(r"assembly\s*(?:(?P<one>1|i|one)|(?P<two>2|ii|two))?")
_KNOWN_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"small\s*parts?"), "Small Parts"),
    (re.compile(r"(?:pocket|pkt)\s*setter"), "Pocket Setter"),
    (re.compile(r"dispatch(?:ing)?"), "Dispatch"),
    (re.compile(r"back"), "Back"),
    (re.compile(r"front"), "Front"),
)


def _reduce(text: object) -> str:
    return re.sub(r"\s+", " ", _NOISE.sub(" ", str(text or "").lower())).strip()


def _known_label(reduced: str) -> str | None:
    match = _ASSEMBLY.fullmatch(reduced)
    if match:
        if match.group("one"):
            return "Assembly-1"
        if match.group("two"):
            return "Assembly-2"
        return "Assembly"
    for pattern, label in _KNOWN_PATTERNS:
        if pattern.fullmatch(reduced):
            return label
    return None


def canonical_section(text: object) -> str:
    """Canonical section label; unrecognised names are kept (title-cased)."""
    reduced = _reduce(text)
    if not reduced:
        return ""
    return _known_label(reduced) or reduced.title()


def looks_like_section_label(text: object) -> bool:
    """True for 'Back Section' style labels and bare known names ('Front')."""
    raw = str(text or "").strip().lower()
    if not raw or "total" in raw:
        return False
    return raw.endswith("section") or _known_label(_reduce(raw)) is not None
