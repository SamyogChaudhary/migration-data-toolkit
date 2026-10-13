import random
from pathlib import Path

import pandas as pd

def generate_messy_customers(data_dir="data"):
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    data = []
    answer_key = []

    firsts = ["John", "Sarah", "Mike", "Emma", "David", "Chloe", "Sam", "Lisa", "Tom", "Nina"]
    lasts = ["Smith", "Brown", "Jones", "Taylor", "Wilson", "Davies", "Evans", "Thomas", "Roberts", "White"]

    for i in range(1, 301):
        f_name = random.choice(firsts)
        l_name = random.choice(lasts)
        company = f"{l_name} {random.choice(['Ltd', 'Limited', 'Co', 'Company', 'Inc'])}"
        email = f"{f_name.lower()}.{l_name.lower()}@example.com"
        phone = f"+6421{random.randint(1000000, 9999999)}"
        reg_date = f"2025-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        
        data.append({
            "customer_id": f"CUST-{i:04d}", "first_name": f_name, "last_name": l_name,
            "company_name": company, "email": email, "phone": phone, "registration_date": reg_date
        })

    df = pd.DataFrame(data)

    # Plant deliberate customer problems
    exact_dupe = df.iloc[10].copy()
    exact_dupe['customer_id'] = "CUST-0011-DUP" 
    df = pd.concat([df, pd.DataFrame([exact_dupe])], ignore_index=True)
    answer_key.append({"customer_id": "CUST-0011-DUP", "issue": "Exact Duplicate of CUST-0011"})

    df.at[30, 'phone'] = "021 123 4567"
    answer_key.append({"customer_id": df.at[30, 'customer_id'], "issue": "Mixed phone format (spaces)"})

    df.at[40, 'registration_date'] = "03/04/2025"
    answer_key.append({"customer_id": df.at[40, 'customer_id'], "issue": "Mixed date format (DD/MM/YYYY)"})

    df.at[60, 'email'] = df.at[60, 'email'].replace("@", "@@")
    answer_key.append({"customer_id": df.at[60, 'customer_id'], "issue": "Invalid email (double @)"})

    df.at[80, 'company_name'] = None
    answer_key.append({"customer_id": df.at[80, 'customer_id'], "issue": "Missing required field (Company)"})

    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    df.to_csv(Path(data_dir) / "sample_customers_messy.csv", index=False)
    pd.DataFrame(answer_key).to_csv(Path(data_dir) / "answer_key_customers.csv", index=False)
    print("Generated sample_customers_messy.csv")

def generate_invoice_data(data_dir="data"):
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    old_invoices = []
    answer_key = []

    # Generate 200 old system invoices
    for i in range(1001, 1201):
        inv_id = f"INV-{i}"
        cust_id = f"CUST-{random.randint(1, 300):04d}"
        amount = round(random.uniform(50.0, 5000.0), 2)
        inv_date = f"2025-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        
        old_invoices.append({
            "invoice_num": inv_id,
            "customer_id": cust_id,
            "amount": amount,
            "invoice_date": inv_date
        })

    df_old = pd.DataFrame(old_invoices)
    df_new = df_old.copy()

    # Plant reconciliation differences:
    # 1. Remove 3 invoices (Missing in new system)
    missing_ids = df_new.iloc[10:13]['invoice_num'].tolist()
    df_new = df_new[~df_new['invoice_num'].isin(missing_ids)]
    for mid in missing_ids:
        answer_key.append({"invoice_num": mid, "issue": "Missing in New System"})

    # 2. Change 5 amounts
    for idx in range(20, 25):
        inv_num = df_new.iloc[idx]['invoice_num']
        df_new.iat[idx, df_new.columns.get_loc('amount')] += 150.00
        answer_key.append({"invoice_num": inv_num, "issue": "Amount Mismatch (+ $150.00)"})

    # 3. Add 2 duplicate rows in new system
    dupes = df_new.iloc[30:32].copy()
    df_new = pd.concat([df_new, dupes], ignore_index=True)
    for idx, row in dupes.iterrows():
        answer_key.append({"invoice_num": row['invoice_num'], "issue": "Duplicate in New System"})

    # 4. Rounding difference (1 cent)
    round_inv = df_new.iloc[40]['invoice_num']
    df_new.iat[40, df_new.columns.get_loc('amount')] += 0.01
    answer_key.append({"invoice_num": round_inv, "issue": "Rounding Difference (+ $0.01)"})

    # Save files
    df_old.to_csv(Path(data_dir) / "sample_invoices_old.csv", index=False)
    df_new.to_csv(Path(data_dir) / "sample_invoices_new.csv", index=False)
    pd.DataFrame(answer_key).to_csv(Path(data_dir) / "answer_key_invoices.csv", index=False)
    print("Generated sample_invoices_old.csv & sample_invoices_new.csv")

def generate_all(data_dir="data"):
    """Generate all sample files. Seeded, so the output is identical every run."""
    random.seed(42)
    generate_messy_customers(data_dir)
    generate_invoice_data(data_dir)


if __name__ == "__main__":
    generate_all()
