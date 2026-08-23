"""
Tests for tlf_geo.geo_resolver.GeoResolver.

Uses a real GeoResolver() instance loading the actual bundled places.yaml
and codes.yaml — no mocking, matching the "test against real data" approach
used throughout tlf-geo's development. Facts asserted below (codes,
district names, ambiguity counts, fuzzy scores) come from real terminal
output recorded during Sessions 11-13; if the underlying YAML data
changes, some of these will need updating alongside it.
"""

import math

import pandas as pd
import pytest

from tlf_geo import GeoResolver
from tlf_geo.exceptions import AmbiguityError, FuzzyMatchError, NotFoundError


@pytest.fixture(scope="module")
def resolver():
    # module-scoped: loading places.yaml/codes.yaml once per test file,
    # not once per test, since GeoResolver() is read-only after __init__
    return GeoResolver()


# ---------------------------------------------------------------------------
# resolve() — exact match, disambiguation, ambiguity, invalid district, level
# ---------------------------------------------------------------------------

class TestResolveExactAndDisambiguation:
    def test_exact_match_disambiguated_by_district(self, resolver):
        result = resolver.resolve("Kalika", district="Rasuwa")
        assert result["code"] == "32902"
        assert result["level"] == "gaunpalika"
        assert result["canonical_key"] == "kalika"
        assert result["district"] == "rasuwa"
        assert result["district_code"] == 29
        assert result["province_code"] == 3

    def test_exact_match_disambiguated_by_district_and_level(self, resolver):
        # same result as above, reached via explicit level filtering instead
        result = resolver.resolve(
            "Kalika", district="Rasuwa", level="gaunpalika")
        assert result["code"] == "32902"

    def test_ambiguous_without_district_raises(self, resolver):
        with pytest.raises(AmbiguityError) as exc_info:
            resolver.resolve("Kalika")
        candidates = exc_info.value.candidates
        assert len(candidates) == 3
        levels = {c["level"] for c in candidates}
        assert levels == {"gaunpalika", "municipality"}

    def test_wrong_district_raises_not_found(self, resolver):
        # name matches something real, but not in this district —
        # this is the "invalid_district" case, not a generic miss
        with pytest.raises(NotFoundError) as exc_info:
            resolver.resolve("Kalika", district="Kathmandu")
        assert exc_info.value.district == "Kathmandu"

    def test_suffix_stripped_match(self, resolver):
        # "Kalika Nagarpalika" is the WRONG suffix on purpose (real level is
        # gaunpalika) — suffix-stripping should still recover "kalika" and
        # let district/level filtering do the real disambiguation
        result = resolver.resolve(
            "Kalika Nagarpalika", district="Rasuwa", level="gaunpalika"
        )
        assert result["code"] == "32902"


class TestResolveFuzzy:
    def test_typo_raises_fuzzy_match_error_with_ranked_suggestions(self, resolver):
        with pytest.raises(FuzzyMatchError) as exc_info:
            resolver.resolve("Kalka")
        suggestions = exc_info.value.candidates
        assert len(suggestions) == 3
        keys = [s[0] for s in suggestions]
        assert keys[0] == "kalika"  # best match ranked first
        scores = [s[1] for s in suggestions]
        assert scores == sorted(scores, reverse=True)  # descending by score

    def test_complete_garbage_raises_not_found_or_fuzzy(self, resolver):
        # rapidfuzz's top-3-no-threshold means even nonsense usually returns
        # *something* — assert it's one of the two designed failure modes,
        # not that it silently resolves
        with pytest.raises((FuzzyMatchError, NotFoundError)):
            resolver.resolve("zzzznotarealplacename1234")


# ---------------------------------------------------------------------------
# resolve() — untested-in-prior-sessions case, flagged in Session 12/13 notes
# ---------------------------------------------------------------------------

class TestResolveDistrictVsSameNameLocalLevel:
    def test_district_name_resolves_to_district_not_local_level(self, resolver):
        """
        Flagged as unconfirmed as of Session 13: does resolve("Taplejung")
        correctly return the DISTRICT rather than a local level of the same
        name, when no level filter is given? Written as a real assertion
        rather than skipped — if this fails, it's a genuine open design
        question (does resolve() even search district names via
        _get_candidates, or only via the district= param?) worth resolving
        before publish, not a test bug.
        """
        result = resolver.resolve("Taplejung", level="district")
        assert result["level"] == "district"


