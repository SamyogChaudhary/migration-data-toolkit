"""Build the human-readable migration summary."""
from datetime import datetime


def _breakdown(counts):
    if not counts:
        return "  (none)"
    return "\n".join(f"  - {name}: {n}" for name, n in sorted(counts.items()))


def build_report(stats, now=None):
    """Turn the pipeline's statistics dictionary into report text."""
    now = now or datetime.now()
    if stats["invoices_checked"]:
        invoices = (
            f"Old system invoices           : {stats['invoices_old']}\n"
            f"New system invoices           : {stats['invoices_new']}\n"
            f"Discrepancies found           : {stats['discrepancies']}\n"
            f"{_breakdown(stats['discrepancy_types'])}"
        )
    else:
        invoices = "Not run (no invoice files supplied)."

    return f"""================================================
      DATA MIGRATION SUMMARY REPORT
================================================
Date generated : {now.strftime('%Y-%m-%d %H:%M:%S')}

CUSTOMERS
------------------------------------------------
Records read                  : {stats['customers_in']}
Duplicates removed            : {stats['duplicates_removed']}
Records in final file         : {stats['customers_final']}
  Ready (no issues found)     : {stats['customers_ready']}
  Need human review           : {stats['customers_need_review']}
Validation issues found       : {stats['validation_issues']}
{_breakdown(stats['validation_types'])}

INVOICE RECONCILIATION
------------------------------------------------
{invoices}

ASSUMPTIONS (change these if they do not fit your data)
------------------------------------------------
- Non-ISO numeric dates are read as DD/MM/YYYY (day first).
- Phone numbers without a country code are treated as +{stats['country_code']} numbers.
- Duplicates = same first name, last name, email and phone (ignoring case).

NEXT STEPS
------------------------------------------------
A person should review validation_errors.csv, duplicate_report.csv and
reconciliation_results.csv before anything is imported into the new system.
This tool flags problems; it does not decide what is correct.
================================================
"""
