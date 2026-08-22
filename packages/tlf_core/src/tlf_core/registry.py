"""
field_registry.py
-----------------
Column HEADER resolution — maps raw dataset column names (e.g. "c.id", "c_no") 
to canonical field names (e.g. "customer_id") using `fields.yaml`.

This module does NOT resolve cell contents (see `value_registry.py`).
"""

from pathlib import Path
import yaml

from .normalizers import normalize_whitespace_artifacts


def _clean_header(header: str) -> str:
    """Standardizes header strings for registry lookup (strips hidden Unicode & lowercases)."""
    if header is None:
        return ""
    clean = normalize_whitespace_artifacts(str(header))
    return clean.lower().strip()


class FieldResolver:
    """Looks up a raw column header name and returns its canonical field name."""

    def __init__(self, registry_path: str | Path):
        with open(registry_path, encoding="utf-8") as f:
            self.registry = yaml.safe_load(f) or {}

        # Build reverse lookup: cleaned_alias -> canonical_field_name
        self._alias_map: dict[str, str] = {}
        for canonical, info in self.registry.items():
            # 1. Auto-include canonical name itself as a valid key
            self._alias_map[_clean_header(canonical)] = canonical
            # 2. Map all declared aliases in fields.yaml
            for alias in info.get("aliases", []):
                self._alias_map[_clean_header(alias)] = canonical

    def resolve(self, raw_field_name: str) -> str | None:
        """Returns the canonical name for a raw column header, or None if unknown.

        Guarantees exact, zero-guessing matching.
        """
        if not raw_field_name:
            return None
        return self._alias_map.get(_clean_header(raw_field_name))

    def resolve_columns(self, columns: list[str]) -> tuple[dict[str, str], list[str]]:
        """Resolves a list of column names.

        Returns:
            rename_map (dict): Ready for `df.rename(columns=rename_map)`
            unmapped (list): Column names that had no known canonical match
        """
        rename_map = {}
        unmapped = []
        for col in columns:
            canonical = self.resolve(col)
            if canonical:
                rename_map[col] = canonical
            else:
                unmapped.append(col)
        return rename_map, unmapped