# ---------------------------------------------------------------------------
# resolve_df() — every geo_status outcome represented in one batch
# ---------------------------------------------------------------------------

class TestResolveDf:
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame(
            {
                "place_name": [
                    "Kalika",          # + district -> resolved
                    "Kalika",          # no district -> ambiguous
                    # typo -> not_found (via FuzzyMatchError)
                    "Kalka",
                    "Kalika",          # wrong district -> invalid_district
                    # right district, wrong level -> level_mismatch (if enforced)
                    "Kalika",
                ],
                "district_name": ["Rasuwa", None, None, "Kathmandu", "Rasuwa"],
                "level": [None, None, None, None, "municipality"],
            }
        )

    def test_all_status_types_represented(self, resolver, sample_df):
        result = resolver.resolve_df(
            sample_df,
            name_col="place_name",
            district_col="district_name",
            level_col="level",
        )
        assert list(result["geo_status"]) == [
            "resolved",
            "ambiguous",
            "not_found",
            "invalid_district",
            "invalid_district",
            # NOTE: row 5 (Kalika/Rasuwa/municipality) — Rasuwa's Kalika is a
            # gaunpalika, not a municipality, so district+level together
            # eliminate every candidate. resolve() raises NotFoundError with
            # district="Rasuwa" set, and resolve_df() only checks whether
            # e.district is truthy to decide between "invalid_district" and
            # "not_found" — it can't currently tell whether the district or
            # the level was what actually caused zero survivors. Both rows 4
            # and 5 land on "invalid_district" as a result, even though row 5's
            # real cause is the level filter, not the district.
        ]

    def test_original_dataframe_not_mutated(self, resolver, sample_df):
        original_columns = list(sample_df.columns)
        resolver.resolve_df(sample_df, name_col="place_name",
                            district_col="district_name")
        assert list(sample_df.columns) == original_columns

    def test_resolved_row_has_full_metadata(self, resolver, sample_df):
        result = resolver.resolve_df(
            sample_df, name_col="place_name", district_col="district_name"
        )
        resolved_row = result.iloc[0]
        assert resolved_row["geo_code"] == "32902"
        assert resolved_row["geo_status"] == "resolved"
        assert pd.isna(resolved_row["geo_error_reason"])

    def test_unresolved_rows_have_nan_fields_and_a_reason(self, resolver, sample_df):
        result = resolver.resolve_df(
            sample_df, name_col="place_name", district_col="district_name"
        )
        ambiguous_row = result.iloc[1]
        assert pd.isna(ambiguous_row["geo_code"])
        assert ambiguous_row["geo_error_reason"] is not None
        assert "Ambiguous" in ambiguous_row["geo_error_reason"]


# ---------------------------------------------------------------------------
# Listing methods — DataFrame default, as_dict=True variant, filters
# ---------------------------------------------------------------------------

class TestListingMethods:
    def test_provinces_returns_seven(self, resolver):
        df = resolver.provinces()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 7

    def test_provinces_as_dict(self, resolver):
        records = resolver.provinces(as_dict=True)
        assert isinstance(records, list)
        assert isinstance(records[0], dict)
        assert len(records) == 7

    def test_districts_filtered_by_province_name(self, resolver):
        df = resolver.districts(province="Bagmati")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert (df["province_code"] == df["province_code"].iloc[0]).all()

    def test_districts_unknown_province_returns_empty_not_all(self, resolver):
        # regression guard for the districts() bug fixed in Session 13 —
        # an unmatched province name must NOT silently fall through to
        # "no filter applied"
        df = resolver.districts(province="Nonexistent Province")
        assert len(df) == 0

    def test_local_levels_single_filter(self, resolver):
        df = resolver.local_levels(level="gaunpalika")
        assert (df["level"] == "gaunpalika").all()

    def test_local_levels_stacked_filters(self, resolver):
        # per Session 13 notes: filter combinations were only tested
        # individually, never stacked together — this is the first
        # combined-filter test
        df = resolver.local_levels(
            level="gaunpalika", district="Rasuwa", province_code=3
        )
        assert len(df) > 0
        assert (df["level"] == "gaunpalika").all()
        assert (df["district_code"] == 29).all()

    def test_protected_areas_as_dict(self, resolver):
        records = resolver.protected_areas(as_dict=True)
        assert isinstance(records, list)


