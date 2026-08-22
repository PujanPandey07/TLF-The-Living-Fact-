# scripts/dedupe_vocab.py
import json
from collections import defaultdict


def dedupe_vocab(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # group by the actual (en, np) value pair
    grouped = defaultdict(list)
    for key, (en, np_) in raw.items():
        grouped[(en, np_)].append(key)

    unique = []
    for (en, np_), keys in grouped.items():
        namespaces = sorted({k.split(".", 1)[0] for k in keys})
        unique.append({
            "en": en,
            "np": np_,
            "source_keys": keys,
            "namespaces": namespaces,
            "n_duplicates": len(keys),
        })

    return unique, raw


if __name__ == "__main__":
    unique, raw = dedupe_vocab("fertility_pairs.json")  # your file
    print(f"raw entries: {len(raw)}")
    print(f"unique (en, np) pairs: {len(unique)}")

    # rough noise triage: chrome-y namespaces vs vocab-y namespaces
    CHROME_NS = {"footer", "header", "form", "home"}
    likely_chrome = [u for u in unique if set(u["namespaces"]) <= CHROME_NS]
    likely_vocab = [u for u in unique if u not in likely_chrome]
    print(f"likely chrome: {len(likely_chrome)}")
    print(f"likely vocab candidates: {len(likely_vocab)}")

    with open("vocab_deduped.json", "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
