"""Duplicate customer detection (exact match on normalised fields)."""
import pandas as pd

DEDUPE_COLUMNS = ["first_name", "last_name", "email", "phone"]
_MISSING = "\x00missing\x00"


def find_duplicates(df, columns=DEDUPE_COLUMNS):
    """Split customers into (deduplicated table, report of removed duplicates).

    Matching ignores case and surrounding spaces. Of each group of duplicates, the
    record with the lowest customer_id is kept (so 'CUST-0011' beats 'CUST-0011-DUP'),
    regardless of the order rows happen to be in. The remaining rows keep their
    original order. The report lists only the REMOVED rows, each pointing at the
    record it duplicates in the `duplicate_of` column.
    """
    df = df.reset_index(drop=True)
    norm = (
        df[columns].astype("string")
        .apply(lambda s: s.str.strip().str.lower())
        .fillna(_MISSING)
    )
    preference = df["customer_id"].astype("string").sort_values(kind="stable").index

    first_seen = {}
    removed_to_kept = {}
    for idx, key in zip(preference, map(tuple, norm.loc[preference].to_numpy())):
        if key in first_seen:
            removed_to_kept[idx] = df.at[first_seen[key], "customer_id"]
        else:
            first_seen[key] = idx

    deduped = df.drop(index=list(removed_to_kept)).reset_index(drop=True)
    report = df.loc[list(removed_to_kept)].copy()
    report["duplicate_of"] = [removed_to_kept[i] for i in report.index]
    return deduped, report.reset_index(drop=True)
