# TLF — The Living Fact

**Making Nepal's civic and census data interoperable.**

Nepal's public data — census results, ward profiles, staff directories,
survey exports — is real, useful, and inconsistent in the ordinary ways
government and NGO data usually is: the same column means three different
things across files (`c.id` / `c_no` / `नागरिकता नं`), the same value is
written five different ways (`M` / `Male` / `पुरुष`), place names carry
spelling variants and script mixing, and dates mix the Bikram Sambat and
Gregorian calendars. None of this is a data-quality failure so much as the
normal cost of many independent sources never having agreed on a shared
vocabulary.

TLF is a toolkit for closing that gap — not by rewriting the data, but by
resolving it: mapping messy real-world headers and values to one canonical
form, deterministically, with unresolved cases queued for review rather than
silently dropped or guessed at.

TLF is an initiative started by [Corpola Tech](https://github.com/PujanPandey07)
and the [Open Tech Community](https://www.facebook.com/opentechcommunity/),
released as open source for anyone in Nepal working with civic, census, or
survey data to use, extend, or contribute back to.

---

## The two packages

Rather than one large all-purpose library, TLF is deliberately built as a
growing collection of small, focused packages — one per problem domain —
published and versioned independently. `tlf-core` and `tlf-geo` are the
first two; more (e.g. around date/calendar conversion, or other data-quality
problems logged in `docs/`) are expected to follow the same pattern as real
needs surface. The two so far:

### [`tlf-core`](packages/tlf-core) — field & value resolution, general-purpose

Resolves column headers and cell values to a canonical form, and cleans up
common formatting problems inside values that already resolve (casing,
Devanagari digits, date formatting, invisible Unicode artifacts, phone
numbers). Domain-agnostic — works for any category of tabular data, not just
geography. Exact-match only by design; nothing is guessed, and anything
unrecognized goes into a local review queue.

📦 [PyPI](https://pypi.org/project/tlf-core/) · [package README](packages/tlf-core/README.md)

### [`tlf-geo`](packages/tlf-geo) — Nepal administrative geography resolution

Resolves messy place names (province, district, and all 753 local government
units — gaunpalika, municipality, sub-metropolitan and metropolitan city) to
their official NSO codes, including fuzzy matching for typos and spelling
variants, and disambiguation for the ~30 names that legitimately exist in
more than one district (e.g. "Kalika" in both Rasuwa and Chitawan).
Domain-specific and built on top of the same resolution philosophy as
`tlf-core`, but kept as a separate package since it's large (bundled
reference data) and only useful for geography.

📦 [PyPI](https://pypi.org/project/tlf-geo/) · [package README](packages/tlf-geo/README.md)

---

## Shared approach

Both packages follow the same core rules, carried over from `tlf-core`'s
initial design and kept intentionally simple:

- **Deterministic first.** Exact/alias matching is the default path; fuzzy
  matching (where it exists, in `tlf-geo`) is an explicit, separate fallback
  tier — never silently blended into "close enough."
- **Never guess, never drop.** Anything that doesn't resolve is surfaced
  (via a review queue or a raised exception with candidates), not discarded
  and not silently passed through as if it were canonical.
- **Vocabulary grows from real files, not upfront guessing.** Registries
  (`fields.yaml`, `values.yaml`, `places.yaml`/`codes.yaml`) started from
  authoritative sources where they exist, and grow from what real pipeline
  runs actually encounter.
- **Local-first.** Nothing about how these packages resolve data reports
  usage or unresolved values anywhere automatically — contributions back to
  the shared registries happen only if you choose to open an issue or PR.

---

## Repo layout

```
tlf-monorepo/
├── packages/
│   ├── tlf-core/        # field & value resolution (published)
│   └── tlf-geo/         # Nepal place-name resolution (published)
├── docs/                 # data-quality findings, design notes
├── scripts/               # vocabulary extraction / build tooling
└── external-data/         # source reference data (crosswalks, census exports)
```

Each package is self-contained under `packages/<name>/` with its own
`pyproject.toml`, bundled data, and README — see the package-level docs
linked above for installation and API details.

---

## Contributing

Each package's own README covers how to contribute to that package's
registries specifically. In general: unresolved values/fields queue up
locally when you use these packages — nothing is reported automatically.
If you'd like to share what you found, open an issue or PR against this
repo.

---

## License

MIT
