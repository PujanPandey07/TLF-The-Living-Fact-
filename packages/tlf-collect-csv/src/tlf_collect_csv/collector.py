"""
Phase 3: CSV collector, now optionally wired into tlf-core.

Still does NOT do:
- BS/AD date handling
- numeral transliteration
- missing-value normalization
(all still NotImplementedError in tlf_core.normalizers — see docs/data_quality_checklist.md)

What it NOW does, if you pass a FieldResolver:
- resolves known column-header aliases to canonical names (e.g. "Area/Sex" -> "area_sex")
- lowercases/strips string values (fixes the real Arghakhanchi-casing problem)
- reports which columns it could NOT resolve, instead of silently guessing

Both are opt-in (via the `resolver` and `normalize_string_values` params) so
the dumb Phase 2 behavior is still available by just not passing them.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tlf_core import FieldResolver, normalize_casing


@dataclass
class CollectionResult:
    """What every collector hands back. Kept minimal for now —
    this will likely move into tlf-core once more collectors exist
    and need to share the same shape (see docs/decisions.md)."""

    data: pd.DataFrame
    source: str
    collected_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    unmapped_columns: list[str] = field(default_factory=list)


def collect_csv(
    path: str | Path,
    resolver: FieldResolver | None = None,
    normalize_string_values: bool = False,
) -> CollectionResult:
    """Read a CSV file.

    If `resolver` is provided, known column headers get renamed to their
    canonical form; unrecognized ones are reported in `unmapped_columns`
    rather than silently left as-is or guessed at.

    If `normalize_string_values` is True, all string/object columns get
    casing-normalized (lowercased + stripped) — fixes the confirmed
    Arghakhanchi-vs-ARGHAKHANCHI problem. Off by default since it changes
    the data, not just its shape, and callers should opt in deliberately.

    Raises FileNotFoundError if the path doesn't exist, and whatever
    pandas raises if the file isn't valid CSV.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path)
    unmapped: list[str] = []

    if resolver is not None:
        rename_map, unmapped = resolver.resolve_columns(list(df.columns))
        df = df.rename(columns=rename_map)

    if normalize_string_values:
        string_cols = df.select_dtypes(include="object").columns
        for col in string_cols:
            df[col] = df[col].apply(
                lambda v: normalize_casing(v) if isinstance(v, str) else v
            )

    return CollectionResult(
        data=df,
        source=str(path),
        unmapped_columns=unmapped,
    )
