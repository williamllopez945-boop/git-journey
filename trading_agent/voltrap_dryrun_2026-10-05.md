# VOLTRAP dry-run — 2026-10-05

**Status: paper/demonstration only.** VOLTRAP itself remains unfunded and
gated exactly as PLAYBOOK.md's "VOLTRAP" section specifies — no real
option order has been placed, `VOLTRAP_RISK_LIMITS`, `VOLTRAP_WATCHLIST`,
and `VOLTRAP_AUTO_EXECUTE` are all untouched, and the real go-live
condition has not changed. This is the second run of the recurring
weekly dry-run Routine (first run: `voltrap_dryrun_2026-09-30.md`) — same
method, run fresh against today's live market data.

## Method

Same procedure as the first run, substituting a **hypothetical** $5,000
portfolio for the real account value everywhere the real VOLTRAP
procedure would read `get_portfolio`. The saved scan, the ranking/strike
functions, and `review_option_order` for real collateral/fee numbers are
all the real, live mechanism; only the budget input is synthetic. No
`place_option_order` call was made or will be made.

- Hypothetical portfolio: **$5,000**
- `max_voltrap_pct` (real, confirmed `VOLTRAP_RISK_LIMITS`): **0.25**
- Reserved collateral ceiling: $5,000 × 0.25 = **$1,250**
- Concurrent positions assumption: **2** (same as the first run) →
  max_collateral_per_contract = $1,250 / 2 = **$625**

## Step 1: candidate screen (real data)

`run_scan` on the real saved VOLTRAP scan
(`e3983260-740b-4a84-8369-54420cbeafdd`, "Options Wheel Candidates —
IV/Liquidity Screener") returned **399 matching instruments** (200-row
page cap, same known pagination limit as every scan on this account).

`voltrap_candidates.rank_by_voltrap_fit` against the 200 returned rows,
at the same three concurrent-position assumptions as the first run:

| concurrent_positions | max_collateral_per_contract | candidates fitting |
|---|---|---|
| 1 | $1,250.00 (Last ≤ $12.50) | 68 |
| **2 (chosen)** | **$625.00 (Last ≤ $6.25)** | **14** |
| 3 | $416.67 (Last ≤ $4.17) | 0 (scan's own `Last > 5` floor excludes everything) |

Top 8 of 14 at concurrent_positions=2, ranked by implied volatility:

| Ticker | Last | IV | Avg opt. volume | Open interest | 100-share collateral |
|---|---|---|---|---|---|
| DCH | $5.59 | 79.6% | 5,914 | 27,258 | $559.00 |
| AUR | $5.63 | 70.3% | 19,367 | 430,706 | $563.50 |
| SOUN | $5.88 | 67.0% | 25,984 | 557,057 | $587.98 |
| LUMN | $5.67 | 65.3% | 17,275 | 316,690 | $567.00 |
| STUB | $5.44 | 63.1% | 10,842 | 24,309 | $544.00 |
| COUR | $5.10 | 62.4% | 7,370 | 34,876 | $510.00 |
| JOBY | $5.84 | 61.1% | 18,144 | 366,680 | $584.50 |
| BTG | $5.15 | 52.9% | 13,627 | 486,374 | $515.01 |

Same finding as the first run: none of the real `VOLTRAP_WATCHLIST`
names (SMCI, MARA, OKLO, CLSK, RGTI, ASST, NVDL, SEDG) fit at
concurrent_positions=2. At concurrent_positions=1 ($1,250 ceiling), only
**MARA** ($11.02) clears the bar — same result as 2026-09-30, i.e.
stable week over week at this hypothetical size.

## Step 2: strike selection walkthrough

Worked through the top 3 survivors in order, per PLAYBOOK.md — **two of
three failed to land a strike in the target delta band (0.15–0.30) and
were skipped**, which is itself the headline finding this week.

**#1 DCH — skipped.** Nearest expiration is 2026-10-16 (11 days out, no
nearer weekly exists for this name). Strikes are $2.50 apart near the
money ($5.59 last): $2.50 strike delta -0.012, $5.00 strike delta
-0.056. Nothing between — too coarse, `pick_strike_by_delta` returns
`None`.

