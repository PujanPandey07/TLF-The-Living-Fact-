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
