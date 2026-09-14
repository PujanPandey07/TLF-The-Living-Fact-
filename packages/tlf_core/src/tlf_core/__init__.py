from pathlib import Path

# ← confirm this filename is actually correct
from .registry import FieldResolver
from .value_registry import ValueResolver
from .normalizers import (
    normalize_casing,
    normalize_column_casing,
    normalize_devanagari_digits,
    normalize_column_devanagari_digits,
    normalize_date,
    normalize_column_date,
    normalize_whitespace_artifacts,
    normalize_column_whitespace_artifacts,
    normalize_chrome_symbols,
    normalize_column_chrome_symbols,
    normalize_phone_number,
    normalize_column_phone_number,
)
from . import proposal_queue
from . import review_queue

__version__ = "0.1.2"  # ← bump from 0.1.0, matching your pyproject.toml

__all__ = [
    "FieldResolver",
    "ValueResolver",
    "normalize_casing",
    "normalize_column_casing",
    "normalize_devanagari_digits",
    "normalize_column_devanagari_digits",
    "normalize_date",
    "normalize_column_date",
    "normalize_whitespace_artifacts",
    "normalize_column_whitespace_artifacts",
    "normalize_chrome_symbols",
    "normalize_column_chrome_symbols",
    "normalize_phone_number",
    "normalize_column_phone_number",
    "default_registry_path",
    "proposal_queue",
    "review_queue",
    "__version__",
]


def default_registry_path(filename: str) -> Path:
    """Return the path to a bundled registry YAML (fields.yaml or values.yaml)."""
    return Path(__file__).parent / "data" / filename
