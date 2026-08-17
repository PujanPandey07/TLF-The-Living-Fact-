"""
tlf-geo reconciliation script.

Matches your hand-curated places.yaml (canonical_key -> [aliases]) against
municapalities.csv (the official codes source) to produce:

  1. crosswalk.yaml       canonical_key -> locallevel_fullcode
  2. places.enriched.yaml  places.yaml + new aliases pulled from the CSV
  3. review_needed.csv     low-confidence matches you must check by hand

Run once, offline. Never point this at production files directly --
always review the outputs before merging them in.

Install deps first:
    pip install rapidfuzz pyyaml pandas --break-system-packages
"""

import re
import pandas as pd
import yaml
from rapidfuzz import fuzz, process

# ---- file paths --------------------------------------------------------
PLACES_YAML = "places.yaml"
CSV_PATH = "municapalities.csv"

CROSSWALK_OUT = "crosswalk.yaml"
ENRICHED_OUT = "places.enriched.yaml"
REVIEW_OUT = "review_needed.csv"

# only these levels in places.yaml have a matching row in the CSV.
# province/district are handled separately (see build_codes.py).
LOCAL_LEVELS = ["gaunpalika", "municipality", "metropolitan_city", "sub_metropolitan_city"]

# fuzzy match score below this always goes to manual review, never auto-linked
MATCH_THRESHOLD = 90

# suffix words to strip before comparing -- both languages, both directions
SUFFIXES = [
    # both correct spelling and the "metropolitian" typo baked into the
    # source data itself -- keep both, don't "fix" the data silently
    "metropolitan city", "metropolitian city",
    "sub-metropolitian city", "sub-metropolitan city", "sub metropolitan city",
    "municipality", "gaunpalika", "nagarpalika", "upamahanagarpalika",
    "महानगरपालिका", "उपमहानगरपालिका", "नगरपालिका", "गाउँपालिका",
]


# ---- step 3: normalize() ------------------------------------------------
def normalize(name: str) -> str:
    """Lowercase, strip suffix words, strip punctuation/extra whitespace."""
    s = name.lower().strip()
    # longest suffix first -- otherwise "उपमहानगरपालिका" gets partially
    # eaten by "महानगरपालिका", leaving a dangling "उप" prefix behind
    for suf in sorted(SUFFIXES, key=len, reverse=True):
        s = s.replace(suf.lower(), "")
    s = re.sub(r"[.\-()]", " ", s)   # drop punctuation like "K.I. Singh", "Balan-Bihul"
    s = re.sub(r"\s+", " ", s).strip()
    return s


def test_normalize():
    """Step 3 sanity check -- run this alone before step 4."""
    cases = [
        ("Nepalgunj Sub-Metropolitian City", "नेपालगंज उपमहानगरपालिका"),
        ("Byas Municipality", "ब्यास नगरपालिका"),
        ("K.I. Singh Gaunpalika", "के.आई.सिं. गाउँपालिका"),
    ]
    for en, np in cases:
        print(f"{en!r:45} -> {normalize(en)!r}")
        print(f"{np!r:45} -> {normalize(np)!r}")


# ---- step 2: load both sources ------------------------------------------
def load_sources():
    with open(PLACES_YAML, "r", encoding="utf-8") as f:
        places = yaml.safe_load(f)

    csv = pd.read_csv(CSV_PATH)

    print("places.yaml levels found:", list(places.keys()))
    for level in LOCAL_LEVELS:
        print(f"  {level}: {len(places.get(level, {}))} canonical keys")
    print("CSV rows:", len(csv))

    return places, csv


