# Weekly watchlist review — 2026-09-27

First run of the standing weekly review (owner request, 2026-09-25; see
`PLAYBOOK.md`'s "Weekly watchlist review" section for the full
procedure). **Decision: no change recommended** for either watchlist
this week — both a real crypto data gap and a real isolated-vs-combined
backtest reversal on the stock side, detailed below.

## Method

1. Score every current `WATCHLIST`/`STOCK_WATCHLIST` member by trailing
   performance: `watchlist_review.trailing_trade_pnl` (real trade
   history) where it exists, else a 90-day-hourly `backtest.py` pass
   against real historicals.
2. Rank worst-case-first; bottom 1-2 (skipping any open position) become
   removal candidates.
3. Source addition candidates from both production scans via
   `watchlist_review.rank_by_crossover_strength`, excluding the current
   watchlist and (crypto) the meme/political/stablecoin list from
   `watchlist_2026-09-23_meme_removal.md`.
4. Backtest every candidate in isolation, then in a combined
   `portfolio_backtest.py` run against the current watchlist.
5. Propose a swap only where the candidate clearly beats the removal
   candidate worst-case-first.

## Crypto: current holdings scored

| Asset | Score | Source | Open position? |
|---|---|---|---|
| SOL | **-$27.45** | real trade P&L | No (fully exited + dust transferred out) |
| AVAX | -$2.36 | real trade P&L (unrealized) | **Yes — skip** |
| DOGE | -$2.05 | real trade P&L (unrealized) | **Yes — skip** |
| ETH | $0.00 | real trade P&L (dust, ~$0.0025 notional) | No |
| HBAR | +$0.04 | real trade P&L | No |
| DOT | +$1.94 | real trade P&L (unrealized) | **Yes — skip** |
| LINK | +$0.60 | real trade P&L | No |
| BTC | +16.06% | 90-day-hourly backtest, IBIT proxy | No |
| LIT, BCH, AERO, CRV, ZORA, ASTER, XLM | **not scoreable** | no trade history, no equity-ETF proxy exists | — |

**Real data gap, same one flagged in every prior crypto backtest this
project has run**: there is no crypto historicals tool, and only
BTC/ETH have a usable equity-ETF proxy (IBIT/ETHA). 7 of 15 `WATCHLIST`
assets (LIT, BCH, AERO, CRV, ZORA, ASTER, XLM) have never traded and
have no proxy, so they cannot be scored this week or any week under
current tooling. Noted, not worked around.

**Removal candidate: SOL** (-$27.45, the clear worst real result, no
open position — a legitimate, real realized loss on a position that was
fully exited this week). ETH's $0.00 is dust-sized (~$0.0025 notional)
and not treated as a meaningful "underperformance" on its own.

**Addition candidates** (crypto scan, excluding watchlist + meme list),
top by crossover strength: SUI (+4.05%), XPL (-2.34%), UNI (+1.74%).

**No crypto swap can be responsibly proposed.** None of SUI/XPL/UNI (or
any other candidate) can be backtested — the same historicals gap that
blocks scoring 7 current holdings blocks validating any replacement.
Per this project's standing rule ("never swap on a screener snapshot
alone"), a real, clearly-underperforming asset (SOL) is not enough by
itself to justify a swap without a backtested replacement. **SOL stays
on the watchlist this week, flagged for re-review once a crypto data
source exists** — this is a real limitation, not a decision to ignore
the finding.

## Stocks: current holdings scored (90-day-hourly backtest.py, real data)

None of the 10 `STOCK_WATCHLIST` names have ever traded, so all 10 are
scored by backtest (production settings: SMA(10,30), `min_strength_pct=0`,
`cooldown_bars=4`, current stop-loss/take-profit).

