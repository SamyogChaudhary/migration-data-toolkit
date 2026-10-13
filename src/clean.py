"""Field-level cleaning functions for customer records.

Two rules guide everything in this file:

1. Never silently destroy data. If a value cannot be cleaned with confidence it is
   returned (trimmed) unchanged, and validate.py flags it for a human to review.
2. Values that are already in the target format must pass through untouched.
"""
import re
from datetime import datetime

import pandas as pd

DEFAULT_COUNTRY_CODE = "64"  # New Zealand. Change this for other countries.

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Tried in order. Day-first (DD/MM/YYYY) is assumed for ambiguous numeric dates,
# because that is the convention in NZ/UK/AU. This is an ASSUMPTION - see README.
_OTHER_DATE_FORMATS = (
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%Y/%m/%d",
    "%d %B %Y", "%d %b %Y", "%B %d %Y", "%B %d, %Y",
)


def is_valid_iso_date(text):
    """True only for a real calendar date written as YYYY-MM-DD."""
    if not isinstance(text, str) or not _ISO_DATE.match(text):
        return False
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def clean_date(value):
    """Convert known date formats to YYYY-MM-DD.

    Already-ISO dates are returned unchanged and are NEVER reinterpreted
    (the original version swapped day and month on ISO dates).
    Unrecognised dates are returned unchanged so validate.py can flag them.
    """
    if pd.isna(value):
        return value
    text = str(value).strip()
    if _ISO_DATE.match(text):
        return text
    for fmt in _OTHER_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def clean_phone(phone, country_code=DEFAULT_COUNTRY_CODE):
    """Normalise phone numbers to international format, e.g. +64211234567.

    - "+64 21 123 4567", "0064 21 123 4567" and "021 123 4567" all become +64211234567
    - A value with no digits at all (e.g. "N/A") has no phone information -> None
    - Anything ambiguous is returned as plain digits for validate.py to flag
    """
    if pd.isna(phone):
        return phone
    raw = str(phone).strip()
    has_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if has_plus:
        # "+64 (0)21 ..." -> the (0) trunk prefix must be dropped
        if digits.startswith(country_code + "0"):
            digits = country_code + digits[len(country_code) + 1:]
        return "+" + digits
    if digits.startswith("00"):
        return "+" + digits[2:]
    if digits.startswith("0"):
        return f"+{country_code}{digits[1:]}"
    return digits


def clean_email(email):
    """Trim, lowercase, and collapse accidental repeated @ signs."""
    if pd.isna(email):
        return email
    text = re.sub(r"@{2,}", "@", str(email).strip().lower())
    return text or None


def _tidy_text(value):
    """Trim and collapse repeated whitespace; empty strings become missing."""
    if pd.isna(value):
        return value
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def clean_customers(df, country_code=DEFAULT_COUNTRY_CODE):
    """Return a cleaned COPY of the customer table."""
    out = df.copy()
    for col in ("first_name", "last_name", "company_name"):
        if col in out.columns:
            out[col] = out[col].map(_tidy_text)
    out["phone"] = out["phone"].map(lambda p: clean_phone(p, country_code))
    out["registration_date"] = out["registration_date"].map(clean_date)
    out["email"] = out["email"].map(clean_email)
    return out
