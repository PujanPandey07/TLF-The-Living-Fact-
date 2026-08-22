# Decisions Log

Dated, short entries. Each one records a real decision made and why — not a
design doc, just enough for future-us to understand a choice without
re-deriving it.

Format:

```
## YYYY-MM-DD — short title
Decision: ...
Why: ...
Alternatives considered: ...
```

---

## 2026-08-02 — Monorepo over per-package repos (for now)

Decision: build `tlf-core` and the `tlf-collect-*` packages inside one
monorepo (`packages/`) instead of separate GitHub repos per package.

Why: package boundaries are still being figured out; moving code between
packages is much cheaper inside one repo than across repos. Will split into
independent repos under `ctpl-git` once each package's scope is stable enough
to publish and depend on independently.

Alternatives considered: one repo per package from day one (matches the
existing 5 TLF repos' pattern, but adds overhead while boundaries are still
fuzzy).

---

## 2026-08-02 — Interoperability approach: crosswalk registry + entity resolution

Decision: solve within-domain field-naming mismatches (e.g. `c.id` vs `c_no`
vs `citizenship_number`) with a versioned alias registry (`fields.yaml` +
resolver) living in `tlf-core`. Solve cross-domain joins (e.g. education +
health data joined on ward) separately, later, with entity-resolution
techniques (starting manual, moving to a library like `recordlinkage` only if
alias/exact matching proves insufficient).

Why: these are genuinely different problems (schema mapping vs. entity
resolution) with different standard solutions; conflating them into one
mechanism would make both harder to reason about.

---

## 2026-08-02 — Phase 1 complete: confirmed real data-quality problems

Decision: treat Phase 1 (manual exploration, no code) as done after finding
four distinct, independently-sourced consistency problems: casing
(Open Data Nepal), language (Bharatpur ward profiles), numeral system
(Pokhara staff directory), and date format/calendar system (BS vs AD, mixed
formats). See `docs/data_quality_checklist.md` for full detail and the two
unexplored dimensions (completeness, validity) flagged for later.

Why stop here rather than searching further: four distinct problem types
from independent sources is enough diversity to build Phase 2/3
against with confidence; further searching would likely surface variations
of the same buckets rather than new categories, with diminishing
returns relative to just starting to build.

Note: the date/calendar finding (BS vs AD) is the most Nepal-specific and
technically hardest of the four — it needs a lookup table or conversion
library, not just reformatting, since BS month lengths vary year to year and
aren't computable by a fixed formula.

---

## 2026-08-07 — Nepal place-name mapping: use existing authoritative source, don't hand-build

Decision: for district/municipality/ward name mapping (including
Devanagari <-> Roman script), import an existing authoritative reference
dataset rather than hand-building a mapping table entry by entry the way
`fields.yaml` currently works.

Why: Nepal has 753 local government units alone — hand-entering aliases
one at a time (the `fields.yaml` pattern) doesn't scale to this size.
Confirmed that authoritative sources already exist: COD-AB (Common
Operational Dataset - Administrative Boundaries), sourced from Nepal's own
Survey Department, reviewed as recently as October 2024. Also confirmed
via a working GitHub mirror (SaugatPdl/nepal-administrative-boundary-
shapefiles) containing real shapefiles with an attribute table
(DISTRICT, GaPa_NaPa, Type_GN, Province columns) — verified by actually
downloading and reading it, not just reading about it. Note: this
particular mirror only has English/Roman names, not Devanagari — HDX's
COD-AB dataset likely has both but couldn't be directly verified (site
blocked automated fetching).

Decision: this becomes its own package, tentatively `tlf-geo` — NOT part
of `tlf-core`, because it's domain-specific (only useful for geography)
and large (imported reference data), unlike `tlf-core`'s small
domain-agnostic tools. Not yet built — will build when actually needed by
a collector/analysis package requiring geographic joins (Phase 5).

Related but separate: general Nepali/English category-value translation
(e.g. पुरुष/Male, महिला/Female) is a DIFFERENT, much smaller problem —
belongs in `tlf-core`'s planned `ValueResolver`, not `tlf-geo`. See
docs/data_quality_checklist.md "Anticipated but UNCONFIRMED problems" for
the full distinction.

---

## 2026-08-09 — Vocabulary source upgraded: census site's own translation JSON, not just COD-AB

