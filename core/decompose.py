"""
Operation-text decomposition: splits a compound operation name such as
"S/FLY D/FLY & FRONT RISE SERGE" into its component operations so each can
be matched against the skill matrix on its own.

Pure functions only - no I/O, no framework imports - so they are trivially
unit-testable.
"""
from __future__ import annotations

import re

_SPLIT_RE = re.compile(r"\s*(?:&|\+|,|\band\b)\s*", re.IGNORECASE)
_PAREN_RE = re.compile(r"\(.*?\)")


def split_components(text: str) -> list[str]:
    """Splits on '&', '+', ',' and the word 'and'. Parenthetical notes are
    ignored for splitting purposes (e.g. '( YOKE BACK RISE FOA )')."""
    cleaned = _PAREN_RE.sub(" ", str(text or ""))
    parts = [p.strip() for p in _SPLIT_RE.split(cleaned)]
    return [p for p in parts if p]


def component_variants(components: list[str]) -> list[list[str]]:
    """
    For each component, the candidate spellings to try when matching.

    Compound names usually share their trailing action word:
        "S/FLY D/FLY & FRONT RISE SERGE"  ->  the first part is implicitly
        "S/FLY D/FLY SERGE". So every component also gets a variant with the
        last component's final word appended.
    """
    if not components:
        return []
    tail = components[-1].split()[-1] if components[-1].split() else ""
    variants = []
    for i, comp in enumerate(components):
        options = [comp]
        if tail and i < len(components) - 1 and tail.lower() not in comp.lower().split():
            options.append(f"{comp} {tail}")
        variants.append(options)
    return variants
