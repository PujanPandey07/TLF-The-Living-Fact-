"""
Value-level resolution — resolves values INSIDE a column (e.g. "M" or
"पुरुष" both -> "male"), separate from FieldResolver, which resolves
column HEADERS. See finding #5 in docs/data_quality_checklist.md.
"""

from pathlib import Path

import yaml


class ValueResolver:
    """Looks up a raw category value and returns its canonical form,
    scoped by category (e.g. "sex", "yes_no") since the same raw value
    could mean different things in different categories."""

    def __init__(self, registry_path: str | Path):
        with open(registry_path, encoding="utf-8") as f:
            self.registry = yaml.safe_load(f) or {}

        # build reverse lookup per category: alias (lowercased) -> canonical
        self._alias_maps: dict[str, dict[str, str]] = {}
        for category, canonical_map in self.registry.items():
            alias_map = {}
            for canonical, aliases in canonical_map.items():
                for alias in aliases:
                    alias_map[alias.lower().strip()] = canonical
            self._alias_maps[category] = alias_map

    def resolve(self, value: str, category: str) -> str | None:
        """Returns the canonical value for a raw value within a given
        category, or None if unknown. Never guesses — same principle as
        FieldResolver.resolve()."""
        if value is None:
            return None
        alias_map = self._alias_maps.get(category, {})
        return alias_map.get(value.lower().strip())

    def resolve_column(self, values: list[str], category: str) -> tuple[list, list[str]]:
        """Resolves a whole column of values against one category.
        Returns (resolved_values, unmapped) — unmapped lists the distinct
        raw values that had no known canonical form."""
        resolved = []
        unmapped = set()
        for v in values:
            canonical = self.resolve(v, category)
            if canonical is not None:
                resolved.append(canonical)
            else:
                resolved.append(v)  # leave as-is, don't guess
                if v is not None:
                    unmapped.add(v)
        return resolved, sorted(unmapped)
