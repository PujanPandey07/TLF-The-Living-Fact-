"""
proposal_queue.py
-----------------
Persists unmapped values/fields from resolver output to a JSON queue file.
Deduplicates by (kind, category, raw_value) so the same misspelling across
50 files becomes one entry with seen_count=50.

Storage-agnostic interface: queue_path is a local file now, but can be
swapped for an API backend later without changing caller code.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


def _make_id(kind: str, category: str, raw_value: str) -> str:
    """Deterministic ID from the deduplication tuple."""
    payload = f"{kind}:{category}:{raw_value}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _load_queue(queue_path: str | Path) -> dict[str, Any]:
    """Load existing queue or return empty dict."""
    path = Path(queue_path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_queue(queue_path: str | Path, queue: dict[str, Any]) -> None:
    """Save queue back to disk with pretty printing."""
    path = Path(queue_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def queue_unmapped(
    unmapped: list[str],
    kind: str,
    category: str,
    source: str,
    queue_path: str | Path,
) -> None:
    """Append unmapped items to the proposal queue with deduplication.

    Args:
        unmapped: List of raw strings that failed resolution.
        kind: "value" or "field".
        category: The registry category (e.g. "sex", "citizenship_id").
        source: Identifier for the file/run that produced these unmapped items.
        queue_path: Path to the JSON queue file.
    """
    queue = _load_queue(queue_path)

    for raw_value in unmapped:
        entry_id = _make_id(kind, category, raw_value)

        if entry_id in queue:
            entry = queue[entry_id]
            entry["seen_count"] += 1
            if source not in entry["sources"]:
                entry["sources"].append(source)
        else:
            queue[entry_id] = {
                "id": entry_id,
                "kind": kind,
                "category": category,
                "raw_value": raw_value,
                "seen_count": 1,
                "sources": [source],
                "status": "pending",
                "resolved_to": None,
                "proposed_at": datetime.now(timezone.utc).isoformat(),
                "reviewed_at": None,
            }

    _save_queue(queue_path, queue)