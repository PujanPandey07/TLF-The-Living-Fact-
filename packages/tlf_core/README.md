# tlf-core

**One canonical value, however many ways someone spelled it.**

`tlf-core` resolves messy real-world column headers and cell values (`c.id` / `c_no` / `नागरिकता नं`, `M` / `Male` / `पुरुष`) to one canonical form, and cleans up common formatting problems inside values that already resolve — casing, Devanagari digits, dates, invisible Unicode artifacts, phone numbers.

Part of **TLF (The Living Fact)**, Corpola Tech's toolkit for making Nepal's civic and census data interoperable.
Full project story, data sources, and architecture reasoning: [github.com/PujanPandey07/TLF-The-Living-Fact-](https://github.com/PujanPandey07/TLF-The-Living-Fact-)

> **Status:** Alpha (v0.1.2). Registries grow from real files as they're processed — expect gaps, and see [Contributing](#contributing).

---

## Installation

```bash
pip install tlf-core
```

---

## Quick start

```python
import pandas as pd
from tlf_core import ValueResolver, FieldResolver, default_registry_path, proposal_queue

df = pd.read_csv("your_file.csv")

# 1. Resolve column headers to canonical field names.
#    No arguments needed — FieldResolver automatically uses its own
#    bundled fields.yaml unless you pass a different path.
field_resolver = FieldResolver()
rename_map, unmapped_fields = field_resolver.resolve_columns(df.columns.tolist())
df = df.rename(columns=rename_map)

# 2. Resolve cell values within a known column
value_resolver = ValueResolver(default_registry_path("values.yaml"))
resolved, unmapped_values = value_resolver.resolve_column(df["sex"], category="sex")

# 3. Whatever didn't resolve, queue it for review instead of losing it
if unmapped_values:
    proposal_queue.queue_unmapped(
        unmapped=unmapped_values,
        kind="value",
        category="sex",
        source="your_file.csv",
        queue_path="queue.json",
    )
```

Then review what came up later:

```bash
tlf-review queue.json values.yaml value
```

---

## API Reference

Every function below is available directly from the top-level package: `from tlf_core import <name>`.

### `FieldResolver` — resolves column headers

```python
from tlf_core import FieldResolver

# Uses the bundled fields.yaml automatically — nothing else to configure
resolver = FieldResolver()

# Or point it at your own copy explicitly (see note below on when this matters)
resolver = FieldResolver(registry_path="path/to/your/fields.yaml")
```

**`resolver.resolve(raw_field_name: str) -> str | None`**
Resolves one raw column header. Returns the canonical name, or `None` if unrecognized (never guesses).

```python
resolver.resolve("c_no")   # "citizenship_id"
```

**`resolver.resolve_columns(columns: list[str]) -> tuple[dict[str, str], list[str]]`**
Resolves a whole list of column names. Returns `(rename_map, unmapped)` — `rename_map` is ready for `df.rename(columns=rename_map)`.

```python
rename_map, unmapped = resolver.resolve_columns(["c_no", "जिल्ला", "???"])
# rename_map == {"c_no": "citizenship_id", "जिल्ला": "district"}
# unmapped   == ["???"]
```

> **Using `tlf-review` to grow the registry?** Pass an explicit `registry_path` pointing at _your own_ writable copy of `fields.yaml` — don't rely on the no-args default for this. The default reads the copy bundled inside the installed package, which gets overwritten every time you reinstall or upgrade `tlf-core`. The no-args default is meant for read-only lookups (like `tlf-geo-auto`'s use case), not for a workflow that writes approved aliases back into the file.

---

### `ValueResolver` — resolves cell values within a column

```python
from tlf_core import ValueResolver, default_registry_path
resolver = ValueResolver(default_registry_path("values.yaml"))
```

**`resolver.resolve(value: str, category: str) -> str | None`**
Resolves one raw value, scoped to a category. Returns the canonical value, or `None` if unrecognized.

```python
resolver.resolve("पुरुष", category="sex")   # "male"
```

**`resolver.resolve_column(values, category: str) -> tuple[list, list[str]]`**
Resolves a whole column (`list` or pandas Series). Returns `(resolved_values, unmapped)` — unknown values are left as-is, never dropped or guessed.

```python
resolved, unmapped = resolver.resolve_column(["M", "F", "Other"], category="sex")
# resolved == ["male", "female", "Other"]
# unmapped == ["Other"]
```

> Unlike `FieldResolver`, `ValueResolver` still requires an explicit `registry_path` — there's no bundled-default shortcut for `values.yaml` yet.

