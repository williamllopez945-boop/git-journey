# VOLTRAP dry-run — 2026-10-19

**Status: paper/demonstration only.** This firing never called
`place_option_order`, `place_equity_order`, or `place_crypto_order`, and it
did not modify `VOLTRAP_RISK_LIMITS`, `VOLTRAP_WATCHLIST`,
`VOLTRAP_AUTO_EXECUTE`, `RISK_LIMITS`, `WATCHLIST`, `STOCK_WATCHLIST`, or
`DRY_RUN`. Per the standing dry-run Routine (PLAYBOOK.md's "VOLTRAP dry-run
(paper — owner request, 2026-09-30)" section) — see `voltrap_dryrun_2026-09-30.md`,
`voltrap_dryrun_2026-10-05.md`, and `voltrap_dryrun_2026-10-12.md` for prior
runs.

Market was open regular hours (Monday 2026-10-19, not a holiday) — all steps
ran normally.

## Method

Hypothetical portfolio: **$5,000** (never `get_portfolio` for this dry-run's
budget math). Live config values read directly from `config.py` (not
PLAYBOOK's prose, which is known stale per the 2026-10-12 doc):

- `max_voltrap_pct`: **1.00**
- Reserved collateral ceiling = $5,000 × 1.00 = **$5,000**
- Assumed 2 concurrent positions → `max_collateral_per_contract` = $5,000 / 2
  = **$2,500**
- `min_avg_options_volume` / `min_open_interest`: **100** / **500**
- `target_delta_min` / `target_delta_max`: **0.15** / **0.30**

## Step 1: candidate screen (real data)

`run_scan` on `e3983260-740b-4a84-8369-54420cbeafdd` returned **354 matching
instruments** (200-row page cap, sorted `Last asc` — same known pagination
limit as every prior run).

`voltrap_candidates.rank_by_voltrap_fit` against the 200 returned rows at
`max_collateral_per_contract=$2,500`: **118 survivors**.

Top 10, ranked by implied volatility:

| Ticker | Last | IV | Avg opt. volume | Open interest | 100-share collateral |
|---|---|---|---|---|---|
| SMMT | $15.15 | 79.9% | 11,142 | 161,222 | $1,515 |
| SMR | $5.87 | 79.5% | 28,069 | 411,052 | $587 |
| SCO | $16.73 | 79.3% | 12,433 | 42,574 | $1,673 |
| SHLS | $7.09 | 78.1% | 7,419 | 23,936 | $709 |
| BMNR | $21.73 | 77.6% | 70,117 | 1,404,344 | $2,173 |
| BB | $8.12 | 77.6% | 26,810 | 414,021 | $812 |
| RGTI | $11.84 | 76.9% | 27,157 | 466,562 | $1,184 |
| ASST | $24.96 | 76.3% | 21,124 | 214,566 | $2,496 |
| SG | $9.85 | 76.2% | 9,925 | 135,273 | $985 |
| EQX | $11.17 | 75.9% | 5,292 | 120,756 | $1,117 |

Notes on this list:
- **SMMT** (rank 1) is skipped for the walkthrough: `config.py`'s own
  `VOLTRAP_WATCHLIST` comment excludes it by name for "clinical-stage
  biotech binary-catalyst risk" during the real watchlist's fundamentals
  vetting — same reasoning as prior dry-runs' skips of PGEN/MMED. This
  screen doesn't re-run that fundamentals check, so it resurfaces here;
  not being proposed as a watchlist addition.
- **RGTI** and **ASST** (ranks 7-8) are real `VOLTRAP_WATCHLIST` names and
  both clear this cycle's budget/liquidity bar.
- Picked the top two non-biotech, liquid survivors for the walkthrough:
  **SMR** and **SCO**.

## Step 2: strike selection — SMR

Current price (scan): $5.87. Nearest Friday (2026-10-23) is only 4 calendar
days out — **too near per the 5+ day rule, skipped.** Used the next weekly,
**2026-10-30 (11 days out)**.

`get_option_instruments` → puts near the current price → `get_option_quotes`:

| Strike | Delta | Mark | Bid/Ask | Open interest | chance_of_profit_short |
|---|---|---|---|---|---|
| $4.00 | -0.116 | $0.050 | $0.02/$0.08 | 86 | 87.0% |
| **$4.50** | **-0.305→-0.304** | **$0.175** | **$0.15/$0.20** | **160** | **72.3%** |
| $5.00 | -0.543 | $0.390 | $0.31/$0.47 | 249 | 60.3% |

`pick_strike_by_delta` selects **$4.50** (delta ≈ -0.30, the only strike
landing inside the 0.15–0.30 band in this sampled range — $5.00's -0.54 is
well outside it).

**`review_option_order` (real, live — no order placed):**
- 1 contract, SMR $4.50 put, exp 2026-10-30, sell to open, limit $0.17
- Live re-quote at review time: delta -0.3036, mark $0.175, bid $0.15/ask
  $0.20
- Fees: **$0.04 total** (OCC $0.02 + OR $0.02)
- **Collateral reserved: $550.00 cash** (not the simple 100×strike=$450
  back-of-envelope number — fits easily inside the $2,500 ceiling)
- Premium at the $0.17 limit: $17.00 gross, ~$16.96 net of fees
- `chance_of_profit_short`: **72.4%** at review time — inside the 70-85%
  target band, toward its lower edge
- No `order_checks` alert fired (real account buying power sufficient for
  this smaller collateral amount).

## Step 2b: strike selection — SCO

Current price (scan): $16.73. Same expiration, **2026-10-30**.

| Strike | Delta | Mark | Bid/Ask | Open interest | chance_of_profit_short |
|---|---|---|---|---|---|
| $14.50 | -0.022 | $0.475 | $0.00/$0.95 | 105 | 97.5% |
| $15.00 | -0.027 | $0.275 | $0.00/$0.55 | 63 | 97.0% |
| **$15.50** | **-0.244** | **$0.300** | **$0.15/$0.45** | **28** | **77.1%** |
| $16.00 | -0.334 | $0.450 | $0.30/$0.60 | 61 | 71.4% |
| $16.50 | -0.437 | $0.725 | $0.40/$1.05 | 204 | 65.4% |

`pick_strike_by_delta` selects **$15.50** (delta -0.244, the only strike
inside the band — $16.00's -0.334 falls just outside it).

**`review_option_order` (real, live — no order placed):**
- 1 contract, SCO $15.50 put, exp 2026-10-30, sell to open, limit $0.30
- Live re-quote: delta -0.2431, mark $0.300, bid $0.15/ask $0.45
- Fees: **$0.04 total** (OCC $0.02 + OR $0.02)
- **Collateral reserved: $1,550.00 cash** (= 100 × $15.50)
- Premium at the $0.30 limit: $30.00 gross, ~$29.96 net of fees
- `chance_of_profit_short`: **77.2%** at review time — inside the 70-85%
  target band
- **`order_checks` alert fired: `OPTION_NOT_ENOUGH_BP_FOR_COLLATERAL`**,
  `depositAmount: $635.16` — the real, live brokerage account does not
  currently have enough real buying power to cover this $1,550 collateral.
  Expected and informative, not a bug: the real account (~$1,023 total
  value this cycle) is far smaller than this dry-run's $5,000 hypothetical
  — the same honest gap every prior dry-run has surfaced.

Liquidity note: SCO's open interest at the chosen strike (28) is thin
relative to the scan's own aggregate "Open interest" column for the
underlying (42,574) — same per-strike-vs-aggregate distinction flagged in
the 2026-10-12 doc for GLXY.

## Observations for the owner

1. **Mechanism still works end to end** — scan → rank → chain →
   instruments → quotes → delta-band strike pick → real
   collateral/fee/probability numbers via `review_option_order` — with no
   code changes needed, fourth consecutive clean run.
2. **RGTI and ASST, two real `VOLTRAP_WATCHLIST` names, both clear this
   cycle's budget/liquidity bar** (ranks 7 and 8) — not walked through in
   detail this cycle since SMR/SCO were picked as the top two eligible
   survivors, but worth noting the real watchlist now has multiple names
   fitting a $2,500/contract budget, not just the single MARA hit from
   2026-10-12.
3. **SMMT recurs as a top-ranked-by-IV name that the real watchlist
   deliberately excludes** for binary-catalyst risk — same caution as
   PGEN/MMED in prior runs: raw IV rank alone is not a safe selection
   filter without the fundamentals check already applied elsewhere.
4. **The real account's buying power remains the binding constraint** for
   any position sized anywhere near this $5,000 hypothetical (SCO's
   preview alert, needing ~$635 more than available). This dry-run
   describes what a funded $5,000 book could do, not what the current
   real account (~$1,023 total value) could place today.
5. Single-cycle, two-symbol snapshot, not a backtest — shows the mechanism
   working on real live data, not whether the strategy is profitable over
   time.
