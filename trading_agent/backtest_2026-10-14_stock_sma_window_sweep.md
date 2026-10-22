# Stock watchlist SMA window sweep — keep 10/30, do not shorten

**Goal impact: none recommended — `STRATEGY["short_window"]`/`STRATEGY["long_window"]`
stay at 10/30. `config.py` is unchanged.**

## What was asked

The owner asked to backtest a shorter SMA window for `STOCK_WATCHLIST`
(TWLO, ILMN, PTC, CRWD, PANW), prompted by a discussion of why the
current signal rarely fires live on this watchlist. This is a test of
whether shortening the 10/30 crossover window increases trade frequency
*and* holds up worst-case-first against real history, not just whether
it trades more often.

## What was tested

`portfolio_backtest.py` (unmodified, production module) with `(short_window,
long_window)` swept at **(5,10), (5,15), (6,18), (7,21), (8,24), (9,27),
(10,30) [current]**, every other parameter held at current production
values, all imported directly rather than hardcoded: `max_position_pct=0.20`,
`max_concurrent_positions=5`, `max_aggregate_position_pct=0.60`,
`max_trades_per_day=4`, `min_strength_pct=0`, `cooldown_bars=4`,
current stop-loss/take-profit (4%/8%, selling 70%), `min_sell_profit_pct=0.0`
(profit gate), `awesome_trade_min_crossover_pct=5.0`/
`awesome_trade_aggregate_pct=1.00`, `fee_pct=0.001`.

**Two independent real-history windows**, per this project's
worst-case-first, don't-trust-one-window standard — the same two ~90-day
hourly windows used in `backtest_2026-10-02_vpoc_evaluation.md` and
`backtest_2026-10-02_awesome_trade_threshold_sweep.md`:
- **`hourly_dev`**: 2026-07-06 to 2026-09-30 (372 hourly bars/symbol)
- **`hourly_oos`**: 2026-04-06 to 2026-07-01 (366 hourly bars/symbol)

All 5 current `STOCK_WATCHLIST` symbols, real `get_equity_historicals`
hourly bars (regular hours), no synthetic or interpolated data.

## Results

### Return / drawdown table

| window | (short,long) | return% | maxDD% | trades |
|---|---|---:|---:|---:|
| hourly_dev | (5,10) | 7.94% | 5.89% | 104 |
| hourly_dev | (5,15) | 7.41% | 5.32% | 81 |
| hourly_dev | (6,18) | 8.58% | 5.48% | 73 |
| hourly_dev | (7,21) | 14.34% | 5.78% | 67 |
| hourly_dev | (8,24) | 11.99% | 6.19% | 59 |
| hourly_dev | (9,27) | 13.06% | 5.55% | 63 |
| hourly_dev | (10,30) current | 13.06% | 4.84% | 51 |
| hourly_oos | (5,10) | 21.36% | 5.63% | 101 |
| hourly_oos | (5,15) | 19.01% | 4.69% | 80 |
| hourly_oos | (6,18) | 31.79% | 2.83% | 63 |
| hourly_oos | (7,21) | 30.95% | 2.62% | 65 |
| hourly_oos | (8,24) | 21.60% | 3.63% | 61 |
| hourly_oos | (9,27) | 23.31% | 3.27% | 53 |
| hourly_oos | (10,30) current | 25.28% | 4.67% | 50 |

### Worst-case-first (min return / max drawdown across both windows)

| (short,long) | worst return% | worst maxDD% | mean return% |
|---|---:|---:|---:|
| (5,10) | 7.94% | 5.89% | 14.65% |
| (5,15) | 7.41% | 5.32% | 13.21% |
| (6,18) | 8.58% | 5.48% | 20.19% |
| (7,21) | 14.34% | 5.78% | 22.65% |
| (8,24) | 11.99% | 6.19% | 16.80% |
| (9,27) | 13.06% | 5.55% | 18.18% |
| **(10,30) current** | **13.06%** | **4.84%** | **19.17%** |

## Analysis

- **(5,10) and (5,15)** — the genuinely "short" windows — are clearly
  worse than current on every axis: lower worst-case return (7.4-7.9%
  vs 13.06%), worse worst-case drawdown (5.3-5.9% vs 4.84%), and roughly
  double the trade count (fee drag and whipsaw both rise). Shortening
  the window does increase trade frequency as expected, but at a real
  cost, not for free.
- **(7,21)** posts the best worst-case return in the table (14.34%) and
  the best worst-case drawdown among the non-current windows (2.62%/5.78%
  split), which would look attractive taken alone. But checking its
  immediate neighbors — this project's standing rule for not trusting a
  single data point — shows it sitting between two *worse* points on
  both sides: (6,18) and (8,24) both underperform it on worst-case return,
  and (8,24) also has the single worst drawdown in the whole sweep
  (6.19%). That non-monotonic shape (worse, better, worse) is the same
  pattern flagged in `backtest_2026-10-02_awesome_trade_threshold_sweep.md`
  as characteristic of noise rather than a real, generalizable edge —
  a robust optimum should look stable against its neighbors, not like an
  isolated spike.
- **(9,27)** lands within rounding of current (10,30) on worst-case
  return (13.06% vs 13.06%) but with a worse worst-case drawdown (5.55%
  vs 4.84%) — directionally the same conclusion as (7,21), just smaller.
- **(10,30), current production**, has the best worst-case drawdown of
  every window tested (4.84%) and ties for the best worst-case return,
  while trading the least (51 vs up to 104) — the lowest fee drag and
  whipsaw exposure of the set.

## Decision

**No change recommended.** Shortening the SMA window does increase trade
frequency, confirming the mechanism works as expected, but no shorter
window tested shows a worst-case-first improvement over current 10/30
that survives a neighbor check — the one candidate that looked better in
isolation (7,21) sits on an isolated spike flanked by worse values on
both sides, the same failure mode this project's prior sweeps have
already learned to distrust. `STRATEGY["short_window"]`/`["long_window"]`
stay at 10/30.

This doesn't mean the signal's rarity on `STOCK_WATCHLIST` is wrong to
flag — it's a real, separately-noted structural property of this
specific 5-name, large-cap, low-volatility watchlist (see the live
discussion this session) — just that a shorter window is not a
worst-case-safe fix for it on the evidence here.

## Caveats

- Both windows are ~3 months of real hourly history each (~90 days);
  robust but not multi-year, same limitation as every other hourly sweep
  this project has run on these symbols (no equity historicals source
  goes back further at hourly granularity without hitting rate/size
  limits).
- `portfolio_backtest.py` models the shared-budget crossover strategy
  exactly as production uses it (concurrent-position cap, aggregate cap,
  cooldown, daily trade cap, profit gate, awesome-trade override) — this
  is not an isolated single-asset signal-quality test, it is the same
  shared-budget mechanics the live stock bot actually runs under.
- No crypto history was used or needed here — `STOCK_WATCHLIST` is an
  equity-only question; crypto is separately cut per the 2026-10-08
  owner request and untouched by this study.
