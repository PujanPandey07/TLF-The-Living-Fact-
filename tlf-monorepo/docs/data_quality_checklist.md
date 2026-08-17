# Data Quality Checklist

A working list of problems to check for before or while building a collector
for a new data source. This list isn't finished — it grows every time we find
a new kind of problem in a real file. The point isn't to guess every possible
issue ahead of time. It's to look at data in a structured way instead of
randomly, and to know what kind of fix each kind of problem needs.

## Dimensions to check

- **Consistency** — the same real-world thing written differently across
  sources, or even inside one source. All of our findings so far live here.
- **Completeness** — missing values, and how the missingness is marked
  (blank vs `N/A` vs `-` vs `0`).
- **Accuracy** — is the value actually correct. Hard to check without an
  outside source to compare against.
- **Timeliness** — how current the data is. Risk of comparing two sources
  from different years as if they're from the same year.
- **Uniqueness** — the same real thing (e.g. a ward) listed twice under
  slightly different names.
- **Validity** — does a value fit what's expected (a phone number should be
  about 10 digits, a ward number should be between 1 and 33, etc).

## Confirmed findings

### Session 1 — 2026-08-02 (first look around)

These first three all fall under "consistency," but each one needs a
different fix — which is exactly why we can't solve this with one generic
cleanup function.

### 1. Same word, different casing

- **Where:** two different datasets on Open Data Nepal (ODN)
- **Example:** `"Arghakhanchi"` in one place, `"ARGHAKHANCHI"` in another —
  same district, two different publishers
- **Fix:** simple — lowercase and trim both sides before comparing
  (`.lower().strip()`)

### 2. Same publisher, two languages for the same thing

- **Where:** Bharatpur Metropolitan City's own ward profile documents
- **Example:** Ward 1's document uses the Nepali header "स.नं.", Ward 2's
  uses the English "S.N." — same municipality, same kind of document,
  different wards
- **Fix:** needs a lookup table (a list of known alternate names for each
  column), not a simple text fix, because the words are genuinely
  different, not just formatted differently. This is what `FieldResolver`
  is for.
- **Still open:** we don't know if this comes from each ward doing things
  differently, or just inconsistent publishing on the website. Doesn't
  change the fix, but worth remembering when explaining _why_ this happens.

### 3. Nepali numerals vs. regular numerals

- **Where:** Pokhara Metropolitan City's staff directory
  (pokharamun.gov.np/staff)
- **Example:** some phone numbers are written with Devanagari digits
  (९८४१२३४५६७), others with regular digits (9841234567) — same page, same
  kind of field
- **Fix:** a small function that swaps each Devanagari digit for its
  regular-number equivalent. Different again from fixes #1 and #2.

### 4. Date format AND calendar mixed together

- **Where:** seen across several sources
- **Example:** dates written as `10/06/2079`, `10-06-2079`, and
  `"10th Ashar 2079"` — and some sources use the Western (AD) calendar
  instead of the Nepali (BS) calendar entirely
- **Fix — two separate problems, both needed:**
  - **Formatting** — different punctuation or word order for the same
    calendar. Fixable with normal date-parsing rules once you know the
    format.
  - **Calendar conversion** — BS and AD aren't just different formats,
    they're different calendars. BS month lengths change year to year (set
    officially, not by a fixed formula), so converting between them needs a
    lookup table or a proper conversion library — not just reformatting.
- **Why this one's harder than #1-3:** a date can look perfectly formatted
  and still be ambiguous. `10/06/2079` means nothing until you know if it's
  BS or AD — the two calendars can be ~56-57 years apart. Every date field
  needs to record _which calendar_ it's in, not just the date itself.
- **Seen a second time (Session 2):** the AD/BS mixing specifically (not
  just the punctuation part) showed up again in a different source. This
  confirms it's a real recurring problem, and that calendar conversion is
  the harder half worth prioritizing.

### Session 2 — 2026-08-03 (continued)

### 5. Short forms vs. full words for the same value

- **Where:** a Ministry of Education Flash Report PDF (text-based, not a
  scanned image)
- **Example:** sex recorded as `"M"`/`"F"` in some tables, `"Male"`/
  `"Female"` in others — **inside the same PDF report**, not even across
  different documents
- **Fix:** this isn't a header problem, so `FieldResolver` doesn't help —
  it needs a sibling tool that works on _values inside a column_, not
  column names. This is what `ValueResolver` is for.
- **Why this one stands out:** it's the first case where even a single
  author wasn't consistent with themselves across their own tables — worse
  than the Bharatpur case, which could at least be explained as different
  wards doing their own thing.

### 6. Age groups split at different sizes

- **Where:** same Ministry of Education PDF, two different tables — one
  splits ages into `0-4`, `5-9`, `10-14`... the other into `0-14`,
  `15-29`...
