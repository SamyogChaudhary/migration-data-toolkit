import pandas as pd
import pytest

from src.clean import clean_customers, clean_date, clean_email, clean_phone


@pytest.mark.parametrize("iso", ["2025-03-04", "2025-12-01", "2025-01-02", "2025-11-12"])
def test_iso_dates_are_never_reinterpreted(iso):
    # Regression test: the original code swapped day/month on ISO dates like these.
    assert clean_date(iso) == iso


@pytest.mark.parametrize("raw, expected", [
    ("03/04/2025", "2025-04-03"),        # day-first assumption
    ("13/04/2025", "2025-04-13"),
    ("3-4-2025", "2025-04-03"),
    ("2025/03/04", "2025-03-04"),
    ("4 March 2025", "2025-03-04"),
    ("March 4, 2025", "2025-03-04"),
])
def test_known_formats_are_converted(raw, expected):
    assert clean_date(raw) == expected


@pytest.mark.parametrize("bad", ["garbage", "04/13/2025", "2025-02-30", "31/02/2025"])
def test_unparseable_dates_are_kept_for_validation_not_dropped(bad):
    assert clean_date(bad) == bad


def test_missing_date_stays_missing():
    assert pd.isna(clean_date(None)) and pd.isna(clean_date(float("nan")))


@pytest.mark.parametrize("raw", [
    "021 123 4567", "+64 21 123 4567", "+6421 1234567", "0064 21 123 4567",
    "(021) 123-4567", "+64 (0)21 123 4567", " 021-123-4567 ",
])
def test_phone_variants_converge_on_one_format(raw):
    assert clean_phone(raw) == "+64211234567"


def test_phone_without_digits_has_no_information():
    assert clean_phone("N/A") is None
    assert pd.isna(clean_phone(None))


def test_phone_country_code_is_configurable():
    assert clean_phone("0412 345 678", country_code="61") == "+61412345678"


def test_ambiguous_phone_is_left_for_validation():
    assert clean_phone("1234567") == "1234567"


@pytest.mark.parametrize("raw, expected", [
    ("john@@example.com", "john@example.com"),
    ("  John.Smith@Example.COM ", "john.smith@example.com"),
])
def test_email_cleaning(raw, expected):
    assert clean_email(raw) == expected


def test_clean_customers_does_not_modify_input():
    df = pd.DataFrame({"first_name": [" A  b "], "last_name": ["x"], "company_name": [""],
                       "email": ["a@@b.com"], "phone": ["021 123 4567"],
                       "registration_date": ["03/04/2025"]})
    before = df.copy()
    out = clean_customers(df)
    pd.testing.assert_frame_equal(df, before)
    assert out.at[0, "first_name"] == "A b"
    assert pd.isna(out.at[0, "company_name"])
    assert out.at[0, "phone"] == "+64211234567"
