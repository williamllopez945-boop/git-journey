# Stock watchlist review — 2026-09-26

Owner request: "work on our watchlists" (crypto/options/stocks, refresh
with real candidates now). This is the stock pass, sibling to
`watchlist_review_2026-09-26_crypto.md` and `watchlist_review_2026-09-26_voltrap.md`
from the same request. Same purpose as the standing "Weekly watchlist
review" Routine, run early/by hand at the owner's request.

**Recommendation: swap the two worst backtested performers for two
backtest-validated replacements.**

## Method

Unlike crypto, stocks have a real historicals source
(`get_equity_historicals`), so this pass can do what the crypto one
structurally can't: a genuine backtest-based trailing-performance score
for every current member, not just today's crossover snapshot.

1. **Trailing performance of current members.** `STOCK_WATCHLIST` has
   **zero real trades this session** (checked `RiskManager.state["trade_log"]`
   — every trade logged so far is crypto: PEPE/DOT/LINK/HBAR/AVAX), so
   `trailing_trade_pnl` returns `None` for all 10 — expected, falls back
   to backtest per the Weekly watchlist review procedure. Ran the
   production `backtest.py` engine (same entry/exit code as live) against
   real hourly closes, 2026-06-29 → 2026-09-26 (~90 days, 378 bars,
   `adjustment_type=split`, regular hours).
2. **Addition candidates.** Re-ran the production stock scan (scan_id
   `6e009dcf-d184-45a7-915f-ccfc50b4e6be`, $10B+ market cap floor,
   unchanged since `watchlist_stocks_2026-09-23_large_cap.md`), 398
   matches, sorted `Crossover % desc` (confirmed during the 2026-09-26
   system audit that this sort makes the 200-row page cap harmless for
   this exact use — it trims only the weakest signals). Excluded the
   current 10-name watchlist.
3. **Never swap on a screener rank alone** (this project's standing
   rule) — backtested the top screener candidates the same way as the
   current members before proposing any of them.

## Current STOCK_WATCHLIST: backtested trailing performance

| Symbol | Return (90d) | Buy&hold | Max DD | Trades | Win rate | Verdict |
|---|---|---|---|---|---|---|
| ILMN | **+14.96%** | +50.67% | 13.40% | 20 | 30% | keep |
| TWLO | **+12.93%** | +39.12% | 10.73% | 12 | 50% | keep |
| CRWD | **+12.32%** | +33.96% | 12.11% | 12 | 50% | keep |
| PTC | +2.72% | +19.14% | 13.88% | 16 | 25% | keep |
| AR | +2.58% | +0.82% | 6.44% | 11 | 60% | keep |
| IR | -0.08% | -5.34% | 11.86% | 11 | 20% | keep (near-flat, not a clear loser) |
| PANW | -4.60% | +13.85% | 18.90% | 12 | 33% | keep |
| MAIR | -16.16% | -33.24% | 22.05% | 13 | **0%** | keep, watch closely (worst win rate of any name — 3rd worst return, see note) |
| **CHKP** | **-22.77%** | +0.51% | 23.27% | 18 | 11% | **remove** |
| **HUBS** | **-30.71%** | +12.21% | 37.29% | 15 | 29% | **remove** |

Ranked worst-case-first by total return (this project's standing
convention). **HUBS and CHKP are the bottom two** by a clear margin — both
well past -20%, both with the worst win rates and drawdowns on the list.
Neither holds an open position (`get_equity_positions` — zero stock
positions currently), so both are immediately removal-eligible, no
"skip and revisit" needed.

**MAIR note:** 0% win rate (every single trade in this window lost) is
a genuinely worse *behavioral* signal than its -16.16% return alone
suggests, but its return is still meaningfully better than HUBS/CHKP's.
Following the stated "bottom 1-2" rule rather than widening the cut
based on one extra metric after seeing the numbers (the same
cherry-picking trap `watchlist_stocks_2026-09-23_large_cap.md` warned
against) — MAIR stays for now, flagged for extra attention next review.

## Addition candidates (screened, then backtested — not selected on rank alone)

| Rank | Symbol | Name | Mkt cap | Crossover % | Backtest return | Max DD | Win rate |
|---|---|---|---|---|---|---|---|
| 1 | BE | Bloom Energy | $79.5B | +4.67% | **-4.03%** | 19.73% | 50% |
| 2 | CRDO | Credo Technology | $30.4B | +3.99% | **+17.59%** | 18.15% | 38% |
| 3 | RVMD | Revolution Medicines | $42.0B | +3.56% | +0.43% | 10.26% | 17% |
| 4 | PYPL | PayPal Holdings | $45.1B | +3.28% | **+16.82%** | 9.17% | 62% |

**BE ranked #1 by today's crossover snapshot but backtests negative** —
exactly the "never swap on a screener snapshot alone" scenario this
project's rule exists for. Not proposed. RVMD backtests only marginally
positive — considered, not selected. **CRDO and PYPL are the two
candidates that pass both screens**: real, large-cap, established
companies (Credo — optical/electrical interconnect semiconductors;
PayPal — payments), strong crossover rank AND a real backtested return
clearly ahead of what they'd replace.

**Not repeated this pass:** the combined `portfolio_backtest.py` run
`watchlist_stocks_2026-09-23_large_cap.md` did (crypto proxies + all 10
stocks, one shared cash pool) — skipped for time. The isolated-backtest
gap here is large enough (CRDO/PYPL both +16-18% vs. HUBS/CHKP both
-23/-31%) that a combined run swapping two strongly-negative names for
two strongly-positive ones has no plausible path to hurting the
combined result; still, this is a real gap versus the full rigor of the
prior pass and worth closing before the *next* review if the owner
wants full parity.

## Net effect on STOCK_WATCHLIST (proposed, not yet applied)

```
Before: CRWD, PANW, TWLO, ILMN, IR, PTC, CHKP, MAIR, AR, HUBS
After:  CRWD, PANW, TWLO, ILMN, IR, PTC, CRDO, MAIR, AR, PYPL
```

Same size (10 names). `CHKP` → `CRDO`, `HUBS` → `PYPL`.

## Scope note

`config.py` has **not** been edited — recommendation only, waiting for
explicit approval, same as the crypto and VOLTRAP sibling docs.
`research_agent` will need to pick up CRDO/PYPL and drop CHKP/HUBS from
its own coverage once/if this is approved (see
`watchlist_review_2026-09-26_voltrap.md`'s "research_agent" section for
the mechanism — it already tracks `STOCK_WATCHLIST` by reference, not a
copy, so no separate edit is needed there beyond this file's own change).
