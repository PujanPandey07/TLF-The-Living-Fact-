"""
dedupe_places_fixed.py — same logic as dedupe_places.py, with the
write-before-compute bug fixed, and difflib.SequenceMatcher standing
in for rapidfuzz (this sandbox has no network access to pip install).
In your own environment, use the original with rapidfuzz — the ratio
scores won't be identical but the grouping behavior will be similar.
"""

import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher

LEVEL_SUFFIXES = [
    "sub-metropolitian city",
    "sub-metropolitan city",
    "metropolitian city",
    "metropolitan city",
    "rural municipality",
    "gaunpalika",
    "municipality",
]


def normalize(name: str) -> str:
    n = name.lower().strip()
    for suffix in LEVEL_SUFFIXES:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
            break
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def detect_level(name: str) -> str:
    n = name.lower()
    for suffix in LEVEL_SUFFIXES:
        if n.endswith(suffix):
            return suffix
    return "unknown"


def fuzz_ratio(a: str, b: str) -> float:
    # stand-in for rapidfuzz.fuzz.token_sort_ratio: sort tokens, then compare
    a_sorted = " ".join(sorted(a.split()))
    b_sorted = " ".join(sorted(b.split()))
    return SequenceMatcher(None, a_sorted, b_sorted).ratio() * 100


def main(path: str, out_path: str):
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)

    place_entries = [
        e for e in entries
        if "common" in e.get("namespaces", [])
        and e["en"] not in ("Select Municipality",)
        and any(e["en"].lower().endswith(suf) for suf in LEVEL_SUFFIXES)
    ]

    buckets = defaultdict(list)
    for e in place_entries:
        level = detect_level(e["en"])
        buckets[level].append(e)

    groups = []
    for level, items in buckets.items():
        used = set()
        for i, a in enumerate(items):
            if i in used:
                continue
            group = [a]
            used.add(i)
            norm_a = normalize(a["en"])
            for j, b in enumerate(items):
                if j in used or j <= i:
                    continue
                norm_b = normalize(b["en"])
                score = fuzz_ratio(norm_a, norm_b)
                if score >= 85:
                    group.append(b)
                    used.add(j)
            if len(group) > 1:
                groups.append({"level": level, "candidates": group})

    groups.sort(key=lambda g: -len(g["candidates"]))

    # write/print block now correctly comes AFTER groups is built
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)

    print(json.dumps(groups, ensure_ascii=False, indent=2))
    print(
        f"\n# {len(groups)} candidate groups found across "
        f"{len(place_entries)} place entries. Review before merging.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(
        sys.argv) > 2 else "places_review.json")
