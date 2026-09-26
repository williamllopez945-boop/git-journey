# Daily trade cap re-check: 3 → higher? — 2026-09-26

Owner question: "Will increase daily trade cap be better or worse."
**Answer: worse.** This re-confirms `backtest_2026-09-24_trade_cap.md`'s
original finding on fresher data (the current `STOCK_WATCHLIST`, with
`CRDO`/`PYPL` swapped in for `CHKP`/`HUBS` since that original test).

## Method

Reused the same 12-series bar-aligned test bed built for the
2026-09-26 concurrent-positions re-check (all 10 current
`STOCK_WATCHLIST` names + `IBIT`/`ETHA` crypto-beta proxies, 378 real
hourly bars, 2026-06-29 → 2026-09-26) - `portfolio_backtest.py`, current
production settings (`max_position_pct=0.20`,
`max_concurrent_positions=5`, `max_aggregate_position_pct=0.60`,
`cooldown_bars=4`), sweeping only `max_trades_per_day`.

## Full-window sweep

| Cap | Return | Max DD | Trades |
|---|---|---|---|
| 1 | -2.68% | 10.58% | 48 |
| 2 | +2.30% | 5.85% | 60 |
| **3** | **+8.94%** | **7.65%** | 80 |
| 4 | +5.79% | 6.59% | 97 |
| 5-15, uncapped | +5.79% | 6.59% | 99 |

**Cap=3 is the clear peak again** - same shape as the original
2026-09-24 finding (a cliff at 4, not a smooth curve). Caps of 4 and
above all collapse to the same plateau (trade activity never exceeds
what a ~4-per-day cap already allows on most days in this window), and
that plateau underperforms cap=3 on both return and (this time) even
comes out with worse drawdown than cap=3, not just lower return.

## Split-window robustness check

Same two independent halves as the concurrent-cap re-check (H1:
2026-06-29 → 2026-08-12, H2: 2026-08-12 → 2026-09-25):

| Cap | H1 Return | H2 Return |
|---|---|---|
| 1 | -4.84% | -0.30% |
| 2 | -2.49% | +1.65% |
| **3** | **+0.24%** | **+1.18%** |
| 4 | -4.40% | +2.95% |
| 5+ / uncapped | -4.40% | +2.49% |

**Cap=3 is again the only value positive in both halves** - the same
robustness signature the original 2026-09-24 backtest found. Cap 4+
looks fine in H2 alone but is solidly negative in H1 (-4.40%), meaning
its full-window number is propped up by one half and would mislead if
that were the only window tested - exactly the kind of overfitting
this project's methodology exists to catch (never trust a single
window, check that a value holds up when split).

## Conclusion

**Raising `max_trades_per_day` above 3 is worse, not better - confirmed
twice now, two days apart, on two overlapping but not identical stock
lineups.** No change made. `RISK_LIMITS["max_trades_per_day"]` stays at
3 (its current, already-correct value - this was a re-check, not a
change).

Same caveat as the original doc: crypto side still can't be tested
directly (no real crypto historicals source), so this is validated on
the stock+crypto-proxy test bed, not crypto specifically. Worth
re-running again if a much longer or differently-regimed window becomes
available.
