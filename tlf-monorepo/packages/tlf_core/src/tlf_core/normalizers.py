"""
Value-level normalizers — fix problems INSIDE a column's data, not the
column header. Each function does one job, so they can be applied
independently depending on what a given field actually needs.

Only casing is implemented so far (Phase 3, scoped deliberately narrow).
Language, numeral, and date/calendar fixes are separate, harder problems —
see docs/data_quality_checklist.md — and are left as stubs until we come
back for them.
"""


def normalize_casing(value: str) -> str:
    """Fixes the confirmed Arghakhanchi vs ARGHAKHANCHI problem: lowercase +
    strip whitespace, so values can be compared/joined regardless of how they
    were originally cased.

    NOTE: this makes values comparable, it does not restore "proper" casing
    for display. If you need consistent display casing later (e.g. always
    Title Case for reports), that's a separate, presentation-layer concern.
    """
    if value is None:
        return value
    return value.strip().lower()


def normalize_devanagari_digits(value: str) -> str:
    """TODO (not yet implemented): transliterate Devanagari numerals (०-९)
    to Arabic numerals (0-9). Needed for the Pokhara phone-number finding.
    Left unimplemented until we have a real test case wired up — flagging
    the gap explicitly rather than guessing at an implementation."""
    raise NotImplementedError(
        "Devanagari digit normalization not yet built — see "
        "docs/data_quality_checklist.md finding #3"
    )


def normalize_date(value: str) -> str:
    """TODO (not yet implemented): needs two separate steps — format
    parsing (/, -, spelled-out months) AND BS/AD calendar conversion.
    The harder of the four confirmed problems; deliberately deferred until
    casing and header-resolution are proven working end to end.
    See docs/data_quality_checklist.md finding #4."""
    raise NotImplementedError(
        "Date/calendar normalization not yet built — see "
        "docs/data_quality_checklist.md finding #4"
    )