---

### Normalizers

Each comes as a **single-value** function and a **column** function (applies across a pandas Series, skipping `NaN`/`None` automatically).

| Function                                                                                  | Does                                                                                                                                 | Example                                 |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| `normalize_casing(value)` / `normalize_column_casing(series)`                             | Lowercase + strip whitespace                                                                                                         | `"  ARGHAKHANCHI  "` → `"arghakhanchi"` |
| `normalize_devanagari_digits(value)` / `normalize_column_devanagari_digits(series)`       | Devanagari numerals (०-९) → Arabic (0-9)                                                                                             | `"९८-५२२१११"` → `"98-522111"`           |
| `normalize_date(value)` / `normalize_column_date(series)`                                 | Parses numeric/AD-month/BS-month (Devanagari or romanized) dates → `YYYY-MM-DD`. **Format only — does not convert BS↔AD calendars.** | `"15 Baishakh 2081"` → `"2081-01-15"`   |
| `normalize_whitespace_artifacts(value)` / `normalize_column_whitespace_artifacts(series)` | Strips invisible Unicode (ZWJ/ZWNJ/BOM/NBSP), collapses multi-spaces                                                                 | `"Kath\u200bmandu"` → `"Kathmandu"`     |
| `normalize_chrome_symbols(value)` / `normalize_column_chrome_symbols(series)`             | Strips list enumerators and trailing footnote marks                                                                                  | `"01 - Koshi"` → `"Koshi"`              |
| `normalize_phone_number(value)` / `normalize_column_phone_number(series)`                 | Standardizes Nepali landline/mobile numbers                                                                                          | `"+977-9812345678"` → `"9812345678"`    |

```python
df["phone"] = normalize_column_phone_number(df["phone"])
df["district"] = normalize_column_casing(df["district"])
```

---

### `default_registry_path(filename: str) -> Path`

Path to a registry YAML bundled inside the installed package (`"fields.yaml"` or `"values.yaml"`).

```python
from tlf_core import default_registry_path, ValueResolver
resolver = ValueResolver(default_registry_path("values.yaml"))
```

`FieldResolver()` uses this same bundled path automatically when called with no arguments — you only need `default_registry_path` directly for `ValueResolver`, or if you want `FieldResolver`'s underlying path for some other purpose.

---

### `proposal_queue.queue_unmapped(...)`

Persists unresolved values/fields to a JSON file so they survive past the current run. Duplicate `(kind, category, raw_value)` entries across files/runs merge into one, with `seen_count` incrementing and `sources` growing rather than duplicating.

```python
proposal_queue.queue_unmapped(
    unmapped=["Other", "Unknown"],
    kind="value",              # or "field"
    category="sex",             # None for kind="field"
    source="ward5_survey.csv",
    queue_path="queue.json",
)
```

---

### `tlf-review` — review CLI

```bash
tlf-review <queue_path> <registry_path> <value|field>
```

Walks pending entries interactively, most-frequently-seen first. Type an existing canonical key to add an alias, press enter for a new key, `skip`, or `reject`. Approved entries are written directly into the registry file — nothing merges without you typing something.

**Important:** point `<registry_path>` at your own writable copy of `fields.yaml`/`values.yaml`, not the bundled copy inside the installed package. Changes written into the bundled copy will be lost the next time you reinstall or upgrade `tlf-core`.

---

## What this does NOT do

- No fuzzy matching — unrecognized values go to the queue, never guessed at
- No automatic reporting — unmapped data stays local unless you choose to share it
- No BS↔AD calendar conversion — `normalize_date()` standardizes format only

---

## Contributing

`queue.json` isn't part of the package — it's created wherever you point `queue_path`, the first time you call `queue_unmapped()`. What happens next depends on how you're using this:

**Just installed via `pip install tlf-core`?** Unresolved values queue up and get reviewed _locally_ — your own `queue.json`, your own copy of the registry. Nothing reaches this repo automatically. If you'd like to share what you found:

1. [Open an issue](https://github.com/PujanPandey07/TLF-The-Living-Fact-/issues) listing the raw values/fields that didn't resolve, or
2. Clone this repo, point `queue_path`/`registry_path` at the real `fields.yaml`/`values.yaml` inside it (not your local copies), run `tlf-review` there, and open a PR with the result.

**Already working from a clone of this repo?** You're editing the real registry files directly — commit and PR your changes once reviewed.

For the project's background, data sources, and architecture decisions, see the [main repo](https://github.com/PujanPandey07/TLF-The-Living-Fact-).

---

## License

MIT
