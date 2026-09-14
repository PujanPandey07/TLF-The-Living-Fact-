from tlf_core.value_registry import ValueResolver
from pathlib import Path

import pytest

from tlf_core import (
    FieldResolver,
    default_registry_path,
    normalize_casing,
    normalize_devanagari_digits,
    normalize_date,
)

FIELDS_YAML = default_registry_path("fields.yaml")


def test_resolver_finds_known_alias():
    resolver = FieldResolver(FIELDS_YAML)
    assert resolver.resolve("Area/Sex") == "area_sex"


def test_resolver_returns_none_for_unknown_field():
    resolver = FieldResolver(FIELDS_YAML)
    assert resolver.resolve("some_totally_unseen_field") is None


def test_resolver_resolve_columns_splits_mapped_and_unmapped():
    resolver = FieldResolver(FIELDS_YAML)
    rename_map, unmapped = resolver.resolve_columns(
        ["Area/Sex", "Total", "c.id"]
    )
    assert rename_map == {"Area/Sex": "area_sex",
                          "Total": "total", "c.id": "citizenship_id"}
    assert unmapped == []


def test_resolver_default_path_works_with_no_arguments():
    """New in 0.1.2 — FieldResolver() with no path uses its own bundled fields.yaml."""
    resolver = FieldResolver()
    assert resolver.resolve("जिल्ला") == "district"


def test_normalize_casing_fixes_real_arghakhanchi_finding():
    # This is the actual real-world case found in Phase 1:
    # two ODN datasets, same district, different casing.
    a = normalize_casing("Arghakhanchi")
    b = normalize_casing("ARGHAKHANCHI")
    assert a == b == "arghakhanchi"


# TODO: this test is STALE, not fixed yet — it still asserts the OLD
# pre-Session-8 behavior (normalizers raising NotImplementedError), but
# normalize_devanagari_digits/normalize_date were actually implemented since
# then. Needs replacing with real expected-output assertions once we confirm
# what these functions actually return today. Left failing deliberately
# rather than guessed, to avoid asserting the wrong thing silently.
def test_normalize_devanagari_digits_and_date():
    """These were stubs at write-time (see git history); now implemented for real.
    normalize_date reformats to ISO YYYY-MM-DD — it does NOT convert BS to AD,
    it just standardizes the format (per tlf-core's documented 'format only' scope)."""
    assert normalize_devanagari_digits("९८-५२२१११") == "98-522111"
    assert normalize_date("10/06/2079") == "2079-06-10"


class TestValueResolver:
    @pytest.fixture
    def resolver(self):
        """Load the real values.yaml bundled with the installed package."""
        return ValueResolver(default_registry_path("values.yaml"))

    # ── resolve() ─────────────────────────────────────────────────────────

    def test_resolve_male_variants(self, resolver):
        """All known aliases for 'male' should resolve to the same canonical."""
        assert resolver.resolve("M", category="sex") == "male"
        assert resolver.resolve("m", category="sex") == "male"
        assert resolver.resolve("male", category="sex") == "male"
        assert resolver.resolve("पुरुष", category="sex") == "male"
        # Extra whitespace should be stripped too
        assert resolver.resolve("  M  ", category="sex") == "male"

    def test_resolve_female_variants(self, resolver):
        """All known aliases for 'female' should resolve to the same canonical."""
        assert resolver.resolve("F", category="sex") == "female"
        assert resolver.resolve("f", category="sex") == "female"
        assert resolver.resolve("female", category="sex") == "female"
        assert resolver.resolve("महिला", category="sex") == "female"

    def test_resolve_unknown_returns_none(self, resolver):
        """Values not in the registry should return None, not crash or guess."""
        assert resolver.resolve("XYZ", category="sex") is None
        assert resolver.resolve("", category="sex") is None

    def test_resolve_none_input_returns_none(self, resolver):
        """None input should be handled gracefully."""
        assert resolver.resolve(None, category="sex") is None

    def test_resolve_missing_category_returns_none(self, resolver):
        """Asking for a category that doesn't exist should return None."""
        assert resolver.resolve("male", category="nonexistent") is None

    # ── resolve_column() ────────────────────────────────────────────────

    def test_resolve_column_maps_and_preserves(self, resolver):
        """
        Known values get mapped; unknown values stay as-is.
        Unmapped values are reported separately.
        """
        raw = ["M", "f", "पुरुष", "XYZ", None, "male"]
        resolved, unmapped = resolver.resolve_column(raw, category="sex")

        assert resolved == ["male", "female", "male", "XYZ", None, "male"]
        assert unmapped == ["XYZ"]

    def test_resolve_column_empty_list(self, resolver):
        """Empty input should return empty output, no crash."""
        resolved, unmapped = resolver.resolve_column([], category="sex")
        assert resolved == []
        assert unmapped == []
