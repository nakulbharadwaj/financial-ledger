# Data Model

The canonical ledger schema. This is the contract between the ingest layer
and everything downstream.

## Entities

### `accounts`
One row per financial account.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (PK) | UUID |
| institution | TEXT | "chase", "citi", "fidelity", etc. |
| account_type | TEXT | "checking", "savings", "credit_card", "brokerage", "loan" |
| display_name | TEXT | User-friendly name ("Chase Sapphire") |
| account_number_last4 | TEXT | Last 4 digits — never store full number |
| currency | TEXT | ISO 4217, default "USD" |
| created_at | DATETIME | When this row was created in our ledger |

### `transactions`
One row per transaction. The atomic unit.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (PK) | UUID |
| account_id | TEXT (FK) | → accounts.id |
| txn_date | DATE | Posted date from statement |
| description | TEXT | Raw description as parsed |
| description_normalized | TEXT | Cleaned for search/categorization |
| amount | DECIMAL(15,2) | Negative = outflow, positive = inflow |
| balance_after | DECIMAL(15,2) | If statement provided it; else NULL |
| source_file | TEXT | Path to original statement |
| source_row_hash | TEXT (UNIQUE) | Idempotency key — re-ingesting same file is a no-op |
| ingested_at | DATETIME | When parser produced this row |

### `categorizations`
One row per categorization decision. Separate table because categorization
evolves over time and we want history.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (PK) | UUID |
| transaction_id | TEXT (FK) | → transactions.id |
| category | TEXT | Canonical category (see `category_taxonomy`) |
| subcategory | TEXT | NULL if not subcategorized |
| confidence | REAL | 0.0–1.0 |
| source | TEXT | "rule", "llm", "user" |
| created_at | DATETIME | |
| superseded_at | DATETIME | NULL = current; non-NULL = historical |

### `lots` (Phase 2)
For brokerage accounts. Tracks individual purchase lots for FIFO P&L.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (PK) | UUID |
| account_id | TEXT (FK) | → accounts.id |
| symbol | TEXT | "AAPL" |
| open_date | DATE | |
| open_quantity | DECIMAL(15,6) | Original quantity |
| open_price | DECIMAL(15,4) | Per-share basis |
| remaining_quantity | DECIMAL(15,6) | After partial sales |
| open_transaction_id | TEXT (FK) | → transactions.id |

### `lot_closures` (Phase 2)
Records when a lot is partially or fully sold.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (PK) | UUID |
| lot_id | TEXT (FK) | → lots.id |
| close_date | DATE | |
| close_quantity | DECIMAL(15,6) | |
| close_price | DECIMAL(15,4) | |
| close_transaction_id | TEXT (FK) | → transactions.id |
| realized_pnl | DECIMAL(15,2) | Computed |

## Category taxonomy

Canonical categories. The LLM should NEVER invent new ones at runtime —
the `get_category_taxonomy` tool returns this list and the LLM picks from it.

```
income/
  salary
  interest
  dividend
  capital_gain
  refund
  other

essentials/
  housing/rent_or_mortgage
  housing/utilities
  housing/insurance
  housing/maintenance
  groceries
  transport/fuel
  transport/transit
  transport/rideshare
  healthcare/insurance
  healthcare/out_of_pocket

discretionary/
  dining
  entertainment
  shopping
  travel
  subscriptions
  personal_care

financial/
  investment_in
  investment_out
  loan_payment
  credit_card_payment
  transfer
  fees

other/
  unknown
  taxes
  gift_given
  gift_received
```

## Invariants

1. **No transaction without an account.** FK enforced.
2. **Transactions are immutable.** Categorization changes; the txn doesn't.
3. **`source_row_hash` is the idempotency key.** Re-ingesting the same statement
   is a no-op. Hash includes: account_id, date, description, amount.
4. **All amounts in account's `currency`.** No cross-currency math at the
   transaction level; conversions happen in the analytics layer.
5. **Money is Decimal, never float.** SQLAlchemy `Numeric(15, 2)`.
