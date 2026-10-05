# VOLTRAP dry-run — 2026-09-30

**Status: paper/demonstration only.** VOLTRAP itself remains unfunded and
gated exactly as PLAYBOOK.md's "VOLTRAP" section specifies — no real
option order has been placed, `VOLTRAP_RISK_LIMITS`, `VOLTRAP_WATCHLIST`,
and `VOLTRAP_AUTO_EXECUTE` are all untouched, and the real go-live
condition ("owner confirms `max_voltrap_pct`" + "`get_portfolio` shows
real free cash for it") has not changed. This file exists so the owner
can see how the mechanism behaves against real live market data before
committing real funds, per an explicit owner request (2026-09-30).

## Method

Ran the real per-cycle procedure from PLAYBOOK.md's "VOLTRAP" section
exactly as written, substituting a **hypothetical** $5,000 portfolio for
the real (currently ~$457) account value everywhere the real procedure
would read `get_portfolio`. Everything else — the saved scan, the
ranking/strike-selection functions, `review_option_order` for real
collateral/fee numbers — is the real, live mechanism; only the budget
input is synthetic. No `place_option_order` call was made or will be
made by this dry-run at any point.

- Hypothetical portfolio: **$5,000**
- `max_voltrap_pct` (from the real, already-confirmed `VOLTRAP_RISK_LIMITS`): **0.25**
- Reserved collateral ceiling: $5,000 × 0.25 = **$1,250**
- Desired concurrent positions: **2** (assumption — not a documented
  VOLTRAP config value; picked as a reasonable small-book default,
  producing max_collateral_per_contract = $1,250 / 2 = $625, i.e. any
  candidate whose 100-share collateral (`Last` × 100) exceeds $625 is
  filtered out.) The recurring dry-run Routine (below) will use the
  same assumption each week unless the owner says otherwise.

## Step 1: candidate screen (real data)

`run_scan` on the real saved VOLTRAP scan
(`e3983260-740b-4a84-8369-54420cbeafdd`, "Options Wheel Candidates —
IV/Liquidity Screener") returned **399 matching instruments** (200-row
page cap applies, sorted `Last asc` — same known pagination limit as
every scan on this account).

`voltrap_candidates.rank_by_voltrap_fit` against the 200 returned rows,
at three different concurrent-position assumptions for comparison:

| concurrent_positions | max_collateral_per_contract | candidates fitting |
|---|---|---|
| 1 | $1,250.00 (Last ≤ $12.50) | 63 |
| **2 (chosen)** | **$625.00 (Last ≤ $6.25)** | **13** |
| 3 | $416.67 (Last ≤ $4.17) | 0 (scan's own `Last > 5` floor excludes everything) |

Top 8 of 13 at concurrent_positions=2, ranked by implied volatility
(the coarse premium-yield proxy `rank_by_voltrap_fit` uses):

| Ticker | Last | IV | Avg opt. volume | Open interest | 100-share collateral |
|---|---|---|---|---|---|
| AUR | $5.39 | 78.2% | 21,995 | 452,023 | $539.00 |
| SOUN | $5.88 | 67.0% | 26,668 | 537,415 | $588.00 |
| JOBY | $5.98 | 66.0% | 19,454 | 394,748 | $598.00 |
| LUMN | $5.57 | 65.3% | 17,186 | 271,816 | $557.00 |
| STUB | $5.30 | 63.1% | 14,915 | 33,160 | $530.00 |
| ACHR | $5.09 | 55.2% | 27,095 | 682,316 | $509.00 |
| BTG | $5.34 | 52.6% | 14,511 | 514,141 | $534.00 |
| TDOC | $5.86 | 49.7% | 5,711 | 152,039 | $586.00 |

None of the real `VOLTRAP_WATCHLIST` names (SMCI, MARA, OKLO, CLSK,
RGTI, ASST, NVDL, SEDG) fit at this budget/concurrency level — MARA
(Last $12.04) only clears the bar at concurrent_positions=1. This is a
direct, honest consequence of the $5,000 hypothetical size: a larger
real deposit would open up the standing watchlist names; a $5,000 book
mostly trades outside it.

## Step 2: strike selection walkthrough (AUR, full detail)

Picked the top-ranked candidate, AUR, to walk the rest of the real
procedure end to end.

**First attempt — nearest Friday (2026-10-02, 2 days out) — rejected.**
This is only 2 calendar days from today (Wed 2026-09-30). At this
maturity, AUR's available strikes ($0.50 increments) are too coarse for
the target delta band: $5.00 strike priced at delta -0.075, next strike
up ($5.50) jumps straight to delta -0.567 — nothing lands in the
0.15–0.30 target band. **Finding:** VOLTRAP's real procedure assumes a
Monday-morning entry, giving a full week to the nearest Friday; running
it mid-week against the *very* next Friday, as this ad hoc dry-run did
first, can leave too little time for clean delta granularity on
lower-priced names. The recurring weekly Routine (below) is scheduled
for Monday specifically to avoid this.

**Second attempt — next weekly (2026-10-09, 9 days out) — used.**

| Strike | Delta | Mark | Bid/Ask | OI | chance_of_profit_short |
|---|---|---|---|---|---|
| $3.50 | -0.021 | $0.425 | $0.00/$0.85 | 0 | 96.6% |
| $4.00 | -0.028 | $0.375 | $0.00/$0.75 | 0 | 96.1% |
| $4.50 | -0.041 | $0.275 | $0.00/$0.55 | 0 | 95.1% |
| **$5.00** | **-0.266** | **$0.125** | **$0.10/$0.15** | **3,021** | **75.1%** |
| $5.50 | -0.532 | $0.325 | $0.25/$0.40 | 59 | 60.9% |

`pick_strike_by_delta` selects **$5.00** (delta -0.266, target band
0.15–0.30, closest to the band's 0.225 midpoint) — the only strike on
this expiration that actually lands in the band; also has by far the
deepest open interest (3,021) of the sampled strikes.

**`review_option_order` (real, live — no order placed):**
- 1 contract, AUR $5.00 put, exp 2026-10-09, sell to open, limit $0.13
- Broker rounds the limit to the $0.05 tick: $0.15
- Fees: $0.04 total (OCC + OR, both $0.02)
- **Collateral reserved: $500 cash** (fits inside the $625
  max_collateral_per_contract ceiling for this scenario)
- Premium at the rounded limit: ~$15 gross, ~$14.96 net of fees
- chance_of_profit_short (probability of expiring OTM, i.e. keeping the
  full premium): **75.1%** — squarely in VOLTRAP's target 70–85% band

At $5,000 hypothetical size, one AUR CSP like this returns roughly
$15 / $500 ≈ **3.0% of reserved collateral over 9 days** if it expires
OTM (annualizes to a rough, not-compounded ~120%/yr on the collateral
actually reserved — a single-symbol snapshot, not a claim about the
strategy's real expected return, which would need the backtesting this
project always requires before trusting a number like that).

## Observations for the owner

1. **Budget size drives everything.** At $5,000 with a 25%/2-position
   split, real candidates exist (13 of them) but they skew toward
   $5–$6 names outside the hand-picked `VOLTRAP_WATCHLIST` — a larger
   real deposit (the earlier PLAYBOOK discussion mentioned owner
   funding "as a % of total portfolio value") would be needed to reach
   the standing watchlist names.
2. **Mid-week entry has real, observable costs** (coarse strike
   granularity near a 2-day expiration) that the real design's
   Monday-morning cadence avoids. The recurring dry-run below is
   scheduled Monday for this reason, matching the real intended cadence.
3. **The mechanism itself works cleanly end to end** against real data
   — scan → rank → chain → instruments → quotes → delta-band strike
   pick → real collateral/fee/probability numbers via
   `review_option_order` — with no code changes needed; the existing
   `voltrap_candidates.py` functions took the hypothetical numbers
   exactly as designed.
4. This is a **single-cycle, single-symbol snapshot**, not a backtest.
   It shows the mechanism working, not whether the strategy is
   profitable over time — that would need real historical options-chain
   backtesting, which does not currently exist as a capability in this
   repo (no options-pricing historical data source is wired up).
