"""
Column HEADER resolution — problem #2 from the checklist (naming differences
like c.id vs c_no), NOT the casing/value problem. See normalizers.py for that.
"""

from pathlib import Path

import yaml


class FieldResolver:
    """Looks up a raw column name and returns its canonical name, if known."""

    def __init__(self, registry_path: str | Path):
        with open(registry_path, encoding="utf-8") as f:
            self.registry = yaml.safe_load(f) or {}

        # build reverse lookup: alias (lowercased) -> canonical name
        self._alias_map: dict[str, str] = {}
        for canonical, info in self.registry.items():
            for alias in info.get("aliases", []):
                self._alias_map[alias.lower().strip()] = canonical

    def resolve(self, raw_field_name: str) -> str | None:
        """Returns the canonical name for a raw column name, or None if unknown.
        Never guesses — an unrecognized field returns None, not a best guess."""
        return self._alias_map.get(raw_field_name.lower().strip())

    def resolve_columns(self, columns: list[str]) -> tuple[dict[str, str], list[str]]:
        """Resolves a list of column names.
        Returns (rename_map, unmapped) — rename_map is ready for df.rename(columns=...),
        unmapped is the list of columns that had no known canonical name."""
        rename_map = {}
        unmapped = []
        for col in columns:
            canonical = self.resolve(col)
            if canonical:
                rename_map[col] = canonical
            else:
                unmapped.append(col)
        return rename_map, unmapped
