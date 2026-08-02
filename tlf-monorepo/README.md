# TLF Monorepo — Data Engineering & Interoperability

Working monorepo for building TLF's core data-engineering packages: collectors,
the shared interoperability registry (`tlf-core`), and (later) analysis/explorer
packages. Packages will be split into independent repos under `ctpl-git` once
their boundaries stabilize.

## Why a monorepo (for now)

Package boundaries are still fuzzy while `tlf-core`, `tlf-collect-csv`,
`tlf-collect-json`, and `tlf-collect-pdf` are being figured out together. A
monorepo makes it cheap to move code between them. Each folder under
`packages/` is written to be extracted into its own repo later with minimal
changes (own `pyproject.toml`, own tests).

## Roadmap / current phase

- [x] Phase 1 — Manual exploration of real messy CSVs (no code abstractions yet)
- [ ] Phase 2 — `tlf-collect-csv`: dumb collector, no field resolution yet
- [ ] Phase 3 — `tlf-core`: field registry (`fields.yaml`) + resolver, wired into csv collector
- [ ] Phase 4 — `tlf-collect-json`, `tlf-collect-pdf` reusing the same registry
- [ ] Phase 5 — First cross-domain join (education + health on ward), entity resolution
- [ ] Phase 6 — Standards alignment (DCAT-style dataset metadata)

See `docs/decisions.md` for the running log of concrete decisions (field
mappings, format choices, scope calls) made along the way.

## Structure

```
packages/
  tlf-core/           # shared contract, field registry, resolver (Phase 3+)
    notebooks/         # exploratory / manual work (Phase 1 lives here)
    src/tlf_core/
    tests/
docs/
  decisions.md          # dated decision log (lightweight ADR)
```

## Background

Part of Corpola Tech's TLF (The Living Fact) civic-data ecosystem for Nepal.
See the TLF presentation deck for the full architectural context (collect →
connect → create value → present).
