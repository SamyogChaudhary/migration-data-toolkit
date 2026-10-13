import pandas as pd

from src.reconcile import reconcile_invoices


def inv(rows):
    return pd.DataFrame(rows, columns=["invoice_num", "customer_id", "amount"])


OLD = inv([("I1", "C1", 100.00), ("I2", "C2", 200.00), ("I3", "C3", 300.00), ("I4", "C4", 400.00)])


def issues(old, new):
    r = reconcile_invoices(old, new)
    return dict(zip(r["invoice_num"] + "|" + r["issue"], r["difference"]))


def test_perfect_migration_returns_empty_table_with_columns():
    r = reconcile_invoices(OLD, OLD.copy())
    assert r.empty and "issue" in r.columns


def test_missing_and_extra_invoices():
    new = inv([("I1", "C1", 100.00), ("I2", "C2", 200.00), ("I3", "C3", 300.00), ("I9", "C9", 5.00)])
    found = issues(OLD, new)
    assert "I4|Missing in New System" in found
    assert "I9|Only in New System" in found


def test_amount_mismatch_has_correct_sign_both_directions():
    new = inv([("I1", "C1", 250.00), ("I2", "C2", 50.00), ("I3", "C3", 300.00), ("I4", "C4", 400.00)])
    found = issues(OLD, new)
    assert found["I1|Amount Mismatch (+$150.00)"] == 150.00
    assert found["I2|Amount Mismatch (-$150.00)"] == -150.00   # original printed "$-150.00"


def test_one_cent_is_a_rounding_difference_not_a_float_artifact():
    new = OLD.copy()
    new.loc[0, "amount"] = 100.01
    assert "I1|Rounding Difference (+$0.01)" in issues(OLD, new)


def test_values_equal_in_cents_are_not_flagged_despite_float_noise():
    old = inv([("I1", "C1", 0.1 + 0.2)])
    new = inv([("I1", "C1", 0.3)])
    assert reconcile_invoices(old, new).empty


def test_duplicates_in_new_system():
    new = pd.concat([OLD, OLD.iloc[[0]]], ignore_index=True)
    assert "I1|Duplicate in New System" in issues(OLD, new)


def test_duplicates_in_old_system_do_not_cause_false_mismatches():
    old = pd.concat([OLD, OLD.iloc[[0]]], ignore_index=True)
    found = issues(old, OLD)
    assert list(found) == ["I1|Duplicate in Old System"]


def test_customer_mismatch():
    new = OLD.copy()
    new.loc[1, "customer_id"] = "C99"
    assert any(k.startswith("I2|Customer Mismatch") for k in issues(OLD, new))


def test_invalid_amount_is_reported_not_crashed_on():
    new = OLD.copy().astype({"amount": object})
    new.loc[0, "amount"] = "abc"
    assert "I1|Invalid Amount" in issues(OLD, new)


def test_real_one_cent_difference_is_not_hidden_by_float_error():
    # 0.08*100 - 0.07*100 is 0.99999... in floating point; cents rounding must still see it.
    old = inv([("I1", "C1", 0.07)])
    new = inv([("I1", "C1", 0.08)])
    assert list(reconcile_invoices(old, new)["issue"]) == ["Rounding Difference (+$0.01)"]
