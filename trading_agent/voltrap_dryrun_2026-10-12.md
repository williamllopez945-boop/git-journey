# VOLTRAP dry-run — 2026-10-12

**Status: paper/demonstration only.** VOLTRAP itself remains gated exactly as
PLAYBOOK.md's "VOLTRAP" and "Auto-execution" sections specify. This firing
never called `place_option_order` or `place_equity_order`, and it did not
modify `VOLTRAP_RISK_LIMITS`, `VOLTRAP_WATCHLIST`, `VOLTRAP_AUTO_EXECUTE`,
`RISK_LIMITS`, `WATCHLIST`, `STOCK_WATCHLIST`, or `DRY_RUN`. This file exists
so the owner can see the mechanism behave against real live market data
without committing real funds, per the standing dry-run Routine
(PLAYBOOK.md's "VOLTRAP dry-run (paper — owner request, 2026-09-30)"
section) — see `voltrap_dryrun_2026-09-30.md` for the first run.

Market was open regular hours (Monday 2026-10-12, not a market holiday) —
steps 3-4 ran normally.

## Method and a config discrepancy worth flagging

Ran the real per-cycle procedure from that PLAYBOOK section exactly as
written, substituting a **hypothetical** $5,000 portfolio everywhere the
real procedure would read `get_portfolio`. `get_portfolio` was never called
for this dry-run. `review_option_order` was called for real
collateral/fee/probability numbers (preview-only, no order placed).

- Hypothetical portfolio: **$5,000**
- `max_voltrap_pct`, read live from `VOLTRAP_RISK_LIMITS` in `config.py`:
  **1.00** — **not 0.25.** PLAYBOOK.md's dry-run section still hard-codes
  "the real, already-confirmed 0.25" in its worked formula, and the first
  dry-run doc (2026-09-30) used 0.25 for the same reason. `config.py`'s own
  comment explains the real history: the owner raised it from a proposed
  0.25 default to 1.00 on 2026-10-09 (after funding, confirmed via
  `AskUserQuestion`) — i.e. **after** the first dry-run doc was written, and
  PLAYBOOK.md's dry-run section was never updated to match. Per this
  session's instructions ("read the live value from `config.py`, don't
  assume a number") this run uses the live **1.00**, not the stale 0.25 in
  PLAYBOOK's prose. Flagging the conflict rather than silently resolving it
  by editing either file. This is a real, pre-existing inconsistency between
  current code and old playbook prose, not something this run introduced.