Decision: use censusresults.nsonepal.gov.np's internal next-i18next
translation JSON (captured via browser devtools, per-namespace: `chart`,
`chart-title`, `common`, `population`, `header`, `footer`, `form`, `home`)
as the primary vocabulary source going forward, rather than relying only
on the COD-AB / shapefile mirror from the 08-07 decision.

Why: the COD-AB GitHub mirror confirmed on 08-07 only had English/Roman
names — Devanagari pairing was unverified. This source pairs official
English and Devanagari labels directly by matching key, confirmed by
actually capturing and inspecting real JSON (not just documentation), and
covers far more than place names: religions, disability types, castes,
occupations, industries, marital status, and the full province/district/
municipality list all come from the same mechanism. Supersedes nothing —
COD-AB may still matter for `tlf-geo` if geometry/shapefile data is ever
needed, not just names.

Related: confirmed the source is not internally consistent (e.g.
`chart.Total female`/`chart.Total male` swapped, a stray Devanagari digit
typo) — reinforces the 08-02 decision that vocabulary can't be trusted
verbatim from any single source, authoritative or not.

---

## 2026-08-09 — `extract_vocab.py` is generic; filtering stays a manual review step

Decision: `scripts/extract_vocab.py` pairs matching keys across an en/np
locale JSON with no topic-specific logic — it doesn't try to guess which
entries are "real vocabulary" vs UI chrome (button labels, page copy).
That judgment stays a manual step, done after extraction, not built into
the extractor.

Why: namespace alone is a decent but imperfect signal (`footer`/`form`/
`home` are almost all chrome; `chart`/`population` are almost all real
vocab; `common` and `header` are mixed) — automating the split risked
silently dropping real vocabulary or keeping chrome. Keeping the
extractor dumb and doing the split as a reviewable, visible step (see
next decision) was judged safer than folding heuristics into the tool.

---

## 2026-08-09 — Dedup-by-value is a required step between extraction and review

Decision: after generic extraction, run a dedup pass that groups entries
by their actual `(english, nepali)` value pair (not by key), collapsing
duplicate keys into one row with a list of source keys and namespaces.
This dedup output — not the raw extraction — is what gets manually
reviewed before anything is merged into `values.yaml` or `tlf-geo`.

Why: merging multiple namespace JSONs produces heavy duplication (the
same value under a semantic key in one namespace and a raw-English-as-key
entry in another, e.g. 5+ separate keys all meaning "05-09 years old").
Reviewing ~900 raw keys by hand isn't necessary once true duplicates
collapse to unique value pairs; the `source_keys`/`namespaces` fields
preserved on each row also make namespace-based triage (see next
decision) possible without re-deriving it later.

---

## 2026-08-09 — Vocabulary review triage: split by namespace before human review, not during

Decision: split deduped vocabulary into three files before manual review
— `vocab_geo_candidates.json` (place names, provinces/districts — feeds
`tlf-geo`), `vocab_chrome.json` (UI labels — archived, not reviewed
further), `vocab_review.json` (everything else — the actual `values.yaml`
candidates). Numeric/age-range entries (bare numbers, age bands) are
dropped entirely at this stage, not reviewed — they're a normalizer's job,
not a value-vocabulary problem.

Why: with ~900+ deduped entries mixing municipality names, category
vocab, UI chrome, and numeric noise in one flat list, a single manual
pass would waste effort re-deciding "is this even worth looking at" for
every row. Splitting by namespace first (a cheap, mechanical step) lets
the actual judgment-requiring review focus only on `vocab_review.json`.

## 2026-08-1x — Stop hunting for new data-quality problems, start building

Decision: treat the exploration phase as sufficiently complete a second
time (echoing the 2026-08-02 Phase 1 decision) and shift primary effort
to building rather than continued manual data auditing.

Why: `values.yaml` had reached ~25 categories with broad real coverage;
the last two "new findings" before this decision were confirmed one-off
facts, not new problem categories — a sign of diminishing returns. The
unmapped-queue mechanism designed into `ValueResolver.resolve_column()`
exists specifically to let vocabulary keep growing from real pipeline
runs instead of continued upfront manual sourcing — this is judged to
be the point where that mechanism takes over.

Alternatives considered: continuing to manually audit more CBS/NSO
files before building anything — rejected as diminishing-returns
exploration.

---

## Session 7 — tlf-geo: places.yaml shape resolved pragmatically, not definitively

