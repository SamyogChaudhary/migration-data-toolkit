import pandas as pd

from src.duplicates import find_duplicates


def make(rows):
    return pd.DataFrame(rows, columns=["customer_id", "first_name", "last_name", "email", "phone"])


def test_removes_exact_duplicate_and_reports_it():
    df = make([("C1", "Ann", "Lee", "a@x.com", "+6421"), ("C2", "Bob", "Ray", "b@x.com", "+6422"),
               ("C1-DUP", "Ann", "Lee", "a@x.com", "+6421")])
    final, report = find_duplicates(df)
    assert len(final) == 2 and len(report) == 1
    assert report.iloc[0]["customer_id"] == "C1-DUP"
    assert report.iloc[0]["duplicate_of"] == "C1"


def test_keeps_lowest_id_even_if_the_copy_comes_first():
    df = make([("C1-DUP", "Ann", "Lee", "a@x.com", "+6421"), ("C1", "Ann", "Lee", "a@x.com", "+6421")])
    final, report = find_duplicates(df)
    assert final["customer_id"].tolist() == ["C1"]


def test_matching_ignores_case_and_spaces():
    df = make([("C1", "Ann", "Lee", "a@x.com", "+6421"), ("C2", " ann ", "LEE", "A@X.COM", "+6421")])
    assert len(find_duplicates(df)[0]) == 1


def test_different_people_are_not_merged():
    df = make([("C1", "Ann", "Lee", "a@x.com", "+6421"), ("C2", "Ann", "Lee", "a@x.com", "+6499")])
    assert len(find_duplicates(df)[0]) == 2


def test_no_duplicates_gives_empty_report_and_unchanged_order():
    df = make([("C2", "B", "B", "b@x.com", "1"), ("C1", "A", "A", "a@x.com", "2")])
    final, report = find_duplicates(df)
    assert report.empty and final["customer_id"].tolist() == ["C2", "C1"]


def test_removed_count_is_rows_removed_not_rows_involved():
    df = make([("C1", "A", "A", "a@x.com", "1"), ("C1b", "A", "A", "a@x.com", "1"),
               ("C1c", "A", "A", "a@x.com", "1")])
    final, report = find_duplicates(df)
    assert len(df) - len(final) == len(report) == 2
