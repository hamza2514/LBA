"""
Pooling / merge engine for Layout Balancing (single-line, multi-line) and
Absentee Balancing.

Rules:
  - An operation with Head Allocated == 1 whose Work Minutes are <= 50% of
    shift time leaves its person under-utilized (spare time).
  - An operation whose Work Minutes exceed what its allocated heads cover
    creates an "overflow" chunk of leftover work.
  - Leftovers are packed into "bins" (one bin = one person's day):
    same Skill Group first, then same Machine Type, never otherwise.
  - Operations are ONLY ever merged within the same line section
    (Back, Front, Assembly, ...). Different sections never share an employee.
  - Multi-line: the same Skill Group (same section) with leftover capacity in
    another line takes priority over same-line pooling.

This module only decides WHICH operations are bundled into one person's day;
assignment.py turns a bin into an actual named employee.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.formulas import OperationCalc

UNDER_UTILIZED_THRESHOLD = 0.5  # <=50% of shift time triggers pooling


@dataclass
class Chunk:
    """One poolable piece of work: a whole under-utilized operation, or the
    leftover overflow portion of an over-capacity one."""
    line: str
    operation: str
    skill_group: str
    machine_type: str
    minutes: float
    kind: str  # "under_utilized" | "overflow"
    sam: float = 0.0
    section: str = ""
    seq: int = 0


@dataclass
class Bin:
    """One person's day: one or more chunks bundled together."""
    chunks: list[Chunk] = field(default_factory=list)
    cross_line: bool = False

    @property
    def total_minutes(self) -> float:
        return sum(c.minutes for c in self.chunks)

    @property
    def lines(self) -> set[str]:
        return {c.line for c in self.chunks}

    @property
    def skill_groups(self) -> set[str]:
        return {c.skill_group for c in self.chunks}

    @property
    def section(self) -> str:
        return self.chunks[0].section if self.chunks else ""


def identify_chunks(line: str, calcs: list[OperationCalc], shift_time: float) -> list[Chunk]:
    """Find every poolable chunk of a line's computed operations."""
    chunks = []
    for c in calcs:
        capacity = c.head_allocated * shift_time
        if c.head_allocated == 1 and c.work_minutes <= UNDER_UTILIZED_THRESHOLD * shift_time:
            minutes, kind = c.work_minutes, "under_utilized"
        elif c.work_minutes > capacity:
            minutes, kind = c.work_minutes - capacity, "overflow"
        else:
            continue
        chunks.append(
            Chunk(line, c.operation, c.skill_group, c.machine_type, minutes, kind,
                  sam=c.sam, section=c.section, seq=c.seq)
        )
    return chunks


def _fits(bin_: Bin, chunk: Chunk, shift_time: float) -> bool:
    return bin_.total_minutes + chunk.minutes <= shift_time


def _compatible(bin_: Bin, chunk: Chunk) -> str | None:
    """'skill' (priority 1), 'machine' (priority 2) or None. Never across sections."""
    if chunk.section != bin_.section:
        return None
    if chunk.skill_group and chunk.skill_group in bin_.skill_groups:
        return "skill"
    if chunk.machine_type and any(c.machine_type == chunk.machine_type for c in bin_.chunks):
        return "machine"
    return None


def _place(bins: list[Bin], chunk: Chunk, shift_time: float, mode: str) -> bool:
    for bin_ in bins:
        if _compatible(bin_, chunk) == mode and _fits(bin_, chunk, shift_time):
            bin_.chunks.append(chunk)
            return True
    return False


def pack_same_line(chunks: list[Chunk], shift_time: float) -> list[Bin]:
    """Greedy bin-packing within one line (largest chunks first)."""
    bins: list[Bin] = []
    for chunk in sorted(chunks, key=lambda c: -c.minutes):
        if _place(bins, chunk, shift_time, "skill") or _place(bins, chunk, shift_time, "machine"):
            continue
        bins.append(Bin(chunks=[chunk]))
    return bins


def pack_multi_line(chunks_by_line: dict, shift_time: float) -> list[Bin]:
    """Cross-line pairing first (same Skill Group + same section), then the
    remainder is packed line by line."""
    used: set[int] = set()
    bins: list[Bin] = []

    by_skill: dict[tuple, list[Chunk]] = {}
    for chunks in chunks_by_line.values():
        for c in chunks:
            if c.skill_group:
                by_skill.setdefault((c.skill_group, c.section), []).append(c)

    for group in by_skill.values():
        group = sorted(group, key=lambda c: -c.minutes)
        for i, c1 in enumerate(group):
            if id(c1) in used:
                continue
            for c2 in group[i + 1:]:
                if id(c2) in used or c2.line == c1.line:
                    continue
                if c1.minutes + c2.minutes <= shift_time:
                    bins.append(Bin(chunks=[c1, c2], cross_line=True))
                    used.update((id(c1), id(c2)))
                    break

    for chunks in chunks_by_line.values():
        bins.extend(pack_same_line([c for c in chunks if id(c) not in used], shift_time))
    return bins
