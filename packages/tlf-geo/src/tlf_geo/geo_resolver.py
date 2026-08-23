from unicodedata import name

import numpy as np
import re
import yaml
from pathlib import Path
from rapidfuzz import process, fuzz
import pandas as pd

from .exceptions import NotFoundError, FuzzyMatchError, AmbiguityError
# ^ adjust this import to match your real folder layout if exceptions.py
#   isn't a sibling of this file inside the tlf_geo package


_MODULE_DIR = Path(__file__).parent
_DATA_DIR = _MODULE_DIR / "data"
_PLACES_PATH = _DATA_DIR / "places.yaml"
_CODES_PATH = _DATA_DIR / "codes.yaml"


def _normalize(text):
    """Lowercase and collapse whitespace. Used as the base cleaning step
    before any lookup — exact, suffix-stripped, or fuzzy."""
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)  # collapse multiple spaces/tabs into one
    return text


_SUFFIXES = [
    # English — order matters: longer/more-specific phrases first,
    # so "rural municipality" is stripped before a shorter partial match could interfere
    "sub-metropolitan city",
    "sub metropolitan city",
    "metropolitan city",
    "rural municipality",
    "municipality",
    "gaunpalika",
    "nagarpalika",
    # Nepali
    "उपमहानगरपालिका",
    "महानगरपालिका",
    "गाउँपालिका",
    "नगरपालिका",
]


def _strip_suffix(normalized_text):
    """Remove a known level-suffix (gaunpalika, nagarpalika, etc.) from an
    already-normalized string, if one is present at the end. Returns the
    stripped text, or the original unchanged if no suffix matched."""
    for suffix in _SUFFIXES:
        if normalized_text.endswith(suffix):
            # slice off the suffix, then strip any trailing space left behind
            # e.g. "kalika gaunpalika" -> "kalika "  -> "kalika"
            stripped = normalized_text[: -len(suffix)].strip()
            if stripped:  # don't return an empty string if input was JUST the suffix
                return stripped
    return normalized_text  # no suffix found — return as-is, unchanged


def _build_places_index(places_data):
    """Build normalized_alias -> [(level, canonical_key), ...] from places.yaml.
    Every alias string (English + Nepali) for every place maps here.
    Uses a LIST of candidates (not a single value) because the same bare
    alias can legitimately belong to more than one place across different
    levels (e.g. "Kalika" exists as both a gaunpalika and a municipality) —
    setdefault + append preserves every match instead of silently
    overwriting earlier ones."""
    index = {}
    for level, entries in places_data.items():
        for canonical_key, aliases in entries.items():
            for alias in aliases:
                key = _normalize(alias)
                index.setdefault(key, []).append((level, canonical_key))
    return index


def _build_district_name_index(codes_data):
    """normalized district name -> district_code (int).
    Built from codes.yaml's districts section only, using BOTH the English
    `name` and Nepali `name_ne` fields, so a query in either language resolves.
    No collision handling needed here — each district code has exactly one
    English name and one Nepali name, so there's nothing to accumulate."""
    index = {}
    for district_code, info in codes_data["districts"].items():
        index[_normalize(info["name"])] = district_code
        index[_normalize(info["name_ne"])] = district_code
    return index


