"""
build_places_draft_v2.py — same inputs as build_places_draft.py, but
outputs in the exact shape of your real values.yaml: a top-level key
per admin level (gaunpalika, municipality, district, ...), and under
each, canonical_snake_case_key: [alias1, alias2, ...] — en and np
variants flattened into ONE list per place, matching how sex/religion/
etc. mix romanized and Devanagari aliases in the same list.

WHY A snake_case KEY (not the raw English name):
values.yaml's canonical keys are snake_case identifiers (male, chhetri,
hindu) — never the raw alias text itself. So the canonical key here is
a slugified version of the shortest en variant (aadarsh_gaunpalika,
kapilbastu_municipality). This is just a readable label for
FieldResolver/ValueResolver internals to key off of — rename any of
these by hand if a different spelling should be canonical.

Aliases are deduped (case-insensitive, whitespace-collapsed) since
values.yaml's own alias lists don't contain exact repeats — unlike the
raw en/np lists in the last draft, which deliberately kept raw
duplicates for review purposes. This version assumes you've done that
review pass already (or are doing it directly on this file instead).

USAGE:
    python build_places_draft_v2.py vocab_geo_candidates.json places_review.json places.yaml
"""

import json
import re
import sys

try:
    import yaml
except ImportError:
    print("pip install pyyaml --break-system-packages", file=sys.stderr)
    raise

LEVEL_SUFFIXES = [
    "sub-metropolitian city", "sub-metropolitan city",
    "metropolitian city", "metropolitan city",
    "rural municipality", "gaunpalika", "municipality",
]

LEVEL_KEY = {
    "sub-metropolitian city": "sub_metropolitan_city",
    "sub-metropolitan city": "sub_metropolitan_city",
    "metropolitian city": "metropolitan_city",
    "metropolitan city": "metropolitan_city",
    "rural municipality": "rural_municipality",
    "gaunpalika": "gaunpalika",
    "municipality": "municipality",
    "district_or_province": "district_or_province",
}


def slugify(name: str) -> str:
    n = name.lower()
    for suf in LEVEL_SUFFIXES:
        if n.endswith(suf):
            n = n[: -len(suf)].strip()
            break
    n = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    return n or "unnamed"


def dedupe_keep_order(items):
    seen = set()
    out = []
    for item in items:
        key = re.sub(r"\s+", " ", item.strip().lower())
        if key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def detect_level(name: str) -> str:
    n = name.lower()
    for suf in LEVEL_SUFFIXES:
        if n.endswith(suf):
            return suf
    return "district_or_province"


def main(candidates_path, review_path, out_path):
    with open(candidates_path, encoding="utf-8") as f:
        all_entries = json.load(f)
    with open(review_path, encoding="utf-8") as f:
        groups = json.load(f)

    grouped_en_names = set()
    for g in groups:
        for c in g["candidates"]:
            grouped_en_names.add(c["en"])

    result = {}  # level_key -> {canonical_key: [aliases]}

    def add(level_raw, canonical_source_name, aliases):
        level_key = LEVEL_KEY.get(level_raw, level_raw)
        result.setdefault(level_key, {})
        key = slugify(canonical_source_name)
        # guard against slug collisions across different groups
        base_key, n = key, 2
        while key in result[level_key]:
            key = f"{base_key}_{n}"
            n += 1
        result[level_key][key] = dedupe_keep_order(aliases)

    # 1. candidate-duplicate groups -> one canonical entry, all en+np merged
    for g in groups:
        candidates = g["candidates"]
        canonical_source = min((c["en"] for c in candidates), key=len)
        aliases = []
        for c in candidates:
            aliases.append(c["en"])
            aliases.append(c["np"])
        add(g["level"], canonical_source, aliases)

    # 2. ungrouped singles
    for e in all_entries:
        if "common" not in e.get("namespaces", []):
            continue
        if e["en"] in ("Select Municipality",):
            continue
        if e["en"] in grouped_en_names:
            continue
        level = detect_level(e["en"])
        add(level, e["en"], [e["en"], e["np"]])

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            "# places.yaml (DRAFT — review before treating as final)\n"
            "# Shape matches values.yaml: level -> canonical_key -> [aliases]\n"
            "# Canonical keys are auto-slugified from the shortest known en\n"
            "# spelling — rename any of them if you know a better official one.\n"
            "# Aliases mix en + np variants in one list, same as values.yaml.\n\n"
        )
        yaml.dump(result, f, allow_unicode=True, sort_keys=True,
                  default_flow_style=None)

    total_places = sum(len(v) for v in result.values())
    print(
        f"{total_places} places across {len(result)} levels written to {out_path}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
