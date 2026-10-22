# Stock watchlist review — trim to top 5 (2026-10-06)

**Owner request** (this session): narrow `STOCK_WATCHLIST` from its current
10 names to the best 5, following the project's existing weekly-review
methodology (`watchlist_review.py`, `backtest.py`, `portfolio_backtest.py`
— same tools and same binding decision rule as `watchlist_review_2026-09-29_stocks.md`
and `watchlist_review_2026-10-04.md`), extended to score all 10 names at
once rather than the usual bottom 1-2.

**Current `STOCK_WATCHLIST`**: `CRWD, PANW, TWLO, ILMN, IR, PTC, CRDO,
VTRS, AR, PYPL`.

## Step 1 — real data, open positions

`get_equity_historicals(symbols=STOCK_WATCHLIST, interval="hour",
bounds="regular")` over the real ~90-day window (2026-07-08 to
2026-10-06, 384 hourly bars per symbol — same window shape used by
`watchlist_review_2026-10-04.md`). `get_equity_positions()` returned no
open stock positions, so **no name is exempt from removal on that
ground** — all 10 scored purely on signal performance.

`trading_agent/state.json`'s `trade_log` has zero entries for any of
these 10 symbols (the strategy has never actually traded a stock name
yet), so every name is scored via `backtest.py` rather than
`watchlist_review.trailing_trade_pnl` (which would need real trade
history to return anything but `None`).

## Step 2 — score all 10, worst-case-first

Each symbol's own 384-bar window run through `backtest.backtest` at
production settings (`short_window=10, long_window=30,
stop_loss_pct=0.04, take_profit_pct=0.08, take_profit_sell_fraction=0.70,
min_strength_pct=0, cooldown_bars=4, fee_pct=0.001`), split into H1/H2
halves (192 bars each), scored by the **worse** of the two half-period
returns — the binding rule both precedent docs established: a
full-period mean is not sufficient, worst-case governs.

| Symbol | Full % | H1 % | H2 % | **Worst %** | Max DD % | Trades |
|---|---:|---:|---:|---:|---:|---:|
| VTRS | 5.28 | −5.04 | 1.60 | **−5.04** | 8.42 | 9 |
| PYPL | −0.11 | 5.48 | −4.68 | **−4.68** | 10.47 | 9 |
| AR | 13.50 | 9.22 | −1.08 | **−1.08** | 6.22 | 10 |
| CRDO | 2.09 | 5.67 | 0.96 | **0.96** | 13.01 | 14 |
| IR | 5.21 | 3.09 | 2.05 | **2.05** | 9.72 | 7 |
| TWLO | 28.57 | 17.13 | 3.05 | **3.05** | 7.97 | 15 |
| ILMN | 19.20 | 15.94 | 3.30 | **3.30** | 7.55 | 12 |
| PTC | 37.85 | 8.53 | 28.49 | **8.53** | 9.76 | 13 |
| CRWD | 18.58 | 11.75 | 10.71 | **10.71** | 8.17 | 8 |
| PANW | 25.85 | 10.84 | 19.11 | **10.84** | 8.20 | 10 |

Ranked ascending by worst-case score, the **bottom 5** — `VTRS, PYPL,
AR, CRDO, IR` — are the removal candidates. The **top 5** — `TWLO, ILMN,
PTC, CRWD, PANW` — are the proposed keep-list. (Note: PTC's own large
positive crossover this session is driven by the Schneider Electric
acquisition arbitrage, not organic SMA momentum — see the 2026-10-06
daily review — but its isolated backtest score still clears every
removal candidate by a wide margin on both halves, so this doesn't
change the ranking.)

## Step 3 — binding portfolio-level gate

This gate still applies to a trim, not just a 1-2 swap, and for the
same reason the precedent docs gave it teeth: `max_concurrent_positions`,
`max_aggregate_position_pct`, and `max_trades_per_day` are *shared*
capacity constraints across the whole list that no single symbol's
isolated backtest can see. `portfolio_backtest.portfolio_backtest` run
twice over the identical window and split, at production `RISK_LIMITS`
(`max_position_pct=0.20, max_concurrent_positions=5,
max_aggregate_pct=0.60, max_trades_per_day=4, fee_pct=0.001`):

| | Full period | H1 | H2 | **Worst-case** | Max DD |
|---|---:|---:|---:|---:|---:|
| **Full 10** | 18.28% | 5.07% | 11.41% | **5.07%** | 6.32% |
| **Kept 5** | 22.17% | 6.90% | 13.78% | **6.90%** | 4.84% |

The kept-5 portfolio clearly beats the full-10 baseline at every level
checked — full-period return, worst-case half-period return, **and**
max drawdown (lower, 4.84% vs 6.32%) — not just a mean-level
improvement. This clears the binding worst-case-first gate cleanly.

## Decision

**Recommend trimming `STOCK_WATCHLIST` to `TWLO, ILMN, PTC, CRWD,
PANW`**, dropping `VTRS, PYPL, AR, CRDO, IR`. Not yet applied —
`config.py` is edited only after explicit owner approval, per this
project's standing rule.

## Caveat the owner should know before approving

Once `STOCK_WATCHLIST` holds exactly 5 names, `RISK_LIMITS`'s
`max_concurrent_positions=5` stops being a real constraint on this list
specifically (5 names, 5 slots — every name could be held at once with
room to spare). That setting's actual purpose — capping
signal-concentration risk out of a *larger* universe — no longer
applies here once the list itself is 5. This is not a reason to avoid
the trim (the portfolio-level numbers above are a real, clean
improvement either way), just something to be aware of: the crypto side
of the shared counter is still the only place that cap binds in
practice. No change to `RISK_LIMITS` is proposed as part of this review.

## What this doesn't establish

- Only 90 days of real hourly data (384 bars) was available/used — same
  limitation every prior weekly review has carried. A longer or
  different-regime window could rank differently.
- VTRS/PYPL/AR/CRDO/IR are not inherently bad companies — this measures
  this specific SMA(10,30) crossover strategy's performance on their
  price action over this window, nothing about their fundamentals.
- No stock in `STOCK_WATCHLIST` has ever actually been traded live by
  this bot (`trade_log` confirms), so this is a backtest-only read, same
  as every prior stock-side review.
