"""
value_registry.py
-----------------
Value-level resolution — resolves cell CONTENTS inside columns (e.g. "M" or 
"पुरुष" -> "male") using `values.yaml`.

Unlike FieldResolver, ValueResolver is scoped by reusable CATEGORY (e.g. "sex", 
"yes_no", "province_names") so the same raw value can resolve appropriately across
different domains.
"""

from pathlib import Path
import pandas as pd
import yaml

from .normalizers import normalize_devanagari_digits, normalize_whitespace_artifacts


def _clean_key(val: str) -> str:
    """Standardizes cell string keys across Devanagari digits, hidden Unicode, and casing."""
    if val is None:
        return ""
    clean = normalize_whitespace_artifacts(str(val))
    clean = normalize_devanagari_digits(clean)
    return clean.lower().strip()


class ValueResolver:
    """Looks up raw cell values and returns their canonical representation scoped by category."""

    def __init__(self, registry_path: str | Path):
        with open(registry_path, encoding="utf-8") as f:
            self.registry = yaml.safe_load(f) or {}

        # Build reverse lookup per category: cleaned_alias -> canonical_value
        self._alias_maps: dict[str, dict[str, str]] = {}
        for category, canonical_map in self.registry.items():
            alias_map = {}
            for canonical, aliases in canonical_map.items():
                # 1. Auto-add canonical key itself as a valid alias
                alias_map[_clean_key(canonical)] = canonical
                # 2. Map all explicit aliases
                for alias in aliases:
                    alias_map[_clean_key(alias)] = canonical
            self._alias_maps[category] = alias_map

    def resolve(self, value: str, category: str) -> str | None:
        """Returns the canonical value for a raw cell value within a given category,
        or None if unknown.
        """
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        alias_map = self._alias_maps.get(category, {})
        return alias_map.get(_clean_key(value))

    def resolve_column(
        self, values: list[str] | pd.Series, category: str
    ) -> tuple[list | pd.Series, list[str]]:
        """Resolves an entire column of values against one category.

        Accepts either a Python list or pandas Series. Unresolved values are left 
        as-is (no guessing) and flagged in the unmapped list.

        Returns:
            resolved_values (list | pd.Series): Transformed series or list
            unmapped (list[str]): Distinct unmapped raw values for proposal queue
        """
        is_series = isinstance(values, pd.Series)
        input_iterable = values.tolist() if is_series else values

        resolved = []
        unmapped = set()
        for v in input_iterable:
            canonical = self.resolve(v, category)
            if canonical is not None:
                resolved.append(canonical)
            else:
                resolved.append(v)  # Keep raw value, do not guess
                if pd.notna(v) and str(v).strip() != "":
                    unmapped.add(str(v))

        result = pd.Series(
            resolved, index=values.index) if is_series else resolved
        return result, sorted(unmapped)

    def resolve_dataframe(
        self, df: pd.DataFrame, column_category_map: dict[str, str]
    ) -> tuple[pd.DataFrame, dict[str, list[str]]]:
        """Resolves multiple columns in a DataFrame in a single call using a
        mapping of `{column_name: category_name}`.

        Returns:
            transformed_df (pd.DataFrame): Copy of DataFrame with resolved values
            all_unmapped (dict[str, list[str]]): Map of column -> unmapped raw values
        """
        df_resolved = df.copy()
        all_unmapped = {}

        for col, category in column_category_map.items():
            if col in df_resolved.columns:
                resolved_col, unmapped = self.resolve_column(
                    df_resolved[col], category)
                df_resolved[col] = resolved_col
                if unmapped:
                    all_unmapped[col] = unmapped

        return df_resolved, all_unmapped
