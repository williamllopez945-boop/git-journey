# Income sleeve: does adding MACD/RSI-oversold gating beat the 20-day range signal? (2026-10-09)

Owner question: "Is the 20 day range the best look? Include MACD and
RSI indicators and buy when momentum hits oversold." Answered with a
real backtest per COLLABORATION.md's rule ("Any strategy parameter
change needs real historical backtesting first... Read the rejected
trailing-stop, profit-lock, RSI, and liquidity-displacement studies
before proposing to enable those ideas again") rather than opinion.

**Important scope note**: `backtest_2026-09-29_macd_rsi_strategy_rejected.md`
already rejected a MACD+RSI entry for the **main crypto/stock bot**
(trend-following SMA(10,30) crossover) - that rejection's stated root
cause was "a mean-reversion-style filter works against a
trend-following edge." The income sleeve is *already* mean-reversion
(buy the dip), so that specific root cause doesn't automatically carry
over. This doc runs the income sleeve's own test rather than assuming
the prior rejection answers it.

## Data

`get_equity_historicals(symbols=INCOME_WATCHLIST + ["AMDW","GOOW","NVDW"],
interval="day", bounds="regular", start_time=2024-01-01)`, filtered to
`interpolated != true` (real trading days only, each symbol's own real
inception onward - same filtering `backtest_2026-10-07_income_sleeve_full_history.md`
used). Real bar counts: YMAX 685, YMAG 676, ULTY 655, CHPY 381, GPTY 430,
AMDW 305, GOOW 305, NVDW 412.

## Method

Reused production `income_signals.classify_dip` (20-day range,
`DIP_ENTRY_THRESHOLD=0.10`) and `income_exit.check_income_exit`
unchanged. Built a standalone (not committed to `trading_agent/`) MACD(12,26,9)
implementation and reused `rsi_filter.rsi` (period 14) to test four entry
variants against the identical exit rule, scored with `backtest.summarize`:

1. **baseline** - today's production signal, `classify_dip` alone.
2. **rsi_only** - `classify_dip` AND RSI(14) <= 30 (oversold).
3. **macd_only** - `classify_dip` AND MACD line crossing above its
   signal line that same bar (bullish cross).
4. **rsi_and_macd** - `classify_dip` AND both of the above (the literal
   combination the owner's question described).

Starting cash $100/symbol, frictionless, same convention as
`income_backtest.py`. **Same price-only caveat as every other income-sleeve
backtest in this project**: no distribution cash flow is modeled.

## Results

RSI threshold 30 unless noted; a 40 variant is included to check
sensitivity.

| Symbol | baseline (n, ret%) | rsi_only@30 (n, ret%) | rsi_only@40 (n, ret%) | macd_only (n, ret%) | rsi_and_macd (n, ret%) |
|---|---|---|---|---|---|
| YMAX | 12, -56.98 | 13, -49.27 | 12, -58.24 | 1, -10.63 | 1, -10.63 |
| YMAG | 9, -23.11 | 9, -22.39 | 9, -23.11 | 2, -15.78 | 0, 0.00 |
| ULTY | 23, -80.42 | 20, -78.44 | 23, -80.42 | 4, -30.34 | 0, 0.00 |
| CHPY | 2, +17.94 | 2, +20.87 | 2, +18.80 | 0, 0.00 | 0, 0.00 |
| GPTY | 4, -6.70 | 4, -1.98 | 4, -5.07 | 0, 0.00 | 0, 0.00 |
| AMDW | 5, +79.89 | 5, +29.77 | 5, +79.89 | 0, 0.00 | 0, 0.00 |
| GOOW | 2, +5.57 | 2, +6.27 | 2, +5.57 | 0, 0.00 | 0, 0.00 |
| NVDW | 4, +3.10 | 2, +13.47 | 4, +3.69 | 0, 0.00 | 0, 0.00 |

## Observations

- **RSI-oversold alone is close to a wash.** It changes which bars
  qualify slightly (a handful fewer/more trades per symbol) and the
  sign of the effect is mixed - helps YMAG/GPTY/NVDW a little, hurts
  YMAX/AMDW, roughly flat elsewhere. No symbol shows a clear, consistent
  improvement from this gate alone, at either threshold tested.
- **MACD-bullish-cross is not a mild filter here - it functionally
  disables the sleeve.** 6 of 8 symbols got **zero** entries at all
  over 300-685 real bars; the other two dropped to 1-4 entries. The
  reason is structural, not a bug: these are covered-call income ETFs
  whose price drifts down most weeks as distributions are paid out, so
  a 20-day dip and a genuine MACD bullish crossover (which wants
  sustained upward momentum, not just a local low) rarely line up.
  Where it did fire (YMAX, YMAG, ULTY), the few trades it allowed did
  show smaller losses than baseline - but on 1-4 data points per
  symbol, that is not evidence of a working strategy, it's evidence of
  a filter so strict it mostly sits in cash.
- **Combining both (the owner's literal ask) is the most restrictive
  of all**: 0 entries on 6 of 8 symbols, 1 entry on YMAX, 0 on YMAG and
  ULTY (where MACD alone had allowed a couple). Requiring RSI oversold
  and a MACD bullish cross on the same bar, on top of the existing
  20-day dip condition, is a triple gate - the joint probability of all
  three lining up on a structurally-declining series is low enough that
  the sleeve would barely trade.

## Answer to "is the 20-day range the best look?"

On this data: better than adding MACD, roughly a wash against adding
RSI alone, and already shown (per the 2026-10-07 doc) to beat
buy-and-hold on price alone for 3 of 4 longer-history names despite
negative absolute returns. The real, already-flagged weakness in the
20-day-range signal is not that it lacks a momentum filter - it's the
win rate on repeat sells (ULTY's 16.7%, per the 2026-10-07 doc). Gating
entries harder with MACD doesn't fix that; it mostly just stops the
sleeve from entering at all, which isn't the same thing as entering
better.

## Decision

**No code change.** `classify_dip`/`income_signals.py` stay as-is; no
MACD module added to the sleeve's production entry path.
`INCOME_WATCHLIST`, `INCOME_RISK_LIMITS`, `INCOME_AUTO_EXECUTE`
untouched, per COLLABORATION.md (owner approval required for any of
those). This is a negative result, reported plainly rather than
reframed as a partial win - same standing practice as
`backtest_2026-09-29_macd_rsi_strategy_rejected.md` and
`backtest_2026-09-25_profit_lock.md`.

**What might still be worth a separate look, if the owner wants it**:
not momentum gating, but tightening the *exit* side (ULTY's repeat
stop-outs) - a different question than the one asked here, not explored
in this doc.