- **Why this is different from #1-5:** every earlier problem was "the same
  value, written two ways" — a simple rename fixes it. This one isn't that.
  The two tables measure age at different levels of detail. To match them
  up you'd have to **add rows together** (e.g. `0-4 + 5-9 + 10-14 = 0-14`),
  and that only works if the boundaries actually line up. If they don't
  (say `0-4, 5-12, 13-19`), some data just can't be reconciled without a
  judgment call.
- **Fix:** neither renaming headers nor renaming values solves this — it
  needs real logic to combine rows together, which is a bigger decision
  than a simple lookup. This belongs in a future `tlf-cleaning` package,
  not in `tlf-core`'s small no-judgment tools.

### 7. The website itself was down

- **Where:** a national government data portal (ASP.NET-based; exact URL
  to confirm — likely `nationaldata.gov.np` or the MoFAGA local government
  profile system)
- **Example:** the site returned a raw server error page ("Runtime
  Error... An application error occurred on the server") instead of the
  page we wanted
- **Why this is different from #1-6:** every earlier problem assumed we
  could at least reach the data and then found it messy. This is a level
  before that — we couldn't reach it at all.
- **Fix:** none of `tlf-core`'s tools can fix this — it's not a per-field
  problem, it's a design question for TLF as a whole. Suggests TLF should
  save its own copies of data once collected, instead of assuming
  government websites will always be up. Worth trying the Wayback Machine
  (web.archive.org) for an older working copy when a source is down.
- **Why it matters:** confirms government sites going down isn't a
  one-off — it's a real, repeating problem, and part of why TLF is useful
  beyond just cleaning up formatting.

### 8. Different ways of marking "no data"

- **Where:** seen across several sources
- **Example:** a missing value shows up as `"N/A"` in one table, `"-"` in
  another, `"NR"` (probably "No Result") in another — three different
  labels for the same thing
- **Why this matters:** if one of these ever got mistaken for a real value
  instead of "missing" (e.g. reading `"-"` as a minus sign or a zero), it
  would quietly corrupt any totals or averages calculated from that column.
- **Fix:** a function that recognizes known "missing" labels (`"N/A"`,
  `"-"`, `"NR"`, empty string, maybe Nepali versions we haven't seen yet)
  and turns them all into one standard "missing" marker before any
  analysis happens. Not built yet.

### 9. Commas in numbers

- **Where:** seen across several sources, including the original 3 test
  CSVs — `literacy_above_five.csv` stored totals like `"23,926,541"` as
  text, while `population_education_level.csv` had the same kind of number
  as a plain `16098519`
- **Why this matters:** a number with commas is read as **text**, not a
  number — you can't add, average, or compare it to a clean number without
  fixing it first. If missed, calculations either fail loudly or, worse,
  silently skip that value.
- **Fix:** strip the commas, then convert to a real number. Simple to do,
  but has to happen **before** any math, and only on columns that actually
  need it — some columns are already clean.

### 10. Short header vs. full header, same language

- **Where:** seen across several sources
- **Example:** a totals column is just called `"T"` in one table, spelled
  out as `"Total"` in another
- **Why this is different from #2:** #2 was a language _switch_ (Nepali to
  English). This is the same language, just shortened. Shows that the
  header-matching problem isn't only about different languages — plain
  English abbreviations need the same treatment too.
- **Fix:** this is exactly what `FieldResolver` already handles — just add
  `"T"` as a known alternate name for `total` in `fields.yaml`. No new tool
  needed, unlike #5 and #6 — just a new entry.

### 11. `%` symbol vs. the word "percent"

- **Where:** seen across several sources
- **Example:** some columns/values use `%` (`"45%"`, or a header like
  `"% literate"`), others spell it out (`"45 percent"`,
  `"Percent literate"`)
- **Why this matters:** if it's inside a value, `"45%"` is read as text
  until the symbol is removed — same problem as commas in numbers (#9). If
  it's in a header, it's the same short-vs-full-word problem as #10.
- **Fix:** probably needs both — a value fix (remove `%` or the word
  "percent", convert to a plain number, and settle on whether the standard
  form is 0-100 or 0-1) and, if it shows up in headers too, a new
  `fields.yaml` entry like #10.

### Session 3 — 2026-08-07 (checking a real government PDF)

### 12. The PDF text looks right on screen but is wrong underneath

- **Where:** a real municipality profile PDF (Suddhodha Gaunpalika, a
  government report exported from Microsoft Word)
- **Example:** pulling text out of the PDF with a normal tool
  (`pdftotext`) gave word like `"मािृभार्ा"` when the page actually shows
  `"मातृभाषा"` (mother tongue). Other examples from the same table:
  `"अविी"` instead of `"अवधी"` (Awadhi), `"पहन्दी"` instead of `"हिन्दी"`
  (Hindi), `"मैधथली"` instead of `"मैथिली"` (Maithili).
- **Why this is worse than it sounds:** this isn't obviously broken text —
  it still looks like real Devanagari, just the wrong word. Unlike garbled
  text you'd immediately notice and throw out, this kind of error is easy
  to miss and could get copied straight into a clean dataset, quietly
  making it wrong.
- **Why it happens:** the PDF was made in Microsoft Word using older-style
  Nepali fonts (we saw `Kalimati`, `Himalaya`, `PreetiItalic` embedded in
  this file) built before Nepali typing had a proper standard. These fonts
  draw the right letters on screen, but the actual character codes stored
  underneath are wrong. Any tool that reads the underlying text — not just
  looking at the page — reads the wrong codes.
  - One thing that did work correctly in this same file: the numbers.
    We checked a row's totals against the image and they matched — this
    particular problem only affects letters, not digits, at least in this
    document. That won't necessarily hold for every document.
- **Fix:** for Nepali-language PDFs, check which fonts are embedded first
  (`pdffonts`). If the PDF uses one of these older-style fonts, don't trust
  the extracted text — instead, turn the page into an image and read it
  visually (or run OCR on it) to get the real words. Plain-English PDFs
  with standard fonts don't have this problem and can use normal text
  extraction.
- **What this means for `tlf-collect-pdf`:** the collector can't always
  use the fast "just extract the text" path for Nepali sources. It needs a
  first check — "is this font safe?" — before deciding whether to read the
  page as text or as an image.

## Not yet checked

- Validity (values outside the expected range)
- Uniqueness (the same thing listed twice under different names)

We haven't gone looking for these on purpose — they'll likely turn up
naturally once `tlf-collect-csv` starts running against real files. Worth
adding to this list as they come up, instead of hunting for them by hand
right now.

## Guessed but not yet confirmed

We're pausing active hunting here — the last few things we found were
repeats of problems we already knew about, not new kinds, and some sources
are getting harder to reach reliably (see #7). The two things below are
**educated guesses**, not confirmed findings, based on patterns we've
already seen elsewhere. Don't treat these the same as findings #1-12. Each
one should get checked for real once collector code runs against enough
files — not searched for by hand right now.

- **Validity (guess):** given how sloppy the formatting already is (commas
  in numbers, `%` symbols, inconsistent missing-value labels), it's likely
  some numeric fields have out-of-range values too (a ward number outside
  1-33, a percentage over 100). Not confirmed yet.
- **Uniqueness (guess):** given the naming inconsistency we've already
  found (#1) and header inconsistency even within one municipality (#2),
  it's likely the same real place (a municipality, a ward) shows up twice
  under slightly different names somewhere in a bigger combined dataset.
  Not confirmed yet.
- **Nepali/English value translation (guess — a "what if," not yet
  directly seen):** could values like `पुरुष`/`Male`, `महिला`/`Female` show
  up across Nepali- and English-language sources for the same thing? This
  is a **different problem** from the place-name question below — don't
  mix them up:
  - **This one** (category values like sex, yes/no, urban/rural) is a
    small, fixed list of options — same shape as finding #5, just also
    crossing two languages. Belongs in `tlf-core`, as part of
    `ValueResolver` (e.g. `sex: {male: ["m", "male", "पुरुष"]}`). Small
    enough to live right alongside `FieldResolver`, not its own package.
  - **Place names** (district, municipality, ward names, in Devanagari vs.
    Roman script) is a much bigger problem — hundreds or thousands of
    names, not a short list. This is a separate topic: an official source
    already exists for this (COD-AB / Survey Department boundary data) and
    should be imported wholesale instead of built by hand — likely its own
    package, `tlf-geo` (not built yet, revisit when needed — see
    `docs/decisions.md`).

**Next step for both:** revisit once `tlf-collect-csv`/`json`/`pdf` are
running against a real batch of files. Validity and uniqueness checks are
much easier to catch automatically inside a running pipeline than to hunt
for by eye — unlike findings #1-12, which needed manual checking to spot in
the first place.

### 13. Wide-format "spine" width isn't fixed across files

- **Where:** CBS curated CSVs on data.nsonepal.gov.np
  (NR_Indv29_PopulationByEcoActivity.csv vs NR_Indv22_PopulationByCountryOfStay.csv)
- **Example:** File 1's spine is `area, prov, dist, area_name` (4 cols)
  before payload; File 2's spine is `area, prov, dist, sex, area_name,
sexname, rowtotal` (7 cols) — extra `sex`/`sexname` columns spliced
  into the middle of the spine, not appended after it.
- **Why this matters:** assuming a fixed column offset ("everything
  after column N is payload") breaks silently on File 2 — you'd either
  melt real spine columns as if they were payload, or miss melting real
  payload columns.
- **Fix:** spine width/composition must be detected per file, not
  assumed from one example. Not yet built — leaning toward this living
  in `tlf-cleaning` rather than `tlf-core`, since it needs detection
  logic, not a static lookup.

### 14. One column mixes multiple geographic granularities

- **Where:** same CBS curated CSVs, the `area` column specifically
- **Example:** one file's `area` column contains national-level rows
  (code 10), urban/rural aggregate rows (21/22), ecological-zone rows
  (31/32/33), province rows (40), and district rows (50) — all in the
  same column, distinguished only by numeric code range.
- **Why this matters:** naively summing a payload column without first
  filtering to one `area` code range would massively overcount — a
  province's total would get added on top of the district totals that
  already sum to it.
- **Fix:** needs a row-filtering step (based on the area-code range)
  before any melt or aggregation runs. Doesn't fit `FieldResolver` or
  `ValueResolver` — needs its own filter step, likely in `tlf-cleaning`.

### 15. Payload header abbreviations split into two genuinely different problem types

- **Where:** same CBS curated CSVs' payload columns
- **Example — Type A (opaque, no algorithmic shortcut):**
  `nua_male`/`nua_feml`, `nea_male`/`nea_feml`, `notstd_male`/`notstd_feml`.
  No official CBS data dictionary found published alongside the raw
  CSVs. Best-guess meanings (`nea` = not economically active, `nua` =
  not usually active, `notstd` = not stated) are plausible but
  **unconfirmed**.
  **Example — Type B (fuzzy-matchable):** `a_india`, `b_saarc`,
  `c_asean`, `d_midleast`, `e_othrasian`, `f_eucntry`, `g_othreuropn`,
  `h_northamericn`, `i_southamericn`, `j_african`, `k_pacific`,
  `l_other`, `m_notstd` — same 13-item list, same order, as the
  `foreign_country_region` category already in `values.yaml`.
- **Why this matters:** these need different fixes. Type A has no
  shared substring to fuzzy-match against — Levenshtein/rapidfuzz finds
  nothing useful against an opaque initialism. Type B's abbreviations
  contain recognizable substrings (`india`, `midleast`≈"middle east")
  and CAN be fuzzy-suggested for human confirmation.
- **Fix:** Type A — one-time manual lookup, then a permanent
  `fields.yaml` entry, no shortcut possible. Type B — fuzzy/substring
  match against existing `values.yaml` aliases to auto-suggest
  candidates, human confirms. CBS's internal category ordering leaking
  into column names (Type B) is a reusable pattern worth building a
  lookup table from.

### 16. Two incompatible ways of encoding geographic hierarchy across NSO's own xlsx exports

- **Where:** two real NSO xlsx files (CRB_15_Children_by_occupation.xlsx,
  WRD_Hhld06-SourceOfDrinkingWater.xlsx)
- **Example:** File 1 uses explicit numeric composite codes
  (`prov`/`dist`/`gapa`) where `dist` resets per province (`dist=1`
  under `prov=1` is Taplejung, not necessarily `dist=1` under any other
  province) and `0` at any level means "rollup total for everything
  under it." File 2 has no codes at all — hierarchy is encoded purely
  by column position plus blank-cell inheritance (a place name appears
  only on the row where it starts; every row below inherits it until
  the next name appears at that column) — and goes one level deeper
  (ward) than File 1.
- **Why this matters:** a single "parse the geography columns" function
  can't handle both — these aren't variations of one format, they're
  two different encoding mechanisms.
- **Fix:** don't build one universal parser. Build one small,
  config'd-per-file tool per pattern (a rollup filter for the
  code-based format, a forward-fill "unstairs" utility for the
  staircase format), and accept that surveying all ~71 files by hand
  isn't feasible — apply the right tool as each new format is
  encountered.

### 17. An entire expected category can be missing from a source, not just individual entries

- **Where:** censusresults.nsonepal.gov.np's `common` namespace
  vocabulary (feeding `tlf-geo`'s `places.yaml`)
- **Example:** the vocabulary capture has ~753 municipalities/
  gaunpalikas and all 77 districts, but zero entries for Nepal's 7
  provinces — not misfiled under a different namespace, genuinely
  absent from the extracted JSON.
- **Why this matters:** every earlier finding in this list is about
  individual values being messy; this is about an entire expected
  slice of data not existing in the source at all. Easy to miss if you
  only check "does the data I have look clean" rather than "is there
  data I'd expect that isn't here" — a **completeness**-dimension
  finding, the first one on this list.
- **Fix:** for a small, stable, well-known list (only 7 provinces,
  unchanged since the 2017 restructuring), hand-authoring the missing
  category is more sensible than chasing why extraction missed it.
  Worth checking if the province selector routes through a different
  mechanism than district/municipality dropdowns if this recurs.
