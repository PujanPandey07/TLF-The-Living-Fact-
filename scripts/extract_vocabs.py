"""
scripts/split_vocab.py

Takes vocab_deduped.json (the (en, np, source_keys, namespaces) rows from
dedupe_vocab.py) and splits it into three files:

  vocab_geo_candidates.json  -> place names (feeds tlf-geo later)
  vocab_chrome.json          -> UI text, not real vocabulary, archived
  vocab_review.json          -> everything else — the real values.yaml pile

Rules are heuristics, not perfect. A few rows will land in the wrong
bucket (especially in `common`, which mixes place names and UI labels).
Spot-check the edges rather than trusting every row blindly.
"""
import json
import re

CHROME_ONLY_NS = {"footer", "form", "home"}

# Header namespace is genuinely mixed — some are chrome ("Home", "Language"),
# some are real category labels that happen to also live elsewhere
# ("Religion", "Disability"). If a header row's value ALSO appears under
# chart/population (i.e. namespaces has more than just header/common/footer),
# it's real. If header is the ONLY namespace, treat as chrome by default.
PLACE_SUFFIXES = ("Gaunpalika", "Municipality", "Metropolitian City",
                  "Metropolitan City", "Sub-Metropolitian City")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"{path}: {len(rows)} rows")


def looks_like_place(row):
    en = row["en"]
    if any(suf in en for suf in PLACE_SUFFIXES):
        return True
    # common.province_1..7 pattern, or single-word district names under
    # a 'common' key that isn't obviously a UI label
    if row["namespaces"] == ["common"]:
        keys = row["source_keys"]
        if any(re.search(r"province_\d", k) for k in keys):
            return True
        # District names: single capitalized word, no spaces, and the
        # key itself is lowercase (common.achham, common.baglung, etc)
        # -- this is the census site's district-list pattern
        if all(re.fullmatch(r"common\.[a-z_]+", k) for k in keys) \
           and en[0:1].isupper() and " " not in en:
            return True
    return False


def is_pure_chrome(row):
    ns = set(row["namespaces"])
    return ns.issubset(CHROME_ONLY_NS)


def is_header_only_chrome(row):
    return row["namespaces"] == ["header"]


def split(vocab):
    geo, chrome, review = [], [], []
    for row in vocab:
        if looks_like_place(row):
            geo.append(row)
        elif is_pure_chrome(row):
            chrome.append(row)
        elif is_header_only_chrome(row):
            chrome.append(row)
        else:
            review.append(row)
    return geo, chrome, review


if __name__ == "__main__":
    vocab = load("vocab_deduped.json")  # adjust filename if different
    geo, chrome, review = split(vocab)

    save("vocab_geo_candidates.json", geo)
    save("vocab_chrome.json", chrome)
    save("vocab_review.json", review)

    print(
        f"\ntotal in: {len(vocab)}  total out: {len(geo)+len(chrome)+len(review)}")
