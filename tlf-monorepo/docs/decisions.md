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
