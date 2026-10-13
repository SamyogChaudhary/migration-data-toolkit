import pandas as pd

from src.validate import validate_customers


def good_row(**over):
    row = {"customer_id": "C1", "first_name": "Ann", "last_name": "Lee", "company_name": "Lee Ltd",
           "email": "ann@x.com", "phone": "+64211234567", "registration_date": "2025-03-04"}
    row.update(over)
    return row


def problems(rows):
    out = validate_customers(pd.DataFrame(rows))
    return set(zip(out["customer_id"], out["field"], out["problem"]))


def test_clean_data_has_no_issues():
    result = validate_customers(pd.DataFrame([good_row()]))
    assert result.empty and list(result.columns) == ["customer_id", "field", "problem", "value"]


def test_missing_company_is_flagged():
    assert ("C1", "company_name", "missing required value") in problems([good_row(company_name=None)])


def test_blank_string_counts_as_missing():
    assert ("C1", "first_name", "missing required value") in problems([good_row(first_name="  ")])


def test_bad_email_phone_and_dates_are_flagged():
    found = problems([good_row(email="john@x", phone="12345", registration_date="2025-02-30")])
    assert ("C1", "email", "not a valid email address") in found
    assert any(f == "phone" for _, f, _ in found)
    assert ("C1", "registration_date", "not a valid date (expected YYYY-MM-DD)") in found


def test_future_date_is_flagged():
    assert ("C1", "registration_date", "date is in the future") in problems(
        [good_row(registration_date="2999-01-01")])


def test_duplicate_ids_are_flagged():
    found = problems([good_row(), good_row(email="b@x.com")])
    assert ("C1", "customer_id", "customer_id is not unique") in found


def test_missing_optional_phone_is_not_an_error():
    assert validate_customers(pd.DataFrame([good_row(phone=None)])).empty
