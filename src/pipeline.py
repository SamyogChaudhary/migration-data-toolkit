"""One command that runs every step: clean -> deduplicate -> validate -> reconcile -> report.

    python -m src --generate        # make sample data, then run everything
    python -m src --customers my.csv --invoices-old a.csv --invoices-new b.csv
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

from .clean import DEFAULT_COUNTRY_CODE, clean_customers
from .duplicates import find_duplicates
from .reconcile import reconcile_invoices
from .report import build_report
from .validate import validate_customers

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CUSTOMER_COLUMNS = ["customer_id", "first_name", "last_name", "company_name",
                    "email", "phone", "registration_date"]
INVOICE_COLUMNS = ["invoice_num", "amount"]


class InputError(Exception):
    """The user's input files are missing or malformed (shown without a traceback)."""


def _read_csv(path, required, label):
    path = Path(path)
    if not path.exists():
        raise InputError(f"{label} file not found: {path}")
    # dtype=str is essential: otherwise pandas turns '+6421...' / '021...' into numbers
    # and silently strips the '+' and leading zeros.
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise InputError(f"{label} file {path.name} is missing column(s): {', '.join(missing)}")
    return df


def _counts(series):
    return {k: int(v) for k, v in series.value_counts().items()}


def run_pipeline(customers_path, invoices_old_path=None, invoices_new_path=None,
                 output_dir=None, country_code=DEFAULT_COUNTRY_CODE, log=print):
    """Run all steps, write every output file, and return a statistics dictionary."""
    out = Path(output_dir or PROJECT_ROOT / "output")
    out.mkdir(parents=True, exist_ok=True)
    check_invoices = invoices_old_path is not None and invoices_new_path is not None

    log("[1/5] Loading customers...")
    raw = _read_csv(customers_path, CUSTOMER_COLUMNS, "Customers")

    log("[2/5] Cleaning fields...")
    cleaned = clean_customers(raw, country_code)
    cleaned.to_csv(out / "customers_cleaned.csv", index=False)

    log("[3/5] Removing duplicates...")
    final, removed = find_duplicates(cleaned)
    final.to_csv(out / "customers_final.csv", index=False)
    removed.to_csv(out / "duplicate_report.csv", index=False)

    log("[4/5] Validating...")
    issues = validate_customers(final)
    issues.to_csv(out / "validation_errors.csv", index=False)  # always written: no stale files

    stats = {
        "customers_in": len(raw),
        "duplicates_removed": len(removed),
        "customers_final": len(final),
        "validation_issues": len(issues),
        "validation_types": _counts(issues["field"] + ": " + issues["problem"]) if len(issues) else {},
        "invoices_checked": check_invoices,
        "country_code": country_code,
        "output_dir": str(out),
    }
    flagged = issues["customer_id"].dropna().nunique()
    stats["customers_need_review"] = int(flagged)
    stats["customers_ready"] = len(final) - int(flagged)

    results_file = out / "reconciliation_results.csv"
    if check_invoices:
        log("[5/5] Reconciling invoices...")
        old = _read_csv(invoices_old_path, INVOICE_COLUMNS, "Old invoices")
        new = _read_csv(invoices_new_path, INVOICE_COLUMNS, "New invoices")
        result = reconcile_invoices(old, new)
        result.to_csv(results_file, index=False)
        stats.update(
            invoices_old=len(old), invoices_new=len(new), discrepancies=len(result),
            discrepancy_types=_counts(result["issue"].str.split(" \\(", regex=True).str[0]) if len(result) else {},
        )
    else:
        log("[5/5] Skipping invoice reconciliation.")
        results_file.unlink(missing_ok=True)  # never leave a stale file behind

    summary = build_report(stats)
    (out / "migration_summary.txt").write_text(summary, encoding="utf-8")
    stats["summary"] = summary
    return stats


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m src", description="Migration Data Toolkit")
    p.add_argument("--data-dir", default=str(PROJECT_ROOT / "data"), help="folder with input files")
    p.add_argument("--output-dir", default=str(PROJECT_ROOT / "output"), help="folder for results")
    p.add_argument("--customers", help="customer CSV (default: <data-dir>/sample_customers_messy.csv)")
    p.add_argument("--invoices-old", help="old-system invoice CSV")
    p.add_argument("--invoices-new", help="new-system invoice CSV")
    p.add_argument("--no-invoices", action="store_true", help="skip invoice reconciliation")
    p.add_argument("--generate", action="store_true", help="generate synthetic sample data first")
    p.add_argument("--country-code", default=DEFAULT_COUNTRY_CODE,
                   help="default phone country code (default: 64 = New Zealand)")
    p.add_argument("--strict", action="store_true",
                   help="exit with code 1 if any issue or discrepancy is found (for automation)")
    args = p.parse_args(argv)

    data = Path(args.data_dir)
    try:
        if args.generate:
            from .generate_data import generate_all
            generate_all(data)
        customers = args.customers or data / "sample_customers_messy.csv"
        old = new = None
        if not args.no_invoices:
            old = args.invoices_old or data / "sample_invoices_old.csv"
            new = args.invoices_new or data / "sample_invoices_new.csv"
        stats = run_pipeline(customers, old, new, args.output_dir, args.country_code)
    except InputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Tip: use --generate to create sample data, or --no-invoices to skip reconciliation.",
              file=sys.stderr)
        return 2

    print("\n" + stats["summary"])
    print(f"All files written to: {stats['output_dir']}")
    problems = stats["validation_issues"] + stats.get("discrepancies", 0)
    return 1 if args.strict and problems else 0


if __name__ == "__main__":
    sys.exit(main())
