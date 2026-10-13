"""End-to-end tests. The generated 'answer key' files are the ground truth."""
import re

import pandas as pd
import pytest

from src.generate_data import generate_all
from src.pipeline import main, run_pipeline


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    base = tmp_path_factory.mktemp("migration")
    data, out = base / "data", base / "output"
    generate_all(data)
    stats = run_pipeline(data / "sample_customers_messy.csv", data / "sample_invoices_old.csv",
                         data / "sample_invoices_new.csv", out, log=lambda *_: None)
    return {"data": data, "out": out, "stats": stats}


def read(path):
    return pd.read_csv(path, dtype=str)


def key_id(run, text):
    key = read(run["data"] / "answer_key_customers.csv")
    return key[key["issue"].str.contains(text, regex=False)]["customer_id"].iloc[0]


def test_only_the_planted_dates_change(run):
    """Regression: the original corrupted 116 of 301 dates. Exactly one should change."""
    raw = read(run["data"] / "sample_customers_messy.csv").set_index("customer_id")
    cleaned = read(run["out"] / "customers_cleaned.csv").set_index("customer_id")
    changed = raw.index[raw["registration_date"] != cleaned.loc[raw.index, "registration_date"]]
    assert list(changed) == [key_id(run, "Mixed date format")]
    assert cleaned.loc[changed[0], "registration_date"] == "2025-04-03"


def test_phones_keep_their_plus_and_are_all_international(run):
    final = read(run["out"] / "customers_final.csv")
    assert final["phone"].str.fullmatch(r"\+\d{8,15}").all()
    cid = key_id(run, "Mixed phone format")
    assert final.set_index("customer_id").at[cid, "phone"].startswith("+6421")


def test_email_fixed(run):
    final = read(run["out"] / "customers_final.csv").set_index("customer_id")
    assert "@@" not in "".join(final["email"].dropna())


def test_exactly_one_duplicate_removed_and_counted_correctly(run):
    raw = read(run["data"] / "sample_customers_messy.csv")
    final = read(run["out"] / "customers_final.csv")
    report = read(run["out"] / "duplicate_report.csv")
    assert len(raw) - len(final) == len(report) == 1
    assert run["stats"]["duplicates_removed"] == 1
    assert report.iloc[0]["customer_id"] == "CUST-0011-DUP"      # the original is kept
    assert "CUST-0011" in final["customer_id"].values


def test_validation_finds_exactly_the_planted_missing_company(run):
    errors = read(run["out"] / "validation_errors.csv")
    assert errors["customer_id"].tolist() == [key_id(run, "Missing required field")]


def test_reconciliation_matches_the_answer_key_exactly(run):
    key = read(run["data"] / "answer_key_invoices.csv")
    found = read(run["out"] / "reconciliation_results.csv")
    norm = lambda s: re.sub(r"\+ \$", "+$", s)                   # "+ $150.00" -> "+$150.00"
    expected = set(zip(key["invoice_num"], key["issue"].map(norm)))
    actual = set(zip(found["invoice_num"], found["issue"]))
    assert actual == expected


def test_summary_numbers(run):
    s = run["stats"]
    assert (s["customers_in"], s["customers_final"], s["customers_need_review"]) == (301, 300, 1)
    assert s["customers_ready"] == 299 and s["discrepancies"] == 11
    assert "Duplicates removed            : 1" in s["summary"]


def test_perfect_migration_runs_without_crashing_and_reports_zero(tmp_path):
    generate_all(tmp_path)
    old = tmp_path / "sample_invoices_old.csv"
    pd.read_csv(old).to_csv(tmp_path / "sample_invoices_new.csv", index=False)
    stats = run_pipeline(tmp_path / "sample_customers_messy.csv", old,
                         tmp_path / "sample_invoices_new.csv", tmp_path / "o", log=lambda *_: None)
    assert stats["discrepancies"] == 0


def test_no_stale_files_between_runs(tmp_path):
    generate_all(tmp_path)
    out = tmp_path / "o"
    args = (tmp_path / "sample_customers_messy.csv", tmp_path / "sample_invoices_old.csv",
            tmp_path / "sample_invoices_new.csv", out)
    run_pipeline(*args, log=lambda *_: None)
    assert len(read(out / "validation_errors.csv")) == 1
    # Fix the data so validation now passes: the old error file must not survive.
    fixed = read(tmp_path / "sample_customers_messy.csv")
    fixed["company_name"] = fixed["company_name"].fillna("Filled Ltd")
    fixed.to_csv(tmp_path / "sample_customers_messy.csv", index=False)
    stats = run_pipeline(*args, log=lambda *_: None)
    assert stats["validation_issues"] == 0 and len(read(out / "validation_errors.csv")) == 0


def test_cli_exit_codes(tmp_path, capsys):
    base = ["--data-dir", str(tmp_path), "--output-dir", str(tmp_path / "o")]
    assert main(base) == 2                                       # no input files yet
    assert "not found" in capsys.readouterr().err
    assert main(base + ["--generate"]) == 0
    assert main(base + ["--strict"]) == 1                        # issues exist -> non-zero
    assert main(base + ["--no-invoices"]) == 0


def test_missing_column_gives_friendly_error(tmp_path, capsys):
    pd.DataFrame({"customer_id": ["1"]}).to_csv(tmp_path / "bad.csv", index=False)
    code = main(["--customers", str(tmp_path / "bad.csv"), "--no-invoices",
                 "--output-dir", str(tmp_path / "o")])
    assert code == 2 and "missing column" in capsys.readouterr().err


def test_numeric_looking_columns_keep_leading_zeros_and_plus_signs(tmp_path):
    """Regression: without dtype=str pandas turns '0211234567' into 211234567."""
    pd.DataFrame({
        "customer_id": ["00123", "00124"], "first_name": ["A", "B"], "last_name": ["X", "Y"],
        "company_name": ["Co", "Co"], "email": ["a@x.com", "b@x.com"],
        "phone": ["0211234567", "0211234568"],            # all-numeric column
        "registration_date": ["2025-01-02", "2025-03-04"],
    }).to_csv(tmp_path / "c.csv", index=False)
    run_pipeline(tmp_path / "c.csv", None, None, tmp_path / "o", log=lambda *_: None)
    final = read(tmp_path / "o" / "customers_final.csv")
    assert final["customer_id"].tolist() == ["00123", "00124"]
    assert final["phone"].tolist() == ["+64211234567", "+64211234568"]
