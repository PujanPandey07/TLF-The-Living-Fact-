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
