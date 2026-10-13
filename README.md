# Migration Data Toolkit

[![tests](https://github.com/SamyogChaudhary/migration-data-toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/SamyogChaudhary/migration-data-toolkit/actions)

A small, transparent Python toolkit that cleans, deduplicates, validates and reconciles
customer and invoice data when moving from an old system to a new one - and produces a
plain-English report of what it found.

**Design principle: it flags problems, it never hides them.** Anything it cannot fix with
confidence is left as-is and listed for a human to review. Nothing is silently dropped or
rewritten.

> Status: early-stage learning project. It handles the common messy-data cases well, but it is
> not a replacement for mature tools such as OpenRefine, Great Expectations or Splink
> (see [Limitations](#limitations)).

## Quick start

```bash
git clone https://github.com/SamyogChaudhary/migration-data-toolkit.git
cd migration-data-toolkit
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python -m src --generate          # creates synthetic sample data and runs everything
```

Results appear in `output/`. Open `output/migration_summary.txt` first.

## Using your own data

```bash
python -m src --customers customers.csv \
              --invoices-old old_invoices.csv --invoices-new new_invoices.csv \
              --output-dir results
```

| Option | Meaning |
|---|---|
| `--no-invoices` | Skip invoice reconciliation (customers only) |
| `--country-code 61` | Default country code for phone numbers without one (default `64`, New Zealand) |
| `--strict` | Exit with code 1 if any issue is found - useful in automated checks |
| `--generate` | Create synthetic sample data in `--data-dir` first |

Required columns are listed in [docs/data_mapping.md](docs/data_mapping.md).

## What each step does

| Step | File | Behaviour |
|---|---|---|
| Generate | `src/generate_data.py` | Synthetic messy data **plus an answer key** of every planted problem |
| Clean | `src/clean.py` | Dates to `YYYY-MM-DD`, phones to `+<country><number>`, emails trimmed/lowercased, `@@` fixed |
| Deduplicate | `src/duplicates.py` | Exact match on first name, last name, email, phone (case-insensitive); keeps the lowest `customer_id` |
| Validate | `src/validate.py` | Required fields, email format, phone format, real calendar dates, unique IDs |
| Reconcile | `src/reconcile.py` | Old vs new invoices, compared in whole cents: missing, extra, duplicate, amount, customer mismatches |
| Report | `src/report.py` | Plain-text summary with counts and next steps |
| Run all | `src/pipeline.py` | `python -m src` |

## Outputs (`output/`)

`customers_cleaned.csv` - after cleaning, before dedupe  
`customers_final.csv` - deduplicated records (some may still need review)  
`duplicate_report.csv` - removed rows, with `duplicate_of` pointing at the kept record  
`validation_errors.csv` - every rule violation: customer, field, problem, value  
`reconciliation_results.csv` - every invoice discrepancy with old/new amounts  
`migration_summary.txt` - the human-readable report

All files are rewritten on every run, even when empty, so you never see results from an old run.

## Assumptions you should check

- Non-ISO numeric dates such as `03/04/2025` are read **day-first** (3 April). Already-ISO dates
  (`2025-03-04`) are never reinterpreted. Truly ambiguous input is a guess - review it.
- Phone numbers with no country code are treated as New Zealand (`+64`). Change with `--country-code`.
- Two customers are duplicates only if all four matching fields agree.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The end-to-end tests check the pipeline against the generator's answer key, so the tests and
the data can never drift apart. Several tests are regression tests for bugs found in review
(day/month swapping on ISO dates, lost `+` and leading zeros, wrong duplicate count).

## Limitations

- Duplicate detection is exact-match only; it will not catch "Jon Smith" vs "John Smith".
  *Idea: add fuzzy matching with Splink or dedupe.*
- Validation rules are hard-coded. *Idea: declarative schemas with Pandera.*
- Reconciliation could be cross-checked against `datacompy`.
- CSV only; no database or ERP connectors.
- Tested on synthetic data only.

## Privacy

Never commit real customer data. `data/` and `output/` are git-ignored for that reason. If you
use this on real personal information, handle it according to the privacy law that applies to
you (for example, the NZ Privacy Act 2020 or GDPR).

## License

MIT - see [LICENSE](LICENSE).
