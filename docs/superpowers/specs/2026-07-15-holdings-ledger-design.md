# Holdings Ledger — Design

**Date:** 2026-07-15
**Status:** Approved by Kyle (brainstorming session)
**Feature branch:** `feat/holdings-ledger`

## Purpose

Let a user record their **real** brokerage activity — buys, sells, dividends, cash
deposits/withdrawals, splits — with every entry editable and backdatable, so the app can
show their actual holdings, cash balances, and P&L. This is separate from the existing
paper-trading module (`/api/paper`, `paper_portfolios`/`paper_trades`), which stays
untouched as a simulation sandbox. Shared plumbing (auth, DB session, quote providers,
UI components) is reused.

## Requirements (agreed)

- Entry types: `buy`, `sell`, `dividend`, `deposit`, `withdrawal`, `split`, `adjust`.
- Every entry is editable and deletable; `trade_date` is user-chosen and backdatable.
- Multi-currency: USD and TWD, tagged per entry. Balances and totals are reported
  **per currency**; no FX conversion in v1.
- Single ledger per user (no named accounts in v1).
- Cost basis: **average cost**. Realized P&L on sells is computed against the running
  weighted-average cost.
- Validation: **warn but allow**. An entry that makes history inconsistent (negative
  position or negative cash at some date) saves successfully and produces a visible
  warning; it is never rejected for inconsistency.
- Dividends and splits are **auto-suggested** from Yahoo Finance corporate-action
  history and only enter the ledger when the user confirms (dividend amount editable at
  accept time, since real cash received differs from gross — e.g. US 30% withholding
  for Taiwan residents).
- `adjust` checkpoints let the user overwrite computed state directly:
  - **Position variant** (`symbol`, `qty`, `price`): "as of this date I hold qty shares
    at average cost price." Fees need not be reconstructed — the stated average cost is
    authoritative.
  - **Cash variant** (`currency`, `amount`): "as of this date my cash balance in this
    currency is amount."

## Architecture: pure ledger, compute-on-read

The database stores **only transactions**. Holdings, average cost, cash balances,
realized P&L, and warnings are derived by replaying the user's full transaction history
on every read. Nothing derived is persisted, so edits/backdates/deletes can never leave
stale state. A personal ledger replays in milliseconds at any realistic size.

Rejected alternatives: materialized holdings tables (cache-invalidation bug surface for
performance we don't need); frontend-side computation (logic not reusable or testable
server-side).

## Data model

New table `portfolio_transactions` (one Alembic migration):

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | autoincrement |
| `user_id` | String FK → `users.id` | indexed |
| `type` | String | `buy` \| `sell` \| `dividend` \| `deposit` \| `withdrawal` \| `split` \| `adjust` |
| `trade_date` | Date | user-entered action date, backdatable |
| `symbol` | String, nullable | uppercase, e.g. `AAPL`, `2330.TW`; null for cash-only entries |
| `qty` | Numeric, nullable | shares (buy/sell, adjust-position); split ratio for `split` (e.g. 4 = 4-for-1) |
| `price` | Numeric, nullable | per-share price (buy/sell); average cost (adjust-position) |
| `amount` | Numeric, nullable | cash amount (dividend/deposit/withdrawal, adjust-cash) |
| `fee` | Numeric, default 0 | commission + tax in the entry's currency |
| `currency` | String | `USD` \| `TWD` |
| `note` | String, nullable | free text |
| `created_at`, `updated_at` | DateTime(tz) | audit only |

Field usage per type is enforced in the Pydantic schemas (e.g. `deposit` requires
`amount`, forbids `symbol`). For symbol-bearing entries, currency is derived from the
symbol suffix (`.TW`/`.TWO` → TWD, else USD) with manual override allowed; cash-only
entries state it explicitly.

Small companion table `portfolio_suggestion_dismissals` (`id`, `user_id`, `symbol`,
`type`, `ex_date`) records dismissed corporate-action suggestions so they stay hidden.
Suggestions themselves are never stored — they are computed on request.

## Ledger replay (service `app/services/portfolio_ledger.py`)

Load the user's transactions ordered by `trade_date` (ties broken by `id`) and fold
left, per currency and per symbol, using `Decimal` arithmetic throughout:

