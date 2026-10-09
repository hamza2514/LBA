"""
Staffing evidence: everything the engine knows about who can do what, in a
framework-free container so selection logic stays pure and unit-testable.

Evidence is graded per Skill Group, strongest first:
  strong   - holds the skill (explicit, near-match wording, all components of
             a compound operation, or via a Role)
  partial  - holds at least one component of a compound operation
  related  - holds a skill with closely related wording on a compatible
             machine (value = similarity strength, 0..1)
  machine  - has experience on the same machine type (last resort)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


def normalize_machine(machine_type) -> str:
    """Canonical machine-type key: upper-case alphanumerics only, so
    '3T O/L', '3TO/L' and '3t-o/l' are the same machine."""
    return re.sub(r"[^A-Z0-9]", "", str(machine_type or "").upper())


Score = tuple  # (strong_count, partial_count, related_strength)


@dataclass(frozen=True)
class StaffingEvidence:
    strong: dict = field(default_factory=dict)    # {skill_group: set(employee)}
    partial: dict = field(default_factory=dict)   # {skill_group: set(employee)}
    related: dict = field(default_factory=dict)   # {skill_group: {employee: strength}}
    machines: dict = field(default_factory=dict)  # {employee: set(normalized machine)}

    def score(self, employee: str, skill_groups: set) -> Score:
        """How well `employee` covers a unit of work spanning `skill_groups`.
        Each group counts once, at the strongest level the employee has for it."""
        strong = partial = 0
        related = 0.0
        for sg in skill_groups:
            if employee in self.strong.get(sg, ()):
                strong += 1
            elif employee in self.partial.get(sg, ()):
                partial += 1
            else:
                related += self.related.get(sg, {}).get(employee, 0.0)
        return (strong, partial, round(related, 4))

    def candidates(self, skill_groups: set) -> set:
        """Everyone with any skill-based evidence for any of the groups."""
        found: set = set()
        for sg in skill_groups:
            found |= set(self.strong.get(sg, ()))
            found |= set(self.partial.get(sg, ()))
            found |= set(self.related.get(sg, {}))
        return found

    def machine_candidates(self, machines: set) -> set:
        """Employees with experience on ALL given machine types."""
        wanted = {m for m in machines if m}
        if not wanted:
            return set()
        return {emp for emp, have in self.machines.items() if wanted <= have}

    def restrict_to(self, employees: set) -> "StaffingEvidence":
        """Same evidence limited to a subset of people (e.g. who is present)."""
        keep = set(employees)
        return StaffingEvidence(
            strong={sg: set(h) & keep for sg, h in self.strong.items()},
            partial={sg: set(h) & keep for sg, h in self.partial.items()},
            related={sg: {e: s for e, s in h.items() if e in keep} for sg, h in self.related.items()},
            machines={e: m for e, m in self.machines.items() if e in keep},
        )
