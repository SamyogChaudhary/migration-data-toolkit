# Data dictionary and rules

## Customer file (required columns)

| Column | Required value? | Cleaning applied | Validation |
|---|---|---|---|
| `customer_id` | yes | none | must be present and unique |
| `first_name`, `last_name` | yes | trim, collapse spaces | must be present |
| `company_name` | yes | trim, collapse spaces | must be present |
| `email` | yes | trim, lowercase, `@@` -> `@` | `name@domain.tld` shape |
| `phone` | no | to `+<country><number>` | `+` and 8-15 digits if present |
| `registration_date` | no | known formats -> `YYYY-MM-DD` | real calendar date, not in the future |

Extra columns are carried through untouched.

## Invoice files (old and new system)

| Column | Notes |
|---|---|
| `invoice_num` | the key used to match old and new records (required) |
| `amount` | compared in whole cents (required) |
| `customer_id` | optional; if present in both files a different value is reported |

## Reconciliation issue types

| Issue | Meaning |
|---|---|
| `Missing in New System` | invoice exists only in the old system |
| `Only in New System` | invoice exists only in the new system |
| `Duplicate in Old/New System` | same `invoice_num` appears more than once |
| `Amount Mismatch (+$X)` | difference of $1.00 or more (new minus old) |
| `Rounding Difference (+$X)` | difference under $1.00 |
| `Customer Mismatch (A -> B)` | same invoice, different customer |
| `Invalid Amount` | amount is not a number |

## Date formats understood

`YYYY-MM-DD` (kept as-is), `DD/MM/YYYY`, `DD-MM-YYYY`, `DD.MM.YYYY`, `YYYY/MM/DD`,
`4 March 2025`, `4 Mar 2025`, `March 4 2025`, `March 4, 2025`. Anything else is left unchanged
and reported by validation.