| Symbol | Return | Max DD | Trades |
|---|---|---|---|
| **MAIR** | **-18.35%** | 23.92% | 13 |
| **IR** | **-2.53%** | 10.49% | 10 |
| PTC | +2.24% | 13.14% | 16 |
| PANW | +2.25% | 16.59% | 10 |
| TWLO | +2.32% | 15.77% | 12 |
| AR | +3.51% | 5.90% | 11 |
| CRWD | +6.53% | 13.36% | 8 |
| CRDO | +8.48% | 20.69% | 15 |
| ILMN | +15.11% | 13.16% | 16 |
| PYPL | +16.27% | 9.48% | 16 |

**Removal candidates: MAIR (-18.35%) and IR (-2.53%)** — a clear bottom
2, neither currently held.

**Addition candidates** (stock scan, excluding watchlist, `$10B+`
market cap floor): top by crossover strength VIAV (+4.80%), BE (+4.67%),
RVMD (+3.56%). Isolated 90-day backtests:

| Symbol | Return | Max DD | Trades |
|---|---|---|---|
| VIAV | -14.23% | 28.52% | 13 |
| BE | -15.54% | 25.25% | 14 |
| RVMD | -1.35% | 11.92% | 13 |

**Split-window check** (H1 2026-06-29 to 08-12, H2 08-12 to 09-25),
worst-case first:

| Symbol | Full | H1 | H2 | Worst |
|---|---|---|---|---|
| MAIR | -18.35% | -9.45% | -6.88% | -9.45% |
| IR | -2.53% | +0.50% | -3.02% | -3.02% |
| VIAV | -14.23% | -6.13% | -0.39% | -6.13% |
| BE | -15.54% | -7.06% | +3.75% | -7.06% |
| RVMD | -1.35% | +7.78% | -4.17% | -4.17% |

**IR is not beaten by any candidate** — its worst-case (-3.02%) is
better than VIAV, BE, or RVMD's worst-case. No swap proposed for IR.

**MAIR vs. RVMD, isolated: RVMD clearly wins** (worst-case -4.17% vs.
MAIR's -9.45%, positive in both halves' relative comparison). This
looked like a real, decisive swap.

### The combined portfolio check reverses it

Per the required step 4, ran `portfolio_backtest.py` with the full
10-name watchlist (current settings: `max_position_pct=20%`,
`max_concurrent_positions=5`, `max_aggregate_pct=60%`,
`max_trades_per_day=4`) against the same swap:

| Variant | Full return | Max DD | H1 | H2 | Worst (split) |
|---|---|---|---|---|---|
| Current (with MAIR) | **+1.72%** | 7.90% | **+0.28%** | +2.24% | **+0.28%** |
| Proposed (MAIR→RVMD) | -0.76% | 9.96% | -3.38% | +2.87% | -3.38% |

**The swap makes the portfolio worse, not better**, despite RVMD's
much stronger isolated result. This is a real interaction effect (the
same shared-concurrent-position/aggregate-cap dynamic this project has
found before with correlated signals) — RVMD's entries evidently
compete with the other 9 names for the same concurrent-position/
aggregate-cap room in a way that isolated single-asset backtesting
can't see. The portfolio-level result is the one that actually reflects
how the live system trades (all 10 names sharing one set of caps), so
it's the binding one, not the isolated number.

**No stock swap recommended.** MAIR and IR remain the two weakest
backtested names, but no sourced candidate beats either of them once
tested the way the real system actually runs.

## Decision

**No change recommended this week**, for both watchlists — a genuine,
evidence-based outcome, not a failure to look. Flagged for next week:
- Crypto: re-score SOL and the 7 untestable names the moment any crypto
  historicals source becomes available.
- Stocks: MAIR and IR remain the weakest 2; re-run candidate sourcing
  next week in case a better-fitting name (one that doesn't collide with
  the rest of the watchlist's concurrent-position dynamics) turns up.

No `config.py` change made or proposed as a specific edit — `WATCHLIST`
and `STOCK_WATCHLIST` are unchanged. No order placed, previewed, or
cancelled at any point in this review.
