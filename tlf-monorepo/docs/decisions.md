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
