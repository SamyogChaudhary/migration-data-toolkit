"""Business-rule validation for customer records.

Nothing is changed or dropped here: every problem is reported so a human can decide.
"""
import re
from datetime import date

import pandas as pd

from .clean import is_valid_iso_date

REQUIRED_FIELDS = ["customer_id", "first_name", "last_name", "company_name", "email"]
ISSUE_COLUMNS = ["customer_id", "field", "problem", "value"]

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_E164_PHONE = re.compile(r"^\+\d{8,15}$")


def _is_blank(series):
    s = series.astype("string")
    return s.isna() | s.str.strip().eq("").fillna(False)


def _flag(df, mask, field, problem):
    mask = mask.fillna(False).astype(bool)
    out = df.loc[mask, ["customer_id"]].copy()
    out["field"] = field
    out["problem"] = problem
    out["value"] = df.loc[mask, field]
    return out[ISSUE_COLUMNS]


def validate_customers(df):
    """Return a table of every rule violation (empty table if there are none)."""
    df = df.reset_index(drop=True)
    found = []

    for col in REQUIRED_FIELDS:
        found.append(_flag(df, _is_blank(df[col]), col, "missing required value"))

    present_email = ~_is_blank(df["email"])
    bad_email = ~df["email"].astype("string").str.match(_EMAIL).fillna(False)
    found.append(_flag(df, present_email & bad_email, "email", "not a valid email address"))

    present_phone = ~_is_blank(df["phone"])
    bad_phone = ~df["phone"].astype("string").str.match(_E164_PHONE).fillna(False)
    found.append(_flag(df, present_phone & bad_phone, "phone",
                       "not in international format (+<country><number>)"))

    present_date = ~_is_blank(df["registration_date"])
    dates = df["registration_date"].astype("string")
    bad_date = ~dates.map(is_valid_iso_date).astype(bool)
    found.append(_flag(df, present_date & bad_date, "registration_date",
                       "not a valid date (expected YYYY-MM-DD)"))
    future = present_date & ~bad_date & (dates > date.today().isoformat()).fillna(False)
    found.append(_flag(df, future, "registration_date", "date is in the future"))

    found.append(_flag(df, df["customer_id"].duplicated(keep=False),
                       "customer_id", "customer_id is not unique"))

    non_empty = [f for f in found if not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=ISSUE_COLUMNS)
    return pd.concat(non_empty, ignore_index=True)