- **buy**: new avg cost = (held·avg + qty·price + fee) / (held + qty); cash −= qty·price + fee.
- **sell**: realized P&L += qty·(price − avg) − fee; held −= qty; cash += qty·price − fee; avg cost unchanged.
- **dividend**: cash += amount; per-symbol dividends-received += amount.
- **deposit** / **withdrawal**: cash += / −= amount.
- **split**: held ×= ratio; avg cost ÷= ratio.
- **adjust (position)**: held = qty; avg cost = price. Realized P&L for that symbol is
  reported **from the latest adjust forward**; earlier trades are superseded.
- **adjust (cash)**: that currency's cash = amount.

Warnings are collected during replay whenever a position or a cash balance goes
negative, citing symbol/currency, the date, and the offending transaction id. Warnings
earlier than a symbol's/currency's latest `adjust` checkpoint are suppressed.

The summary enriches held symbols with live quotes via the existing provider chain to
produce market value and unrealized P&L. Quote failures degrade gracefully (market
value shown as unavailable, everything else still computed).

## Corporate-action suggestions

On `GET /suggestions`: for each symbol ever held, fetch Yahoo dividend/split history
(yfinance, via existing provider/cache patterns), replay the ledger to get shares held
on each ex-date, and emit a suggestion for every action where shares > 0 that has **no
matching ledger entry** (same symbol + type + date) and **no dismissal record**.
Dividend suggestions pre-fill gross amount = shares × per-share dividend; the user can
edit the amount when accepting. Accepting creates a normal editable transaction;
dismissing writes a dismissal row.

## API (`app/routes/portfolio.py`, prefix `/api/portfolio`, JWT auth like `/api/paper`)

- `GET /transactions?symbol=&type=` — list entries, newest first.
- `POST /transactions` — create; returns the entry + current `warnings`.
- `PUT /transactions/{id}` — edit any field; returns the entry + current `warnings`.
- `DELETE /transactions/{id}` — delete; returns current `warnings`.
- `GET /summary` — per-currency cash + totals, holdings (qty, avg cost, live price,
  market value, unrealized P&L, realized P&L, dividends received), `warnings`.
- `GET /suggestions` — pending dividend/split suggestions.
- `POST /suggestions/accept` — body: the suggestion + final amount → creates a transaction.
- `POST /suggestions/dismiss` — body: symbol/type/ex_date → records a dismissal.

Errors: 400 malformed entry (per-type validation), 404 missing or not-owned entry,
502 only where a quote is strictly required (never for `/summary`). Consistency issues
are warnings in the payload, never HTTP errors.

## Frontend

New page `HoldingsPage.tsx` at route `/holdings` (nav label "Holdings");
`/portfolio` remains the paper-trading page. Follows existing patterns: protected
route, `src/api` client, i18n strings, shared ui components. Layout:

1. **Summary header** — per-currency cards: cash, market value, unrealized P&L,
   realized P&L + dividends. Consistency warnings render as a dismissable amber banner.
2. **Holdings table** — per held symbol: qty, avg cost, live price, market value,
   unrealized P&L ($ and %); currency badge. A banner surfaces pending suggestions and
   opens a review list with Accept (editable amount) / Dismiss.
3. **Transactions table** — newest first, filter by symbol/type, Edit/Delete per row.
   "Add transaction" dialog adapts its fields to the chosen type; currency auto-derived
   from symbol suffix with manual override. Rows implicated in warnings get an indicator.

## Testing

- **Ledger replay unit tests (core):** avg cost with fees; sell realizing P&L; split
  adjusting qty/avg; dividend cash; both `adjust` variants overriding state and
  suppressing earlier warnings; warning generation; multi-currency separation;
  edit/backdate/delete scenarios re-deriving correctly; Decimal precision.
- **Route tests:** CRUD happy paths, per-type validation failures, auth isolation
  (user A cannot read/edit user B's entries), suggestion diffing and dismissal with
  Yahoo calls mocked.
- **Frontend (vitest):** type-adaptive form validation and symbol→currency derivation.

## Out of scope (v1)

FX conversion and combined-currency totals; multiple named accounts; FIFO/lot-level
cost basis; tax reports; CSV import; automatic (unconfirmed) application of corporate
actions.