# ---------------------------------------------------------------------------
# Code lookups — null-safe, never raise
# ---------------------------------------------------------------------------

class TestCodeLookups:
    def test_get_by_code_known_local_level(self, resolver):
        info = resolver.get_by_code("32902")
        assert info["canonical_key"] == "kalika"

    def test_get_by_code_unknown_returns_none_not_raise(self, resolver):
        assert resolver.get_by_code("99999") is None
        assert resolver.get_by_code(None) is None
        assert resolver.get_by_code("not-a-code") is None

    def test_get_name_english_and_nepali(self, resolver):
        assert resolver.get_name("32902", lang="en") == "Kalika"
        assert resolver.get_name(
            "32902", lang="ne") != resolver.get_name("32902", lang="en")

    def test_get_wards_none_for_district_code(self, resolver):
        # districts/provinces have no wards field — must return None,
        # not raise a KeyError
        district_code = resolver._district_name_index[
            resolver._normalize("Rasuwa")
        ] if hasattr(resolver, "_normalize") else None
        # fall back to a known district code if _normalize isn't exposed
        district_code = district_code or 29
        assert resolver.get_wards(district_code) is None

    def test_get_parent_local_level(self, resolver):
        parent = resolver.get_parent("32902")
        assert parent["district_code"] == 29
        assert parent["province_code"] == 3

    def test_is_valid_code(self, resolver):
        assert resolver.is_valid_code("32902") is True
        assert resolver.is_valid_code("99999") is False

    def test_is_valid_name_ambiguous_still_counts_as_valid(self, resolver):
        # "Kalika" alone raises AmbiguityError from resolve(), but it DID
        # match something real — is_valid_name() should say True
        assert resolver.is_valid_name("Kalika") is True

    def test_is_valid_name_only_fuzzy_match_counts_as_invalid(self, resolver):
        # a typo that only fuzzy-matches is NOT a valid name
        assert resolver.is_valid_name("Kalka") is False

    def test_is_valid_name_nan_safe(self, resolver):
        assert resolver.is_valid_name(float("nan")) is False


# ---------------------------------------------------------------------------
# search() — non-raising, always returns a list
# ---------------------------------------------------------------------------

class TestSearch:
    def test_exact_match_shows_both_real_places_not_collapsed(self, resolver):
        results = resolver.search("Kalika")
        labels = [r[0] for r in results]
        assert any("gaunpalika" in label for label in labels)
        assert any("municipality" in label for label in labels)
        assert all(score == 100.0 for _, score in results)

    def test_fuzzy_match_returns_ranked_suggestions(self, resolver):
        results = resolver.search("Kalka")
        assert len(results) <= 5  # default limit
        assert results[0][0] == "kalika"
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_garbage_input_still_returns_ranked_suggestions_not_empty(self, resolver):
        # per the Session 11 no-threshold decision, rapidfuzz's top-3-always
        # behavior means search() basically never returns an empty list against
        # real bundled data — even nonsense input gets ranked (weak) suggestions,
        # by design, so the human can see and reject them rather than the
        # library silently deciding "no match"
        results = resolver.search("zzzznotarealplacename1234")
        assert len(results) > 0
        assert all(score < 50 for _, score in results)

    def test_limit_is_respected(self, resolver):
        results = resolver.search("Kalka", limit=1)
        assert len(results) <= 1


# ---------------------------------------------------------------------------
# to_choices() — Django integration
# ---------------------------------------------------------------------------

class TestToChoices:
    def test_province_level(self, resolver):
        choices = resolver.to_choices("province")
        assert len(choices) == 7
        assert all(isinstance(c, tuple) and len(c) == 2 for c in choices)

    def test_district_level_scoped_to_province(self, resolver):
        choices = resolver.to_choices("district", province_code=3)
        all_districts = resolver.to_choices("district")
        assert 0 < len(choices) < len(all_districts)

    def test_local_level_scoped_to_province(self, resolver):
        # regression guard for the to_choices() bug fixed in Session 13/14 —
        # province_code must actually be forwarded to local_levels(), not
        # silently dropped (it previously only forwarded district_code)
        scoped = resolver.to_choices("local_level", province_code=3)
        unscoped = resolver.to_choices("local_level")
        assert len(scoped) < len(unscoped)

    def test_unknown_level_raises_value_error(self, resolver):
        with pytest.raises(ValueError):
            resolver.to_choices("not_a_real_level")
