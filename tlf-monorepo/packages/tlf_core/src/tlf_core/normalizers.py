"""
Value-level normalizers — fix problems INSIDE a column's data, not the
column header. Each function does one job, so they can be applied
independently depending on what a given field actually needs.
"""

import re
import pandas as pd

# ---------------------------------------------------------------------------
# 1. CASING & TEXT NORMALIZATION
# ---------------------------------------------------------------------------


def normalize_casing(value: str) -> str:
    """Single-value normalizer: lowercases text and strips leading/trailing whitespace."""
    if value is None:
        return value
    return str(value).strip().lower()


def normalize_column_casing(series: pd.Series) -> pd.Series:
    """Column-level normalizer: lowercases and trims an entire pandas Series."""
    return series.apply(
        lambda val: normalize_casing(val) if pd.notna(val) else val
    )


# ---------------------------------------------------------------------------
# 2. DEVANAGARI DIGIT TRANSLITERATION
# ---------------------------------------------------------------------------

DEVANAGARI_TO_ARABIC = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize_devanagari_digits(value: str) -> str:
    """Single-value normalizer: converts Devanagari numerals (०-९) to Arabic (0-9)."""
    if value is None:
        return value
    return str(value).translate(DEVANAGARI_TO_ARABIC)


def normalize_column_devanagari_digits(series: pd.Series) -> pd.Series:
    """Column-level normalizer: transliterates Devanagari digits across a pandas Series."""
    return series.apply(
        lambda val: normalize_devanagari_digits(val) if pd.notna(val) else val
    )


# ---------------------------------------------------------------------------
# 3. DATE & CALENDAR NORMALIZATION
# ---------------------------------------------------------------------------

MONTH_MAP = {
    # --- AD Months ---
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12",

    # --- Nepali BS Months (Devanagari) ---
    "बैशाख": "01", "वैशाख": "01",
    "जेठ": "02", "ज्येष्ठ": "02",
    "असार": "03", "आषाढ": "03",
    "साउन": "04", "श्रावण": "04",
    "भदौ": "05", "भाद्र": "05",
    "असोज": "06", "आश्विन": "06",
    "कात्तिक": "07", "कार्तिक": "07",
    "मंसिर": "08", "मार्ग": "08", "मङ्शिर": "08",
    "पुस": "09", "पौष": "09",
    "माघ": "10",
    "फागुन": "11", "फाल्गुन": "11",
    "चैत": "12", "चैत्र": "12",

    # --- Nepali BS Months (Romanized / English transliterated) ---
    "baishakh": "01", "baisakh": "01", "vaishakh": "01",
    "jestha": "02", "jeth": "02",
    "ashadh": "03", "asar": "03", "ashad": "03",
    "shrawan": "04", "saun": "04", "sawan": "04",
    "bhadra": "05", "bhadau": "05",
    "ashwin": "06", "asoj": "06", "ashoj": "06",
    "kartik": "07", "kattik": "07",
    "mangsir": "08", "mangaishr": "08", "marg": "08",
    "poush": "09", "pus": "09",
    "magh": "10",
    "falgun": "11", "phagun": "11", "fagoon": "11",
    "chaitra": "12", "chait": "12",
}

ORDINAL_PATTERN = re.compile(r"(\d+)(st|nd|rd|th)\b", re.IGNORECASE)
DATE_PATTERN = re.compile(
    r"^([^\s./\-]+)[./\-\s]+([^\s./\-]+)[./\-\s]+([^\s./\-]+)$")


def normalize_date(value: str) -> str:
    """Single-value date normalizer: converts dates to canonical YYYY-MM-DD format."""
    if value is None or not str(value).strip():
        return value

    clean_val = str(value).translate(DEVANAGARI_TO_ARABIC).strip()
    clean_val = ORDINAL_PATTERN.sub(r"\1", clean_val)
    clean_val = re.sub(r"\b(gate|गते)\b", "", clean_val,
                       flags=re.IGNORECASE).strip()

    match = DATE_PATTERN.match(clean_val)
    if not match:
        return clean_val

    p1, p2, p3 = [p.lower() for p in match.groups()]

    def parse_part(part: str):
        if part in MONTH_MAP:
            return "month", MONTH_MAP[part]
        if part.isdigit():
            val = int(part)
            if len(part) == 4:
                return "year", part
            if 1 <= val <= 32:
                return "num", part.zfill(2)
        return "unknown", part

    t1_type, t1_val = parse_part(p1)
    t2_type, t2_val = parse_part(p2)
    t3_type, t3_val = parse_part(p3)

    if t2_type == "month" and t3_type == "year":
        day, month, year = t1_val, t2_val, t3_val
    elif t1_type == "month" and t3_type == "year":
        month, day, year = t1_val, t2_val, t3_val
    elif t1_type == "year":
        year, month, day = t1_val, t2_val, t3_val
    elif t3_type == "year":
        day, month, year = t1_val, t2_val, t3_val
    else:
        return clean_val

    return f"{year}-{month}-{day}"


def normalize_column_date(series: pd.Series) -> pd.Series:
    """Column-level normalizer: normalizes date formats across a pandas Series."""
    return series.apply(
        lambda val: normalize_date(val) if pd.notna(val) else val
    )