Decision: build `places.yaml` as a flat `level -> canonical_key ->
[aliases]` structure (matching `values.yaml`'s shape) rather than
resolving the flat-vs-hierarchical design question up front.

Why: real collisions (Bagmati Municipality vs Bagmati Gaunpalika, Byas
Gaunpalika vs Byas Municipality, Madi Gaunpalika vs Madi Municipality)
confirm the hierarchy problem is real, but a flat structure is
immediately useful and doesn't block on that harder question. Real NSO
xlsx exports (checklist #16) confirmed the government's own admin-code
scheme is inherently hierarchical — the strongest evidence yet for
eventually needing a hierarchical shape — but that's deferred to when
`PlaceResolver` is actually built.

Alternatives considered: designing the full hierarchical shape before
writing any code — rejected in favor of building the immediately-useful
flat structure first.

---

## Session 7 — Provinces hand-authored directly, not extracted

Decision: for Nepal's 7 provinces (missing from the census site's
vocabulary — checklist #17), write the `province:` block directly into
`places.yaml` by hand rather than chasing why extraction missed them.

Why: only 7 entries, stable since the 2017 restructuring, both old
numbered (Province 1-7) and new named (Koshi, Madhesh, etc.) forms
needed as aliases. Small and stable enough to trust hand-authorship at
this scale, unlike the 753-entry local-level list explicitly rejected
for hand-building on 2026-08-07.

---

## Session 8 — tlf-core packaged and published to PyPI; v0.1.x scope locked

Decision: package `tlf-core` properly (src/ layout, bundled YAML data,
`tlf-review` CLI) and publish to PyPI (0.1.1). Lock in for this version
line: exact-only resolution (no fuzzy/`suggest()` fallback), pure
resolvers (no file I/O), local-first proposal queue with no automatic
reporting — contributions happen only via voluntary GitHub issue/PR.

Why: fuzzy matching and automatic reporting are both useful ideas, but
each trades away a property (determinism, privacy) worth protecting in
the foundational package rather than baking in early. Both stay
addable later in `tlf-geo`/`tlf-cleaning` without breaking `tlf-core`'s
existing contract.

Alternatives considered: adding a `suggest()`/fuzzy fallback directly
to `ValueResolver` for convenience — rejected for this version to keep
the resolver simple and deterministic.

---

## 2026-08-20 — tlf-geo: two-file split, places.yaml vs codes.yaml

Decision: separate name resolution from code lookup into two files.
`places.yaml` (`level -> canonical_key -> [aliases]`) handles fuzzy/alias
matching only. `codes.yaml` (provinces/districts/local_levels/
protected_areas + a `_by_canonical` reverse index) handles deterministic
code lookup and district-level disambiguation. Canonical keys are never
district-scoped (no `kalika_rasuwa`) — same name in different districts
stays one canonical key; disambiguation happens via `codes.yaml`, not by
inflating the key space.

Why: keeps the two genuinely different jobs — "what did the user mean by
this messy string" vs. "what is this place's official code" — decoupled,
so fuzzy-matching logic in `places.yaml` never has to know about district
codes, and `codes.yaml` never has to guess at spelling variants. Confirmed
via the crosswalk CSV (775 rows, 753 unique local levels + 21 protected
areas) that ~30 canonical keys are genuinely ambiguous across districts
(kalika, sunkoshi, likhu, tribeni, bagmati, godawari, ...), which is
exactly the case this split is designed to handle cleanly.

Alternatives considered: district-scoped canonical keys — rejected per
the Session 7 flat-shape decision, would also make `places.yaml` bigger
and coupled to information it doesn't need.

---

## 2026-08-21 — resolver.py matching strategy: 3-tier ladder, fuzzy always top-3 with no threshold, collision-safe index

Decision: `GeoResolver._get_candidates()` resolves a name through three
tiers in order — (1) exact match, (2) suffix-stripped match (only retried
if stripping changed the string), (3) fuzzy match via
`rapidfuzz.process.extract(scorer=fuzz.ratio, limit=3)`, which always
returns its top 3 results regardless of how weak the best match is (no
minimum similarity cutoff). Tier 3 raises `FuzzyMatchError` (candidates as
`(matched_key, score)` tuples); a genuinely ambiguous exact/suffix match
raises the separate `AmbiguityError` (candidates as full built dicts) —
kept as two distinct exception classes because they mean different things
(typo-suggestion vs. real multi-match) and carry different candidate
shapes. `_build_places_index` stores a **list** per normalized alias
(`setdefault(key, []).append(...)`), not a single value, because real data
confirmed collisions exist even within one alias — e.g. bare "Kalika" is a
legitimate alias for both a gaunpalika and a municipality; an
earlier single-value version silently dropped one.

Why: no-threshold fuzzy matching was an explicit call to let the human
judge weak matches rather than have the library silently decide
"close enough" or "no match" on the user's behalf. Structurally
end-anchored suffix stripping (`.endswith()` per suffix, longest/most-
specific suffix checked first) was chosen over substring replacement as
safer against partial mid-string matches. The single-value index bug was
caught by testing against real data, not by design review.

Alternatives considered: a similarity threshold to suppress very weak
fuzzy suggestions — rejected in favor of always surfacing top 3 and
letting the caller/human decide.

---

## 2026-08-21 — District name index sourced from codes.yaml only, not merged with places.yaml

Decision: `_build_district_name_index()` builds `normalized_district_name
-> district_code` from codes.yaml's `districts` section only (both
`name` and `name_ne`), and is deliberately not merged with the district
aliases already present in `places.yaml`.

Why: the two sources' district aliases are nearly identical anyway, and
the fuzzy-matching tier already provides spelling-variant robustness on
top of this index, so merging added complexity without meaningfully
improving resolution quality. Each district code has exactly one English
and one Nepali name with no duplicates, so no collision handling is
needed here (unlike the places index).

Alternatives considered: merging places.yaml's district aliases into this
index for a larger alias set — rejected as not worth the complexity given
near-identical data and the fuzzy safety net.

---

## 2026-08-21 — Package data paths anchored to module location; relative imports during dev

Decision: anchor all bundled YAML loading via `_MODULE_DIR =
Path(__file__).parent` rather than relative-to-cwd paths, and use
relative imports (`.exceptions`) inside the package, which requires
running the module during development as `python -m
tlf_geo.geo_resolver` from the `src/` directory (not `python
geo_resolver.py` directly).

Why: `tlf-geo` bundles its own YAML data and must load it correctly once
pip-installed, regardless of what directory the caller runs from —
cwd-relative paths would break in that scenario. The dev-time relative-
import friction is temporary and resolves naturally once the package is
actually pip-installed and imported normally as `from tlf_geo import
GeoResolver`.

Alternatives considered: cwd-relative paths (simpler during ad-hoc
testing, but would break for real installed usage) — rejected.

---

## 2026-08-22 — Protected-area resolution explicitly out of scope for `resolve()`

Decision: `resolve()` will not support looking up protected areas
(national parks, wildlife reserves, etc.) by name, and this is a
deliberate scope decision, not an unfixed bug. `protected_areas()` (the
listing method) still works and is tested — only name-based resolution
for that category is unsupported. A docstring note flagging this on
`resolve()` is planned but not yet added.

Why: TLF's real use case is civic/demographic data (census, household
surveys). Protected areas are a separate conservation/tourism domain that
only ended up in the same source files by coincidence of the crosswalk
CSV's structure. Supporting them would require a new
`_by_canonical.protected_area` bucket plus special-casing in
`_build_result()` (which currently assumes every resolved code exists in
`codes_data["local_levels"]`, true for administrative levels but not for
protected areas) — not worth the complexity for a category that won't
actually be queried by name in practice. This closes the gap flagged as
open since Session 11; not to be re-raised as a bug in future sessions.

Alternatives considered: adding the `_by_canonical.protected_area` bucket
and matching `_build_result()` special-casing to fully support it —
rejected as complexity not justified by actual use case.

---

## 2026-08-22 — Documentation tier: README-only for tlf-core and tlf-geo

Decision: both `tlf-core` and `tlf-geo` will be documented with a single
README.md (rendered on both GitHub and PyPI via pyproject.toml's `readme`
field), not a generated docs site (Sphinx/MkDocs/Read the Docs). The
README will follow a use-case-walkthrough structure (e.g. for tlf-geo:
single `resolve()` with disambiguation, batch `resolve_df()`, Django
`to_choices()` dropdown example) rather than a dry parameter-by-parameter
reference, mirroring how the two packages' actual working sessions are
structured.

Why: both packages are small, focused toolkits, not large frameworks with
big public APIs (unlike Django/pandas/numpy, where a generated docs site
earns its overhead). A single well-structured README is proportionate and
keeps documentation effort from becoming its own project.

Alternatives considered: Sphinx/MkDocs for a proper docs site — rejected
as disproportionate to package size/scope at this stage.
