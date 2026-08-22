from tlf_core.value_registry import ValueResolver
from pathlib import Path

import pytest

from tlf_core import FieldResolver, normalize_casing, normalize_devanagari_digits, normalize_date

FIELDS_YAML = Path(__file__).parent.parent / "fields.yaml"


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
    assert rename_map == {"Area/Sex": "area_sex", "c.id": "citizenship_id"}
    assert unmapped == ["Total"]


def test_normalize_casing_fixes_real_arghakhanchi_finding():
    # This is the actual real-world case found in Phase 1:
    # two ODN datasets, same district, different casing.
    a = normalize_casing("Arghakhanchi")
    b = normalize_casing("ARGHAKHANCHI")
    assert a == b == "arghakhanchi"


def test_devanagari_and_date_normalizers_not_yet_implemented():
    # Deliberately still unimplemented — these tests document that fact
    # rather than pretending it's done.
    with pytest.raises(NotImplementedError):
        normalize_devanagari_digits("९८४१२३४५६७")
    with pytest.raises(NotImplementedError):
        normalize_date("10/06/2079")


class TestValueResolver:
    @pytest.fixture
    def resolver(self):
        """Load the real values.yaml from the package root."""
        registry_path = Path(__file__).parent.parent / "values.yaml"
        return ValueResolver(registry_path)

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
