"""
review_queue.py
---------------
Interactive CLI for reviewing pending proposals from queue.json and merging
approved entries directly into fields.yaml or values.yaml.

Usage:
    tlf-review queue.json values.yaml value
    tlf-review queue.json fields.yaml field
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

import yaml


def _load(path: str | Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save(path: str | Path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True,
                  sort_keys=False, default_flow_style=None)


def _snake_case(raw: str) -> str:
    """Convert a raw string to a reasonable snake_case key."""
    import re
    clean = re.sub(r"[^\w\s]", "", raw)
    clean = re.sub(r"\s+", "_", clean.strip())
    return clean.lower()


def _review_values(queue: dict, registry: dict, entry: dict) -> bool:
    """Handle approval for a values.yaml entry. Returns True if registry was modified."""
    category = entry["category"]
    raw_value = entry["raw_value"]

    if category not in registry:
        registry[category] = {}

    existing_keys = list(registry[category].keys())

    print(f"\n  Existing keys in '{category}': {existing_keys or '(none)'}")
    print(f"  Enter canonical key to merge into, blank for new key, or 'skip'/'reject': ", end="")

    choice = input().strip()

    if choice.lower() == "skip":
        return False

    if choice.lower() == "reject":
        entry["status"] = "rejected"
        entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        return False

    if not choice:
        # Create new canonical key
        choice = _snake_case(raw_value)
        registry[category][choice] = []
        print(f"  -> Created new key: '{choice}'")

    if choice not in registry[category]:
        registry[category][choice] = []

    if raw_value not in registry[category][choice]:
        registry[category][choice].append(raw_value)
        print(f"  -> Added '{raw_value}' as alias for '{choice}'")

    entry["status"] = "approved"
    entry["resolved_to"] = choice
    entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    return True


def _review_fields(queue: dict, registry: dict, entry: dict) -> bool:
    """Handle approval for a fields.yaml entry. Returns True if registry was modified."""
    raw_value = entry["raw_value"]
    existing_keys = list(registry.keys())

    print(f"\n  Existing field keys: {existing_keys or '(none)'}")
    print(f"  Enter canonical key to merge into, blank for new key, or 'skip'/'reject': ", end="")

    choice = input().strip()

    if choice.lower() == "skip":
        return False

    if choice.lower() == "reject":
        entry["status"] = "rejected"
        entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        return False

    if not choice:
        choice = _snake_case(raw_value)
        registry[choice] = {
            "description": "",
            "aliases": [],
            "data_type": "string",
        }
        print(f"  -> Created new field: '{choice}'")

    if choice not in registry:
        registry[choice] = {
            "description": "",
            "aliases": [],
            "data_type": "string",
        }

    if raw_value not in registry[choice].get("aliases", []):
        registry[choice]["aliases"].append(raw_value)
        print(f"  -> Added '{raw_value}' as alias for '{choice}'")

    entry["status"] = "approved"
    entry["resolved_to"] = choice
    entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    return True


def main():
    if len(sys.argv) != 4:
        print("Usage: tlf-review <queue.json> <registry.yaml> <kind>")
        print("  kind: 'value' (values.yaml) or 'field' (fields.yaml)")
        sys.exit(1)

    queue_path = Path(sys.argv[1])
    registry_path = Path(sys.argv[2])
    kind = sys.argv[3]

    if kind not in ("value", "field"):
        print("Error: kind must be 'value' or 'field'")
        sys.exit(1)

    queue = _load(queue_path)
    registry = _load(registry_path)

    # Filter pending, sort by most seen first
    pending = [
        entry for entry in queue.values()
        if entry.get("status") == "pending"
    ]
    pending.sort(key=lambda e: e["seen_count"], reverse=True)

    if not pending:
        print("No pending entries.")
        return

    modified_queue = False
    modified_registry = False

    for entry in pending:
        print(f"\n{'='*50}")
        print(f"Raw: '{entry['raw_value']}'")
        print(
            f"Category: {entry['category']}  |  Seen: {entry['seen_count']} times")
        print(
            f"Sources: {', '.join(entry['sources'][:3])}{'...' if len(entry['sources']) > 3 else ''}")

        if kind == "value":
            changed = _review_values(queue, registry, entry)
        else:
            changed = _review_fields(queue, registry, entry)

        if changed:
            modified_registry = True
            _save(registry_path, registry)
            print(f"  -> Saved to {registry_path}")

        modified_queue = True
        _save(queue_path, queue)
        print(f"  -> Updated queue status: {entry['status']}")

    print(f"\nDone. Reviewed {len(pending)} entries.")


if __name__ == "__main__":
    main()
