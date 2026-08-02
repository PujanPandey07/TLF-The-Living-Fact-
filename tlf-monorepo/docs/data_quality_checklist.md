# Data Quality Checklist

A working checklist to run against any new data source before/while building
a collector for it. Not exhaustive — grows as new problem types are found in
real sources. The goal isn't to predict every possible issue in advance; it's
to look systematically instead of randomly, and to know what kind of fix each
category needs.

## Dimensions to check

- **Consistency** — same real-world concept, represented differently across
  sources (or even within one source). This is where all three confirmed
  findings below live.
- **Completeness** — missing values, and _how_ missingness is marked (blank
  vs `N/A` vs `-` vs `0`). Not yet checked directly — worth watching for once
  we start writing collectors.
- **Accuracy** — is the value actually correct. Hard to verify without an
  independent source of truth; often not fully checkable from the data alone.
- **Timeliness** — how current the data is; risk of comparing sources from
  different years as if they were contemporaneous.
- **Uniqueness** — duplicate records (e.g. same ward listed twice under
  slightly different names).
- **Validity** — does a value fit the expected type/range (a phone number
  should be ~10 digits, a ward number should be 1–33, etc.).

## Confirmed findings (Phase 1, 2026-08-02)

All three are in the **consistency** bucket, but need different fixes —
important, because it means normalization can't be one generic function.

### 1. Casing inconsistency in place names

- **Source:** two different datasets on Open Data Nepal (ODN)
- **Example:** `"Arghakhanchi"` vs `"ARGHAKHANCHI"` — same district, different
  publishers
- **Fix type:** simple normalization (`.lower().strip()`) before comparison/join

### 2. Language inconsistency within a single publisher

- **Source:** Bharatpur Metropolitan City's own ward profile documents
- **Example:** Ward 1's profile uses Nepali column headers (e.g. "स.नं."),
  Ward 2's uses English ("S.N.") — same municipality, same document type,
  different wards
- **Fix type:** alias/translation map (the field registry / crosswalk
  approach) — can't be solved with simple string normalization since the
  words are genuinely different, not just differently formatted
- **Open question:** not yet confirmed whether this reflects a real
  inconsistency in each ward's own process, or just inconsistent website
  publishing over otherwise-similar underlying data. Doesn't change what the
  collector needs to handle, but worth keeping in mind when describing _why_
  the inconsistency exists.

### 3. Numeral system inconsistency (Devanagari vs Arabic digits)

- **Source:** Pokhara Metropolitan City staff directory
  (pokharamun.gov.np/staff)
- **Example:** some phone numbers written in Devanagari numerals (e.g.
  ९८४१२३४५६७), others in Arabic numerals (9841234567) — same page, same
  field
- **Fix type:** digit transliteration (a small utility function mapping
  Devanagari digit characters to Arabic digits), not a lookup table — a third,
  distinct kind of fix from #1 and #2

### 4. Date format AND calendar system inconsistency

- **Source:** general observation across sources explored so far
- **Example:** dates appear as `10/06/2079`, `10-06-2079`, and
  `"10th Ashar 2079"` — and some sources use AD (Gregorian) dates instead of
  BS (Bikram Sambat) entirely
- **Fix type:** two separate sub-problems, both needed:
  - **Format parsing** (Layer 1) — punctuation/order differences
    (`/` vs `-` vs spelled-out month) with the same underlying calendar;
    fixable with standard date-parsing rules once the format is known
  - **Calendar conversion** (Layer 2) — BS and AD are genuinely different
    calendar systems, not just different formats. BS month lengths vary
    year to year (officially declared, not computable by a fixed formula),
    so BS↔AD conversion needs a lookup table or a dedicated conversion
    library, not regex/reformatting
- **Why this one is harder than #1-3:** a value can be perfectly
  well-formatted and still ambiguous — `10/06/2079` is meaningless without
  knowing whether it's BS or AD, since the two calendars can disagree by
  ~56-57 years. Fields need to record _which calendar_ alongside the date
  itself, not just the date.

## Not yet explored

- Completeness (missing value conventions)
- Validity (malformed/out-of-range values)
- Uniqueness (duplicate entities under different names)

These weren't hunted for directly — likely to surface naturally once
`tlf-collect-csv` starts running against real files. Worth revisiting this
checklist and adding findings as they come up, rather than searching for them
in the abstract now.
