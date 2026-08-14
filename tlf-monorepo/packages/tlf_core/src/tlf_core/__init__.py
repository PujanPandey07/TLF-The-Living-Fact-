from .registry import FieldResolver
from .value_registry import ValueResolver
from .normalizers import (
    normalize_casing,
    normalize_devanagari_digits,
    normalize_date,
    normalize_whitespace_artifacts,
    normalize_chrome_symbols,
    normalize_phone_number,
)

__version__ = "0.1.0"

__all__ = [
    "FieldResolver",
    "ValueResolver",
    "normalize_casing",
    "normalize_devanagari_digits",
    "normalize_date",
    "normalize_whitespace_artifacts",
    "normalize_chrome_symbols",
    "normalize_phone_number",
    "__version__",
]