# ---- step 4: fuzzy match to build the crosswalk --------------------------
def build_crosswalk(places, csv):
    # precompute normalized CSV names once (perf: avoid re-normalizing per key)
    csv = csv.copy()
    csv["_norm_en"] = csv["locallevel_name"].apply(normalize)
    candidates = csv["_norm_en"].tolist()

    crosswalk = {}
    enrich_log = {}      # canonical_key -> {en, np} spellings to add later
    unmatched = []

    for level in LOCAL_LEVELS:
        for key, aliases in places.get(level, {}).items():
            # prefer an ascii (EN) alias as the query string
            en_aliases = [a for a in aliases if a.isascii()]
            if not en_aliases:
                unmatched.append({
                    "level": level, "canonical_key": key,
                    "your_aliases": " | ".join(aliases),
                    "closest_csv_name_en": "", "closest_csv_name_np": "",
                    "closest_csv_code": "", "closest_csv_district": "",
                    "score": 0,
                })
                continue

            query = normalize(en_aliases[0])
            result = process.extractOne(query, candidates, scorer=fuzz.ratio)

            if result is None:
                unmatched.append({
                    "level": level, "canonical_key": key,
                    "your_aliases": " | ".join(aliases),
                    "closest_csv_name_en": "", "closest_csv_name_np": "",
                    "closest_csv_code": "", "closest_csv_district": "",
                    "score": 0,
                })
                continue

            match_str, score, idx = result
            row = csv.iloc[idx]

            if score >= MATCH_THRESHOLD:
                crosswalk[key] = int(row["locallevel_fullcode"])
                enrich_log[key] = {
                    "level": level,
                    "en": row["locallevel_name"],
                    "np": row["locallevel_name_nepali"],
                }
            else:
                # full context inline -- no need to cross-reference the CSV
                # by hand, the review file is self-contained
                unmatched.append({
                    "level": level, "canonical_key": key,
                    "your_aliases": " | ".join(aliases),
                    "closest_csv_name_en": row["locallevel_name"],
                    "closest_csv_name_np": row["locallevel_name_nepali"],
                    "closest_csv_code": int(row["locallevel_fullcode"]),
                    "closest_csv_district": row["district"],
                    "score": round(score, 1),
                })

    return crosswalk, enrich_log, unmatched


# ---- step 6: fold new spellings back into places.yaml ---------------------
def build_enriched_places(places, enrich_log):
    import copy
    enriched = copy.deepcopy(places)

    added_count = 0
    for key, info in enrich_log.items():
        level = info["level"]
        alias_list = enriched[level][key]
        for new_alias in [info["en"], info["np"]]:
            if new_alias not in alias_list:
                alias_list.append(new_alias)
                added_count += 1

    print(f"Added {added_count} new aliases across {len(enrich_log)} canonical keys.")
    return enriched


# ---- step 5 support: write the review file ---------------------------------
def write_review_csv(unmatched):
    df = pd.DataFrame(unmatched)
    df = df.sort_values("score", ascending=False)
    df.to_csv(REVIEW_OUT, index=False)
    print(f"{len(df)} entries need manual review -> {REVIEW_OUT}")


def main():
    print("=== step 3: testing normalize() ===")
    test_normalize()

    print("\n=== step 2: loading sources ===")
    places, csv = load_sources()

    print("\n=== step 4: fuzzy matching ===")
    crosswalk, enrich_log, unmatched = build_crosswalk(places, csv)
    print(f"Auto-matched: {len(crosswalk)}")
    print(f"Needs manual review: {len(unmatched)}")

    with open(CROSSWALK_OUT, "w", encoding="utf-8") as f:
        yaml.dump(crosswalk, f, allow_unicode=True, sort_keys=True)
    print(f"Wrote {CROSSWALK_OUT}")

    write_review_csv(unmatched)

    print("\n=== step 6: enriching places.yaml ===")
    enriched = build_enriched_places(places, enrich_log)
    with open(ENRICHED_OUT, "w", encoding="utf-8") as f:
        yaml.dump(enriched, f, allow_unicode=True, sort_keys=False, width=1000)
    print(f"Wrote {ENRICHED_OUT}")

    print("\nNext: open review_needed.csv, fix each row by hand, then add the")
    print("confirmed pairs into crosswalk.yaml yourself before moving to codes.yaml.")


if __name__ == "__main__":
    main()