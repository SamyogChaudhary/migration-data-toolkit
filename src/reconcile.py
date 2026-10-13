"""Reconcile invoices between the old system and the new system."""
import pandas as pd

RESULT_COLUMNS = ["invoice_num", "issue", "old_amount", "new_amount", "difference"]


def _money(diff):
    """Format a signed dollar amount, e.g. +$150.00 or -$150.00."""
    return f"{'+' if diff > 0 else '-'}${abs(diff):.2f}"


def reconcile_invoices(old, new, rounding_threshold=1.00):
    """Compare two invoice tables and return a table of discrepancies.

    Amounts are compared in whole cents (never as floating-point dollars).
    Differences smaller than `rounding_threshold` dollars are labelled
    'Rounding Difference'; larger ones 'Amount Mismatch'.
    """
    old = old.copy()
    new = new.copy()
    for frame in (old, new):
        frame["invoice_num"] = frame["invoice_num"].astype("string").str.strip()
        frame["_cents"] = (pd.to_numeric(frame["amount"], errors="coerce") * 100).round()

    rows = []

    def add(inv, issue, old_c=None, new_c=None):
        old_amt = None if pd.isna(old_c) else old_c / 100
        new_amt = None if pd.isna(new_c) else new_c / 100
        diff = None if old_amt is None or new_amt is None else round(new_amt - old_amt, 2)
        rows.append({"invoice_num": inv, "issue": issue, "old_amount": old_amt,
                     "new_amount": new_amt, "difference": diff})

    for label, frame in (("Old", old), ("New", new)):
        for inv in frame.loc[frame.duplicated("invoice_num", keep=False), "invoice_num"].unique():
            add(inv, f"Duplicate in {label} System")

    # Compare one row per invoice number so duplicates cannot fan out the merge.
    merged = old.drop_duplicates("invoice_num").merge(
        new.drop_duplicates("invoice_num"),
        on="invoice_num", how="outer", suffixes=("_old", "_new"), indicator=True,
    )

    for _, r in merged[merged["_merge"] == "left_only"].iterrows():
        add(r["invoice_num"], "Missing in New System", r["_cents_old"], None)
    for _, r in merged[merged["_merge"] == "right_only"].iterrows():
        add(r["invoice_num"], "Only in New System", None, r["_cents_new"])

    for _, r in merged[merged["_merge"] == "both"].iterrows():
        c_old, c_new = r["_cents_old"], r["_cents_new"]
        if pd.isna(c_old) or pd.isna(c_new):
            add(r["invoice_num"], "Invalid Amount", c_old, c_new)
            continue
        diff_cents = int(c_new - c_old)
        if diff_cents != 0:
            diff = diff_cents / 100
            kind = "Rounding Difference" if abs(diff) < rounding_threshold else "Amount Mismatch"
            add(r["invoice_num"], f"{kind} ({_money(diff)})", c_old, c_new)
        if "customer_id_old" in merged.columns and "customer_id_new" in merged.columns:
            a, b = r["customer_id_old"], r["customer_id_new"]
            if str(a).strip() != str(b).strip():
                add(r["invoice_num"], f"Customer Mismatch ({a} -> {b})", c_old, c_new)

    if not rows:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    result = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    return result.sort_values(["invoice_num", "issue"], kind="stable").reset_index(drop=True)
