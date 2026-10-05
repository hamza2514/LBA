"""
Pooling / merge engine for Layout Balancing (single-line, multi-line) and
Absentee Balancing.

Core idea, confirmed against the user's own worked examples:
  - An operation with Head Allocated == 1 whose Work Minutes are <= 50% of
    shift time leaves its one assigned person under-utilized (spare time).
  - An operation whose Work Minutes exceed what its allocated heads can
    cover in a shift (a side-effect of the 0.3 rounding-down rule) creates
    an "overflow" chunk of leftover, unassigned work.
  - Both kinds of leftover time/work are pooled and packed together into
    "bins" (one bin = one person's day), preferring same Skill Group first,
    falling back to same Machine Type, and never combined if neither
    matches.
  - In multi-line mode, the SAME operation (same Skill Group) appearing in
    a different line with its own leftover capacity takes priority over
    same-line pooling — one person works that operation across two lines.

This module only decides WHICH operations get bundled into one person's
day. Turning a bin into an actual named employee is assignment.py's job.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.formulas import OperationCalc

UNDER_UTILIZED_THRESHOLD = 0.5  # confirmed: <=50% of shift time triggers pooling
EFFICIENCY_TARGET = 0.85        # "at least 480*85%=408 minutes" — soft target, not a hard cap


@dataclass
class Chunk:
    """One poolable piece of work: either a whole under-utilized operation,
    or the leftover overflow portion of an over-capacity one."""
    line: str
    operation: str
    skill_group: str
    machine_type: str
    minutes: float
    kind: str  # "under_utilized" | "overflow"
    sam: float = 0.0  # lets downstream code convert minutes back to a piece-count target


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


def identify_chunks(line: str, calcs: list[OperationCalc], shift_time: float) -> list[Chunk]:
    """Given a line's computed operations, find every poolable chunk."""
    chunks = []
    for c in calcs:
        capacity = c.head_allocated * shift_time
        if c.head_allocated == 1 and c.work_minutes <= UNDER_UTILIZED_THRESHOLD * shift_time:
            chunks.append(Chunk(line, c.operation, c.skill_group, c.machine_type, c.work_minutes, "under_utilized", sam=c.sam))
        elif c.work_minutes > capacity:
            overflow = c.work_minutes - capacity
            chunks.append(Chunk(line, c.operation, c.skill_group, c.machine_type, overflow, "overflow", sam=c.sam))
    return chunks


def _fits(bin_: Bin, chunk: Chunk, shift_time: float) -> bool:
    return bin_.total_minutes + chunk.minutes <= shift_time


def _compatible(bin_: Bin, chunk: Chunk) -> str | None:
    """Returns 'skill' if it matches by skill group (priority 1), 'machine'
    if only by machine type (priority 2), or None if neither."""
    if chunk.skill_group and chunk.skill_group in bin_.skill_groups:
        return "skill"
    if chunk.machine_type and any(c.machine_type == chunk.machine_type for c in bin_.chunks):
        return "machine"
    return None


def pack_same_line(chunks: list[Chunk], shift_time: float) -> list[Bin]:
    """Greedy bin-packing within one line: priority 1 same Skill Group,
    priority 2 same Machine Type, else the chunk stands alone."""
    remaining = sorted(chunks, key=lambda c: -c.minutes)
    bins: list[Bin] = []

    for chunk in remaining:
        placed = False
        for bin_ in bins:
            if _compatible(bin_, chunk) == "skill" and _fits(bin_, chunk, shift_time):
                bin_.chunks.append(chunk)
                placed = True
                break
        if placed:
            continue
        for bin_ in bins:
            if _compatible(bin_, chunk) == "machine" and _fits(bin_, chunk, shift_time):
                bin_.chunks.append(chunk)
                placed = True
                break
        if not placed:
            bins.append(Bin(chunks=[chunk]))

    return bins


def pack_multi_line(chunks_by_line: dict, shift_time: float) -> list[Bin]:
    """
    Priority 1: same Skill Group, different lines — one person covers the
    same operation across two lines. Whatever's left over after that is
    packed same-line as normal (priority 2 skill, priority 3 machine).
    """
    all_chunks = [c for chunks in chunks_by_line.values() for c in chunks]
    used = set()
    bins: list[Bin] = []

    by_skill: dict = {}
    for c in all_chunks:
        if c.skill_group:
            by_skill.setdefault(c.skill_group, []).append(c)

    for sg, group in by_skill.items():
        group = sorted(group, key=lambda c: -c.minutes)
        i = 0
        while i < len(group):
            c1 = group[i]
            if id(c1) in used:
                i += 1
                continue
            for j in range(i + 1, len(group)):
                c2 = group[j]
                if id(c2) in used or c2.line == c1.line:
                    continue
                if c1.minutes + c2.minutes <= shift_time:
                    bins.append(Bin(chunks=[c1, c2], cross_line=True))
                    used.add(id(c1))
                    used.add(id(c2))
                    break
            i += 1

    leftover_by_line = {}
    for line, chunks in chunks_by_line.items():
        leftover_by_line[line] = [c for c in chunks if id(c) not in used]

    for line, chunks in leftover_by_line.items():
        bins.extend(pack_same_line(chunks, shift_time))

    return bins
