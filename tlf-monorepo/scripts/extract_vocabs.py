#!/usr/bin/env python3
"""
extract_vocab.py

Generic key-pairing extractor for TLF.

NSO's census site ships English and Nepali together in ONE JSON file,
nested under pageProps._nextI18Next.initialI18nStore, split first by
locale (np / en), then by "namespace" (header, common, population,
chart, chart-title, etc). Real vocabulary and UI chrome are mixed
together in every namespace.

This script:
  1. Finds the np and en trees inside that one file.
  2. Walks every namespace that exists in both.
  3. Pairs up every matching leaf key (e.g. common.male -> ["Male", "पुरुष"]).

Deliberately dumb on purpose: it does NOT know which pairs are real
vocabulary vs UI chrome (buttons, tooltips, page titles). That judgment
call is a manual review step done AFTER extraction, by looking at the
output file.

Usage:
    python extract_vocab.py source.json vocab_pairs.json
"""

import json
import sys


def extract_pairs(en_node, np_node, prefix=""):
    """
    Walk two JSON trees in parallel. Wherever a key exists in both trees
    and both values are plain strings, yield (full_key_path, en_value, np_value).

    Skips keys that exist in only one tree, or where the shapes mismatch
    (e.g. one side is a dict, the other a string) -- extraction stays
    best-effort, not strict.
    """
    if not isinstance(en_node, dict) or not isinstance(np_node, dict):
        return

    for key, en_value in en_node.items():
        if key not in np_node:
            continue

        np_value = np_node[key]
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(en_value, str) and isinstance(np_value, str):
            yield (full_key, en_value, np_value)
        elif isinstance(en_value, dict) and isinstance(np_value, dict):
            yield from extract_pairs(en_value, np_value, full_key)
        # else: shape mismatch -> skip


def main():
    if len(sys.argv) != 3:
        print("Usage: python extract_vocab.py <source.json> <output.json>")
        sys.exit(1)

    src_path, out_path = sys.argv[1], sys.argv[2]

    with open(src_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Navigate down to where np/en actually live.
    try:
        store = raw["pageProps"]["_nextI18Next"]["initialI18nStore"]
        np_data = store["np"]
        en_data = store["en"]
    except KeyError as e:
        print(f"Couldn't find expected structure -- missing key: {e}")
        print(
            "Check that this file matches the pageProps._nextI18Next.initialI18nStore.{np,en} shape.")
        sys.exit(1)

    pairs = {}
    # Walk every namespace present in both locales (header, common, population, chart, ...)
    shared_namespaces = set(np_data.keys()) & set(en_data.keys())
    for ns in sorted(shared_namespaces):
        for full_key, en_value, np_value in extract_pairs(en_data[ns], np_data[ns], prefix=ns):
            pairs[full_key] = [en_value, np_value]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"Namespaces found: {sorted(shared_namespaces)}")
    print(f"Extracted {len(pairs)} key pairs -> {out_path}")
    print("Review this file by hand before merging anything into values.yaml.")


if __name__ == "__main__":
    main()