**#2 AUR — skipped.** Same 2026-10-16 expiration (the real next weekly,
2026-10-09, is only 4 calendar days out — skipped per PLAYBOOK's "~5+
days" rule). Strikes are $0.50 apart, finer than DCH, but gamma is steep
right at the money: $5.00 strike delta -0.054, $5.50 strike delta
-0.405. Still nothing in [0.15, 0.30] — skipped.

**#3 SOUN — used.** Same 2026-10-16 expiration. $0.50 strikes:

| Strike | Delta | Mark | Bid/Ask | OI | chance_of_profit_short |
|---|---|---|---|---|---|
| $4.50 | -0.029 | $0.375 | $0.00/$0.75 | 0 | 96.2% |
| $5.00 | -0.042 | $0.030 | $0.00/$0.06 | 5,779 | 95.1% |
| **$5.50** | **-0.228** | **$0.080** | **$0.04/$0.12** | **2,913** | **78.7%** |

`pick_strike_by_delta` selects **$5.50** (delta -0.228, closest to the
band's 0.225 midpoint, and the only strike in range) — also carries
real volume (44 contracts today) and solid open interest (2,913).

**`review_option_order` (real, live — no order placed):**
- 1 contract, SOUN $5.50 put, exp 2026-10-16, sell to open, limit $0.08
- Fees: $0.04 total (OCC + OR, both $0.02)
- **Collateral reserved: $550 cash**
- Premium at the limit: $8 gross, ~$7.96 net of fees
- chance_of_profit_short (probability of expiring OTM): **78.7%** —
  inside VOLTRAP's target 70–85% band

**Real account check (not hypothetical): `order_checks` flagged
`OPTION_NOT_ENOUGH_BP_FOR_COLLATERAL`** — the real account would need an
**additional $321.56** to cover this $550 collateral against its real
$220.49-ish buying power. This is the real brokerage check firing
correctly against the real account, independent of the $5,000
hypothetical used for the ranking math above — a live, concrete
confirmation that VOLTRAP is still unfunded, consistent with every prior
statement in this repo that no real order will be placed until that
changes.

At $5,000 hypothetical size, one SOUN CSP like this returns roughly
$7.96 / $550 ≈ **1.4% of reserved collateral over 11 days** if it
expires OTM (a rough, non-compounded annualized figure in the same
ballpark as the first run's AUR example — a single-symbol snapshot, not
a return claim).

## Observations for the owner

1. **Strike-grid coarseness is a recurring issue, not a one-off.** The
   first run only saw it on a too-near expiration (since fixed by the
   Monday cadence); this run hit it on 2 of the top 3 candidates even at
   a full 11-day expiration, purely because $5-ish stocks trade options
   in $0.50–$2.50 strike increments with steep local gamma. At this
   hypothetical budget tier, expect to skip candidates regularly for
   this reason — it is not a bug, just a real constraint of screening
   sub-$10 names for CSPs.
2. **Budget size still drives everything**, unchanged from the first
   run: the fitting candidates are consistently sub-$6-ish names outside
   the hand-picked `VOLTRAP_WATCHLIST`; only MARA clears the bar, and
   only at the looser 1-concurrent-position assumption.
3. **The real account genuinely cannot fund even the cheapest fitting
   candidate today** — confirmed directly by `review_option_order`'s own
   `OPTION_NOT_ENOUGH_BP_FOR_COLLATERAL` alert on real buying power, not
   just the hypothetical-vs-real budget comparison. Nothing to do here
   except wait for funding, per standing policy.
4. **The mechanism continues to work cleanly end to end** against real
   data — scan → rank → chain → instruments → quotes → delta-band strike
   pick (including correctly returning "skip" for two candidates) →
   real collateral/fee/probability numbers, and a real (not simulated)
   insufficient-funds check. No code changes needed.
5. Still a **single-cycle snapshot**, not a backtest — see the first
   run's doc for the standing caveat on options-chain backtesting not
   being a current capability here.
