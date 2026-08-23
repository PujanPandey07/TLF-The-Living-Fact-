# tlf-geo

**One official code, however many ways someone spelled the place.**

`tlf-geo` resolves messy real-world Nepali place names — provinces,
districts, and all 753 local government units (gaunpalika, municipality,
sub-metropolitan city, metropolitan city) — to their official NSO codes,
handling spelling variants, script mixing (Roman/Devanagari), common
administrative-suffix noise, and the ~30 place names that legitimately exist
in more than one district.

Part of **TLF (The Living Fact)**, an initiative of Corpola Tech and the
Open Tech Community for making Nepal's civic and census data interoperable.
Full project story, data sources, and architecture reasoning: [github.com/PujanPandey07/TLF-The-Living-Fact-](https://github.com/PujanPandey07/TLF-The-Living-Fact-)

> **Status:** Alpha (v0.1.0). Built on real crosswalk data from Nepal's
> local-level code registry; see [Contributing](#contributing) for how to
> report a missing or incorrect place.

---

## Installation

```bash
pip install tlf-geo
```

---

## Quick start

```python
from tlf_geo import GeoResolver

resolver = GeoResolver()

# Resolve a place name, disambiguated by district
result = resolver.resolve("Kalika", district="Rasuwa")
# {
#   "code": "32902", "canonical_key": "kalika", "level": "gaunpalika",
#   "name": "Kalika", "name_ne": "कालिका गाउँपालिका",
#   "district": "rasuwa", "district_code": 29,
#   "province_code": 3, "wards": "5",
# }

# Same name without a district — genuinely ambiguous, raises instead of guessing
resolver.resolve("Kalika")
# -> AmbiguityError: 3 candidates (Rasuwa/gaunpalika, Kalikot/gaunpalika, Chitawan/municipality)
```

Resolving a whole DataFrame column at once, without letting one bad row kill
the batch:

```python
import pandas as pd

df = pd.read_csv("survey.csv")
resolved = resolver.resolve_df(
    df,
    name_col="place_name",
    district_col="district_name",
)
# adds `geo_status` (resolved / ambiguous / not_found / invalid_district /
# level_mismatch) and `geo_error_reason` columns, plus resolved code/name/
# level/etc. columns for rows that succeeded
```

---

## Why resolution can fail — and why that's on purpose

`resolve()` never guesses. If a name doesn't map cleanly to exactly one
place, it raises one of three exceptions instead of silently picking a
"probably right" answer:

| Exception         | Raised when                                                                                                | Carries                                                                                                         |
| ----------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `NotFoundError`   | No candidate matches at all, or a given `district`/`district_code` rules out every candidate for that name | A message describing what was searched                                                                          |
| `AmbiguityError`  | More than one real place matches (same name, multiple districts, no district given to disambiguate)        | Full candidate dicts, one per real place                                                                        |
| `FuzzyMatchError` | Nothing matched exactly or after suffix-stripping, so the name fell through to fuzzy matching              | Top 3 `(matched_key, score)` suggestions, no minimum-similarity cutoff — you decide what counts as close enough |

This mirrors `tlf-core`'s "never guess, never drop" rule: unresolved data
surfaces with enough information to resolve it by hand, rather than being
silently miscategorized.

---

## API Reference

Everything below is available from `from tlf_geo import GeoResolver` (the
exceptions are importable from `tlf_geo.exceptions` or the top-level
package).

### `GeoResolver()`

Loads the bundled `places.yaml` (alias/fuzzy data) and `codes.yaml`
(official codes + district disambiguation) — no arguments, no external
files needed.

---

### `resolver.resolve(name, district=None, district_code=None, level=None) -> dict`

Resolves one place name to a single official record.

- `district` (name string) or `district_code` narrows candidates to that
  district; if both are given, `district_code` takes priority.
- `level` (`"province"`, `"district"`, `"gaunpalika"`, `"municipality"`,
  `"sub_metropolitan_city"`, `"metropolitan_city"`) narrows candidates to
  that administrative level.
- Returns a dict: `code, canonical_key, level, name, name_ne, district,
district_code, province_code, wards`.
- Raises `NotFoundError`, `AmbiguityError`, or `FuzzyMatchError` — see
  above — if it can't resolve to exactly one place.

```python
resolver.resolve("Kalika", district="Rasuwa", level="gaunpalika")
resolver.resolve("Kalka")  # typo -> FuzzyMatchError, suggests kalika/kakani/malika
```

> **Note:** protected areas (national parks, wildlife reserves) are not
> resolvable by name through `resolve()` — that's a deliberate scope
> decision, not a bug. Use `protected_areas()` to list them instead.

---

### `resolver.search(name, limit=5) -> list[tuple[str, float]]`

The non-raising sibling of `resolve()`, meant for interactive use —
autocomplete, a "did you mean...?" prompt, a search box — where you want to
_see options_, not get exactly one answer or an exception.

Runs the same 3-tier lookup as `resolve()`, but always returns a list of
`(label, score)` pairs instead of raising:

- An exact/suffix-stripped match returns `"canonical_key (level)"` labels
  at a score of `100.0` — genuinely distinct places sharing a bare name
  (e.g. Kalika gaunpalika vs. Kalika municipality) show up as separate
  entries rather than being collapsed into one.
- A fuzzy match returns the same `(matched_key, score)` suggestions
  `FuzzyMatchError` would have carried, just returned instead of raised.
- No match at all returns `[]`.

`search()` never filters by district or level the way `resolve()` does —
it's purely "what places even loosely match this string."

```python
resolver.search("Kalika")
# [("kalika (gaunpalika)", 100.0), ("kalika (municipality)", 100.0)]

resolver.search("Kalka")   # typo
# [("kalika", 91.0), ("kakani", 73.0), ("malika", 73.0)]

resolver.search("zzzznotaplace")
# []
```

---

### `resolver.resolve_df(df, name_col, name_ne_col=None, district_col=None, district_code_col=None, level_col=None) -> DataFrame`

Batch version of `resolve()` for a whole DataFrame. Never raises — every
row's outcome is captured instead of stopping the batch:

| `geo_status`       | Meaning                                                     |
| ------------------ | ----------------------------------------------------------- |
| `resolved`         | Matched exactly one place; resolved fields filled in        |
| `ambiguous`        | Multiple real candidates, no district given to disambiguate |
| `not_found`        | No candidate matched at all                                 |
| `invalid_district` | Name matched, but not in the given district                 |
| `level_mismatch`   | Name matched, but not at the given level                    |

Rows that don't resolve get their resolved-field columns left blank and a
human-readable `geo_error_reason` instead of raising.

---

### Listing & filtering — return pandas DataFrames by default

Every listing method takes an `as_dict=False` param — pass `as_dict=True`
to get a plain `list[dict]` back instead of a DataFrame, for callers who
aren't otherwise using pandas (a script, a JSON API response).

| Function                                                                                                  | Returns                                                                                           |
| --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `resolver.provinces(as_dict=False)`                                                                       | All 7 provinces                                                                                   |
| `resolver.districts(province=None, province_code=None, as_dict=False)`                                    | All districts, optionally filtered by province                                                    |
| `resolver.local_levels(level=None, district=None, district_code=None, province_code=None, as_dict=False)` | Local government units, filterable by level, district, and/or province                            |
| `resolver.protected_areas(as_dict=False)`                                                                 | National parks, wildlife reserves, etc. — the listing method, not name-resolvable via `resolve()` |

```python
resolver.provinces(as_dict=True)
# [{"code": 1, "canonical_key": "koshi", "name": "Koshi", "name_ne": "कोशी"}, ...]
```

---

### Code lookups — null-safe, `.apply()`-safe, never raise

| Function                       | Does                              |
| ------------------------------ | --------------------------------- |
| `resolver.get_by_code(code)`   | Full record for an official code  |
| `resolver.get_name(code)`      | Canonical English name for a code |
| `resolver.get_canonical(code)` | Canonical key for a code          |
| `resolver.get_wards(code)`     | Ward count for a local level      |
| `resolver.get_parent(code)`    | Parent district/province code     |

Each is safe to call directly inside `df["code"].apply(resolver.get_name)` —
unknown codes return `None` rather than raising.

---

### Validation

- **`resolver.is_valid_code(code) -> bool`**
- **`resolver.is_valid_name(name) -> bool`**

---

### Django integration

**`resolver.to_choices(level, province_code=None, district_code=None) -> list[tuple[str, str]]`**

Returns `(code, name)` pairs ready for a Django `ChoiceField`/model field's
`choices=`, optionally scoped to a province or district.

```python
# models.py
district_code = models.CharField(
    max_length=5,
    choices=resolver.to_choices("municipality", province_code=3),
)
```

---

## What this does NOT do

- No name-based resolution of protected areas (listing via
  `protected_areas()` works fine — `resolve()` by name doesn't)
- No fuzzy match cutoff — `FuzzyMatchError`'s top-3 suggestions are always
  returned, however weak, so you judge what's close enough
- No BS↔AD calendar handling or general value normalization — that's
  `tlf-core`'s job, not this package's

---

## Contributing

`places.yaml` and `codes.yaml` are built from Nepal's official local-level
code crosswalk. If you find a place that doesn't resolve, resolves
incorrectly, or is missing an alias:

1. [Open an issue](https://github.com/PujanPandey07/TLF-The-Living-Fact-/issues)
   with the raw name, the district it belongs to, and what you expected —
   or
2. Clone this repo, add the alias/entry directly to `places.yaml` (and
   `codes.yaml` if it's a new place rather than a spelling variant), and
   open a PR.

For the project's background, data sources, and architecture decisions, see
the [main repo](https://github.com/PujanPandey07/TLF-The-Living-Fact-).

---

## License

MIT