- Reserved collateral ceiling = $5,000 × 1.00 = **$5,000**
- Desired concurrent positions: **2** (same not-a-documented-VOLTRAP-config
  assumption as the first dry-run, from this section's own text) →
  `max_collateral_per_contract` = $5,000 / 2 = **$2,500**
- `min_avg_options_volume` / `min_open_interest`, read live from
  `VOLTRAP_RISK_LIMITS`: **100** / **500**
- `target_delta_min` / `target_delta_max`, read live: **0.15** / **0.30**

## Step 1: candidate screen (real data)

`run_scan` on the real saved VOLTRAP scan (`e3983260-740b-4a84-8369-54420cbeafdd`)
returned **385 matching instruments** (200-row page cap applies, sorted
`Last asc` — same known pagination limit noted in the first dry-run doc).

`voltrap_candidates.rank_by_voltrap_fit` against the 200 returned rows, at
three concurrent-position assumptions for comparison (all using the live
`max_voltrap_pct=1.00`, so the ceilings are far larger than the first run's
0.25-based ones):

| concurrent_positions | max_collateral_per_contract | candidates fitting |
|---|---|---|
| 1 | $5,000.00 | 198 |
| **2 (chosen)** | **$2,500.00** | **119** |
| 3 | $1,666.67 | 81 |

Top 10 of 119 at concurrent_positions=2, ranked by implied volatility (the
coarse premium-yield proxy `rank_by_voltrap_fit` uses):

| Ticker | Last | IV | Avg opt. volume | Open interest | 100-share collateral |
|---|---|---|---|---|---|
| TSLL | $10.25 | 79.8% | 46,036 | 706,740 | $1,025.15 |
| GLXY | $20.06 | 78.9% | 18,303 | 223,796 | $2,006.00 |
| MMED | $18.76 | 78.8% | 32,609 | 221,268 | $1,875.50 |
| AI | $12.74 | 78.5% | 14,744 | 174,008 | $1,273.50 |
| PGEN | $7.83 | 78.3% | 5,226 | 92,701 | $783.00 |
| SMR | $6.86 | 77.7% | 26,013 | 447,909 | $686.00 |
| SBET | $8.64 | 77.5% | 24,603 | 440,296 | $864.00 |
| DCH | $5.52 | 77.4% | 6,842 | 39,051 | $552.00 |
| MARA | $9.54 | 77.3% | 75,174 | 1,301,794 | $954.00 |
| KSS | $20.16 | 77.3% | 10,055 | 70,290 | $2,016.00 |

Notes on this list:
- **MARA** is the only real `VOLTRAP_WATCHLIST` name (SMCI, MARA, OKLO, CLSK,
  RGTI, ASST, NVDL, SEDG) that clears this cycle's budget/liquidity bar — a
  direct consequence of the much larger `max_voltrap_pct=1.00` ceiling vs.
  the first dry-run's 0.25 (none of the watchlist fit then).
- **PGEN** appears (rank 5) but is deliberately skipped for the strike
  walkthrough below: `config.py`'s own `VOLTRAP_WATCHLIST` comment excluded
  it by name for "clinical-stage biotech binary-catalyst risk" during the
  real watchlist's fundamentals vetting (`watchlist_review_2026-09-26_voltrap.md`).
  This screen (by design, per PLAYBOOK.md) doesn't re-run that fundamentals
  check, so a name excluded there for good reason can still resurface here —
  worth the owner's attention if this dry-run is ever used to suggest
  expanding `VOLTRAP_WATCHLIST`, which it is not doing.
- **MMED** (rank 3) is also a clinical-stage/binary-catalyst-shaped name
  (psychedelic-therapeutics biotech) for the same reason, and separately its
  nearest listed expiration after today is 2026-11-20 (no 2026-10-23 weekly
  on this chain) — not a fit for VOLTRAP's weekly cadence this cycle. Skipped
  for the walkthrough below for both reasons.

Picked the top two survivors that are liquid, not biotech-binary-risk names,
and have a near weekly expiration: **TSLL** and **GLXY**.

## Step 2: strike selection — TSLL (full detail)

Current price (scan): $10.25. Nearest Friday (2026-10-16) is only 4 calendar
days from today (Mon 2026-10-12) — **too near per this section's own
"5+ calendar days" rule, skipped.** Used the next weekly, **2026-10-23 (11
days out)**.

`get_option_instruments` → puts near the current price → `get_option_quotes`:

| Strike | Delta | Mark | Bid/Ask | Open interest | chance_of_profit_short |
|---|---|---|---|---|---|
| $7.00 | -0.036 | $0.025 | $0.02/$0.03 | 867 | 94.8% |
| $7.50 | -0.074 | $0.065 | $0.05/$0.08 | 1,714 | 90.4% |
| $8.00 | -0.125 | $0.125 | $0.12/$0.13 | 2,179 | 85.2% |
| **$8.50** | **-0.202** | **$0.240** | **$0.21/$0.27** | **3,099** | **78.6%** |
| $9.00 | -0.291 | $0.385 | $0.36/$0.41 | 3,028 | 72.2% |
| $9.50 | -0.391 | $0.580 | $0.55/$0.61 | 3,105 | 66.3% |
| $10.00 | -0.496 | $0.845 | $0.81/$0.88 | 1,493 | 61.1% |

`pick_strike_by_delta` selects **$8.50** (delta -0.202, target band
0.15–0.30, closest to the band's 0.225 midpoint) — the only strike in this
sampled range inside the band besides $9.00, and closer to the midpoint;
also carries deep open interest (3,099).

**`review_option_order` (real, live — no order placed):**
- 1 contract, TSLL $8.50 put, exp 2026-10-23, sell to open, limit $0.25
- Live re-quote at review time: delta -0.204180, mark $0.235, bid
  $0.21/ask $0.26 (moved slightly from the screening snapshot seconds
  earlier — expected on a thinly-traded option)
- Fees: **$0.04 total** (OCC $0.02 + OR $0.02)
- **Collateral reserved: $900.00 cash** (note: Robinhood's real collateral
  figure, not the simple 100 × strike = $850 back-of-envelope number — fits
  easily inside the $2,500 `max_collateral_per_contract` ceiling for this
  scenario)
- Premium at the $0.25 limit: $25.00 gross, ~$24.96 net of fees
- `chance_of_profit_short` (probability of expiring OTM, i.e. keeping the
  full premium): **78.4%** at review time — squarely in VOLTRAP's target
  70–85% band
- No `order_checks` alert fired on this one (real account buying power was
  sufficient for this smaller collateral amount).

## Step 2b: strike selection — GLXY (second survivor)

Current price (scan): $20.06. Same expiration used, **2026-10-23**.

| Strike | Delta | Mark | Bid/Ask | Open interest | chance_of_profit_short |
|---|---|---|---|---|---|
| $16.00 | -0.013 | $0.07 | $0.00/$0.14 | 49 | 98.3% |
| $17.00 | -0.098 | $0.14 | $0.04/$0.24 | 6 | 88.7% |
| $18.00 | -0.187 | $0.31 | $0.18/$0.44 | 32 | 80.9% |
| **$18.50** | **-0.250** | **$0.47** | **$0.38/$0.56** | **55** | **76.0%** |
| $19.00 | -0.310 | $0.62 | $0.52/$0.72 | 158 | 72.1% |

`pick_strike_by_delta` selects **$18.50** (delta -0.250, closest to the
0.225 midpoint of the candidates landing inside the band — $19.00's -0.310
is outside it).

**`review_option_order` (real, live — no order placed):**
- 1 contract, GLXY $18.50 put, exp 2026-10-23, sell to open, limit $0.45
- Live re-quote: delta -0.250221, mark $0.47, bid $0.38/ask $0.56
- Fees: **$0.04 total** (OCC $0.02 + OR $0.02)
- **Collateral reserved: $1,850.00 cash** (= 100 × $18.50, fits inside the
  $2,500 ceiling)
- Premium at the $0.45 limit: $45.00 gross, ~$44.96 net of fees
- `chance_of_profit_short`: **76.0%** at review time — inside the 70–85%
  target band
- **`order_checks` alert fired: `OPTION_NOT_ENOUGH_BP_FOR_COLLATERAL`**,
  `depositAmount: $827.88` — the **real, live** brokerage account does not
  currently have enough real buying power to cover this $1,850 collateral.
  This is expected and informative, not a bug: the real account is far
  smaller than this dry-run's $5,000 hypothetical, exactly the same honest
  gap the first dry-run doc called out. `review_option_order` surfaced this
  alert without placing anything — no real risk from this preview.

Liquidity note: GLXY's open interest at the chosen strike (55) is far
thinner than TSLL's (3,099) or the first dry-run's AUR pick (3,021) — still
clears `min_open_interest=500` in aggregate scan terms (GLXY's own
open-interest *column*, 223,796, is what the screen actually filtered on;
the per-strike OI shown above is a separate, finer-grained number from the
option chain itself, worth the owner knowing is much thinner for this
particular contract).

## Observations for the owner

1. **The PLAYBOOK dry-run section's hard-coded `max_voltrap_pct=0.25` is
   stale** (see "Method" above) — it was accurate when the dry-run Routine
   was designed (2026-09-30) and when the first worked example ran, but the
   owner raised the real config value to 1.00 on 2026-10-09 and the
   playbook prose was never updated to match. This run used the live value
   per this session's instructions; the playbook text itself needs an
   owner-reviewed edit to stop citing 0.25, separate from this dry-run doc.
2. **The much larger ceiling changes which names fit.** At $5,000 ×
   1.00 / 2 = $2,500 per contract, 119 of 200 screened rows fit (vs. 13 at
   the first run's $625 ceiling) — including, for the first time, one real
   `VOLTRAP_WATCHLIST` name (MARA).
3. **Not every top-ranked-by-IV candidate is a good pick.** Two of this
   cycle's top 10 (PGEN, MMED) carry the same clinical-stage-biotech
   binary-catalyst shape the real watchlist's fundamentals vetting
   explicitly screened out elsewhere in this project — this dry-run's
   ranking function doesn't re-run that check, so a human (or a future
   fundamentals-aware filter) still needs to look before trusting raw IV
   rank alone.
4. **The mechanism works cleanly end to end on two different underlyings
   this cycle** — scan → rank → chain → instruments → quotes → delta-band
   strike pick → real collateral/fee/probability numbers via
   `review_option_order` — with no code changes needed.
5. **The real account's buying power is still the binding constraint for a
   position anywhere near this hypothetical's size** (GLXY's preview alert).
   This dry-run's numbers describe what a funded $5,000 book could do, not
   what the current real account could place today.
6. Single-cycle, two-symbol snapshot, not a backtest. Shows the mechanism
   working on real live data, not whether the strategy is profitable over
   time — that still needs the real historical options-chain backtesting
   this repo doesn't have a data source for yet.