class GeoResolver:
    def __init__(self):
        # load both YAML files from disk, anchored to this module's location
        # (not the caller's current working directory) so this works
        # correctly once tlf-geo is pip-installed, regardless of where
        # the caller runs their own code from
        with open(_PLACES_PATH, encoding="utf-8") as f:
            places_data = yaml.safe_load(f)

        with open(_CODES_PATH, encoding="utf-8") as f:
            codes_data = yaml.safe_load(f)

        # build the indexes we designed and tested individually
        self._places_index = _build_places_index(places_data)
        self._district_name_index = _build_district_name_index(codes_data)

        # no builder needed — codes.yaml already keys districts by code directly
        self._districts = codes_data["districts"]

        # keep references to the raw loaded data too — resolve() and other
        # methods (provinces(), local_levels(), etc.) will need to look things
        # up directly from local_levels/provinces/_by_canonical/protected_areas
        # sections that we haven't built dedicated indexes for yet
        self._codes_data = codes_data
        self._places_data = places_data
        # __init__ ends here — nothing else should be nested inside it

    def _candidate_matches_district(self, level, canonical_key, district_code):
        """Check codes_data['_by_canonical'][level][canonical_key] to see if
       this candidate has an entry in the given district_code. Returns the
       matching entry (dict with code/district/district_code) if found,
       or None if this candidate doesn't exist in that district."""

        by_canonical = self._codes_data.get("_by_canonical", {})
        entries = by_canonical.get(level, {}).get(canonical_key, [])

        for entry in entries:
            if entry["district_code"] == district_code:
                return entry

        return None

    def _get_candidates(self, name):
        """Look up a raw place name and return a list of (level, canonical_key)
        candidates. Tries exact match first, then suffix-stripped match,
        then falls back to fuzzy matching. Raises FuzzyMatchError if no exact
        match exists (but similar names were found), or NotFoundError if even
        fuzzy matching finds nothing."""

        normalized = _normalize(name)

        # Tier 1: exact match
        candidates = self._places_index.get(normalized)
        if candidates:
            return candidates

        # Tier 2: suffix-stripped match
        # only worth trying if stripping actually changed something —
        # otherwise it's the same lookup we already tried in Tier 1
        stripped = _strip_suffix(normalized)
        if stripped != normalized:
            candidates = self._places_index.get(stripped)
            if candidates:
                return candidates

        # Tier 3: fuzzy match against every known key in the index
        all_keys = list(self._places_index.keys())
        matches = process.extract(
            normalized, all_keys, scorer=fuzz.ratio, limit=3)
        # matches is a list of (matched_key, score, index_in_list) tuples

        if not matches:
            raise NotFoundError(name)

        suggestions = [(matched_key, score)
                       for matched_key, score, _ in matches]
        raise FuzzyMatchError(name, suggestions)

    def resolve(self, name, district=None, district_code=None, level=None):
        """Resolve a place name to its full metadata. Optionally narrow down
        ambiguous matches using district (name), district_code, or level.
      Raises AmbiguityError if multiple candidates remain after filtering,
      NotFoundError/FuzzyMatchError if the name itself doesn't match anything."""

    # Step 1: get raw name-based candidates — may already raise
    # FuzzyMatchError or NotFoundError if the name itself doesn't match
        candidates = self._get_candidates(name)

    # Step 2: resolve a district name into a district_code, if one was given
    # (district_code takes priority if the caller passed both — it's unambiguous)
        if district_code is None and district is not None:
            district_code = self._district_name_index.get(_normalize(district))

    # Step 3: filter candidates by level, if specified
        if level is not None:
            candidates = [c for c in candidates if c[0] == level]

    # Step 4: filter candidates by district, if we have a district_code
    # (either passed directly, or resolved from a district name above)
        resolved_entries = []
        if district_code is not None:
            for cand_level, canonical_key in candidates:
                entry = self._candidate_matches_district(
                    cand_level, canonical_key, district_code)
                if entry is not None:
                    resolved_entries.append((cand_level, canonical_key, entry))
        else:
            # no district filter given — every candidate could still be a match,
            # so pull its full metadata directly from local_levels using its code,
            # rather than only from _by_canonical (we don't have a district to check against)
            for cand_level, canonical_key in candidates:
                entries = self._codes_data.get("_by_canonical", {}).get(
                    cand_level, {}).get(canonical_key, [])
                for entry in entries:
                    resolved_entries.append((cand_level, canonical_key, entry))

    # Step 5: decide what to return based on how many entries survived
        if len(resolved_entries) == 1:
            cand_level, canonical_key, entry = resolved_entries[0]
            return self._build_result(cand_level, canonical_key, entry)

        if len(resolved_entries) == 0:
            # name matched something, but the district/level filter eliminated
            # everything — this is the "invalid_district" case from your design
            raise NotFoundError(name, district=district, level=level)

    # more than one entry survived — genuinely ambiguous, even after filtering
        full_candidates = [
            self._build_result(cand_level, canonical_key, entry)
            for cand_level, canonical_key, entry in resolved_entries
        ]
        raise AmbiguityError(name, full_candidates)

    def _build_result(self, level, canonical_key, entry):
        """Build the final result dict for a single resolved place, pulling
      full metadata (name, name_ne, wards, etc.) from local_levels using
      the code found in the _by_canonical entry."""
        code = entry["code"]
        metadata = self._codes_data["local_levels"][code]
        return {
            "code": code,
            "canonical_key": canonical_key,
            "level": level,
            "name": metadata["name"],
            "name_ne": metadata["name_ne"],
            "district": metadata["district"],
            "district_code": metadata["district_code"],
            "province_code": metadata["province_code"],
            "wards": metadata["wards"],
        }

    import pandas as pd

    def resolve_df(self, df, name_col='place_name', name_ne_col=None,
                   district_col=None, district_code_col=None, level_col=None):
        """Batch-resolve a DataFrame of place names. Returns a NEW DataFrame
       (original untouched) with geo_* columns added — one row per input row,
       NaN-filled for anything that couldn't be cleanly resolved, with the
       reason recorded in geo_error_reason for later review."""

        result_df = df.copy()  # never mutate the caller's original DataFrame

    # columns we'll be filling in, one per row
        geo_codes, geo_names, geo_names_ne, geo_levels = [], [], [], []
        geo_canonical_keys, geo_districts, geo_district_codes = [], [], []
        geo_province_codes, geo_wards = [], []
        geo_statuses, geo_error_reasons = [], []

        for idx, row in df.iterrows():
            name = row[name_col]
            district = row[district_col] if district_col and pd.notna(
                row[district_col]) else None
            district_code = row[district_code_col] if district_code_col and pd.notna(
                row[district_code_col]) else None
            level = row[level_col] if level_col and pd.notna(
                row[level_col]) else None
            try:
                result = self.resolve(name, district=district,
                                      district_code=district_code, level=level)

                # success — fill everything from the resolved dict
                geo_codes.append(result["code"])
                geo_names.append(result["name"])
                geo_names_ne.append(result["name_ne"])
                geo_levels.append(result["level"])
                geo_canonical_keys.append(result["canonical_key"])
                geo_districts.append(result["district"])
                geo_district_codes.append(result["district_code"])
                geo_province_codes.append(result["province_code"])
                geo_wards.append(result["wards"])
                geo_statuses.append("resolved")
                geo_error_reasons.append(None)

            except AmbiguityError as e:
                self._fill_nan_row(geo_codes, geo_names, geo_names_ne, geo_levels,
                                   geo_canonical_keys, geo_districts, geo_district_codes,
                                   geo_province_codes, geo_wards)
                geo_statuses.append("ambiguous")
                geo_error_reasons.append(self._describe_ambiguity(e))

            except FuzzyMatchError as e:
                self._fill_nan_row(geo_codes, geo_names, geo_names_ne, geo_levels,
                                   geo_canonical_keys, geo_districts, geo_district_codes,
                                   geo_province_codes, geo_wards)
                geo_statuses.append("not_found")
                geo_error_reasons.append(self._describe_fuzzy(e))

            except NotFoundError as e:
                self._fill_nan_row(geo_codes, geo_names, geo_names_ne, geo_levels,
                                   geo_canonical_keys, geo_districts, geo_district_codes,
                                   geo_province_codes, geo_wards)
                status = "invalid_district" if e.district else "not_found"
                geo_statuses.append(status)
                geo_error_reasons.append(str(e))

        result_df["geo_code"] = geo_codes
        result_df["geo_name"] = geo_names
        result_df["geo_name_ne"] = geo_names_ne
        result_df["geo_level"] = geo_levels
        result_df["geo_canonical_key"] = geo_canonical_keys
        result_df["geo_district"] = geo_districts
        result_df["geo_district_code"] = geo_district_codes
        result_df["geo_province_code"] = geo_province_codes
        result_df["geo_wards"] = geo_wards
        result_df["geo_status"] = geo_statuses
        result_df["geo_error_reason"] = geo_error_reasons

        return result_df

    def _fill_nan_row(self, *lists):
        """Append NaN to every column-list passed in — used when a row
       couldn't be resolved, so every geo_* value column stays aligned
       (same length) even though this row has nothing real to put there."""
        for lst in lists:
            lst.append(np.nan)

    def _describe_ambiguity(self, e):
        """Turn an AmbiguityError's candidates into one readable string
       for the geo_error_reason column."""
        parts = [f"{c['level']} in {c['district']}" for c in e.candidates]
        return f"Ambiguous ({len(e.candidates)}): " + "; ".join(parts)

    def _describe_fuzzy(self, e):
        """Turn a FuzzyMatchError's suggestions into one readable string."""
        parts = [f"{name} ({score:.0f}%)" for name, score in e.candidates]
        return "No exact match. Did you mean: " + ", ".join(parts)

    def provinces(self, as_dict=False):
        """Return all provinces as a DataFrame: code, canonical_key, name, name_ne."""
        rows = []
        for code, info in self._codes_data["provinces"].items():
            rows.append({
                "code": code,
                "canonical_key": info["canonical_key"],
                "name": info["name"],
                "name_ne": info["name_ne"],
            })
        return self._maybe_dict(pd.DataFrame(rows), as_dict)

    def districts(self, province=None, province_code=None, as_dict=False):
        """Return districts as a DataFrame, optionally filtered to one province
         (by name, name_ne, or canonical_key — province_code takes priority if
         both are given). If a province name is given but doesn't match anything,
         returns an EMPTY DataFrame rather than silently returning all districts."""

        if province_code is None and province is not None:
            normalized = _normalize(province)
            matched = False
            for code, info in self._codes_data["provinces"].items():
                if (normalized == info["canonical_key"]
                        or _normalize(info["name"]) == normalized
                        or _normalize(info["name_ne"]) == normalized):
                    province_code = code
                    matched = True
                    break

            if not matched:
                return self._maybe_dict(pd.DataFrame(), as_dict)

        rows = []
        for code, info in self._codes_data["districts"].items():
            if province_code is not None and info["province_code"] != province_code:
                continue
            rows.append({
                "code": code,
                "canonical_key": info["canonical_key"],
                "name": info["name"],
                "name_ne": info["name_ne"],
                "province_code": info["province_code"],
            })
        return self._maybe_dict(pd.DataFrame(rows), as_dict)

    def local_levels(self, level=None, district=None, district_code=None,
                     province_code=None, as_dict=False):
        """Return local levels (gaunpalika/municipality/etc.) as a DataFrame,
      optionally filtered by level, district (name or code), or province."""
        if district_code is None and district is not None:
            district_code = self._district_name_index.get(_normalize(district))

        rows = []
        for code, info in self._codes_data["local_levels"].items():
            if level is not None and info["level"] != level:
                continue
            if district_code is not None and info["district_code"] != district_code:
                continue
            if province_code is not None and info["province_code"] != province_code:
                continue
            rows.append({
                "code": code,
                "canonical_key": info["canonical_key"],
                "level": info["level"],
                "name": info["name"],
                "name_ne": info["name_ne"],
                "district": info["district"],
                "district_code": info["district_code"],
                "province_code": info["province_code"],
                "wards": info["wards"],
            })
        return self._maybe_dict(pd.DataFrame(rows), as_dict)

    def protected_areas(self, as_dict=False):
        """Return all protected areas as a DataFrame."""
        return self._maybe_dict(
            pd.DataFrame(self._codes_data.get("protected_areas", [])), as_dict
        )

    def get_by_code(self, code):
        """Look up full metadata for a code — works for local_level, district,
       or province codes. Returns None if the code isn't recognized (never
       raises), so this is safe to use inside df["col"].apply(resolver.get_by_code)
       across a whole column, even with messy/invalid values mixed in."""

        if pd.isna(code):
            return None

        code_str = str(code).strip()

    # try local_level first — codes there are 5-digit strings like "32902"
        if code_str in self._codes_data["local_levels"]:
            return self._codes_data["local_levels"][code_str]

    # try district — codes are small ints, keys in self._districts
        try:
            code_int = int(code_str)
        except ValueError:
            return None  # not a valid number at all — genuinely unrecognized

        if code_int in self._districts:
            return self._districts[code_int]

    # try province
        if code_int in self._codes_data["provinces"]:
            return self._codes_data["provinces"][code_int]

        return None  # tried all three, nothing matched

    def get_name(self, code, lang="en"):
        """Return just the display name for a code, in English or Nepali.
       Returns None if the code isn't recognized."""
        info = self.get_by_code(code)
        if info is None:
            return None
        return info["name_ne"] if lang == "ne" else info["name"]

    def get_canonical(self, code):
        """Return just the canonical_key for a code. Returns None if unrecognized."""
        info = self.get_by_code(code)
        if info is None:
            return None
        return info["canonical_key"]

    def get_wards(self, code):
        """Return the ward count for a local_level code. Returns None if
       unrecognized, or if this code is a district/province (which has
       no wards field at all)."""
        info = self.get_by_code(code)
        if info is None:
            return None
    # .get(), not [...] — districts/provinces don't have this key
        return info.get("wards")

    def get_parent(self, code):
        """Return the parent hierarchy for a code: district_code and
       province_code for a local_level, or just province_code for a
       district. Returns None if the code isn't recognized."""
        info = self.get_by_code(code)
        if info is None:
            return None

        parent = {}
        if "district_code" in info:
            parent["district_code"] = info["district_code"]
        if "province_code" in info:
            parent["province_code"] = info["province_code"]
        return parent

    def is_valid_code(self, code):
        """True if this code resolves to a real place (local_level, district,
       or province). False otherwise. Safe for .apply() across a column."""
        return self.get_by_code(code) is not None

    def is_valid_name(self, name):
        """True if this name has at least one real exact/suffix-stripped
      match in places.yaml — ambiguous still counts as valid, since it
      matched something real. False if it only fuzzy-matches (a typo
      guess) or doesn't match anything at all."""
        if pd.isna(name):
            return False
        try:
            self._get_candidates(name)
            return True
        except (FuzzyMatchError, NotFoundError):
            return False

    def to_choices(self, level, province_code=None, district_code=None):
        """Return [(code, name), ...] tuples for Django ChoiceField, built
       from provinces()/districts()/local_levels() depending on `level`."""

        if level == "province":
            df = self.provinces()
        elif level == "district":
            df = self.districts(province_code=province_code)
        elif level == "local_level":
            df = self.local_levels(district_code=district_code)
        else:
            raise ValueError(f"Unknown level: {level!r}")

        return list(zip(df["code"], df["name"]))

    def search(self, name, limit=5):
        """Non-raising lookup for interactive use (autocomplete, "did you mean").
       Returns a list of (label, score) pairs, best first. label is
       "canonical_key (level)" so genuinely distinct places sharing a bare
       name (e.g. Kalika gaunpalika vs. Kalika municipality) aren't collapsed
       into one entry. score is 100.0 for an exact/suffix-stripped match, or
       the fuzzy match score (0-100) otherwise. Never raises — returns an
       empty list if nothing matches at all."""
        try:
            candidates = self._get_candidates(name)
        except FuzzyMatchError as e:
            return e.candidates[:limit]
        except NotFoundError:
            return []

    # exact/suffix-stripped tiers return (level, canonical_key) pairs, not
    # (label, score) — normalize the shape so search()'s return type is
    # consistent regardless of which tier matched
        return [
            (f"{canonical_key} ({level})", 100.0)
            for level, canonical_key in candidates
        ][:limit]

    @staticmethod
    def _maybe_dict(df, as_dict):
        """Convert a DataFrame to a list of dictionaries if as_dict is True, otherwise return the DataFrame."""
        return df.to_dict(orient="records") if as_dict else df
