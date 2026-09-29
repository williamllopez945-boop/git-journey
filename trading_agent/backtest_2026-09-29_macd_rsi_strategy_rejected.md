# MACD+RSI combo strategy — backtested, rejected (2026-09-29)

Owner requested testing a specific, source-verified MACD+RSI strategy as
a possible replacement for the current SMA(10,30) crossover. Backtested
before any implementation, per COLLABORATION.md.

## The exact rules tested

Source: general web research into crypto/stock trading strategies (not
this project's own history). Confirmed-specific rules only - a vaguer
"73% win rate" version citing an undisclosed third filter was explicitly
**not** used; this is the fully-specified alternative found in the same
research, tested on BTC 4H by its original source (38 signals, 58% win
rate, 1.72 profit factor; 1.81 with the RSI exit added):

- **Entry**: MACD(12,26,9) line crosses above its signal line, AND
  RSI(14) < 60, AND price > SMA(200).
- **Exit**: RSI(14) >= 75.
- Standard Wilder-smoothed RSI (this project's own `rsi_filter.py` is
  deliberately non-Wilder to match `strategy.py`'s plain-mean SMA
  convention - a fresh, faithful implementation was used here instead,
  to test the sourced strategy as actually described, not our own
  variant of it).

## Method

Standalone scratch implementation (not a change to production
`strategy.py`). Two passes on the same real data as today's other
backtests (12 symbols incl. `VTRS`, 1149-bar real window):

1. **Bare methodology** (no stop-loss, matching the source's own
   approach) - a sanity check that the implementation produces
   sensible signals, not a real evaluation (3-6 signals per symbol on
   our 9-month window is too small a sample to confirm or refute the
   source's own longer-history statistics).
2. **With this project's own risk management layered on** (4% SL, 8%
   TP/70% partial, `fee_pct=0.001`) - the real "should we switch"
   question, since we'd never deploy an entry signal without our
   existing protective-exit layer.

## Result: broadly underperforms, one narrow exception

**Full-period return, current SMA vs. MACD+RSI (both with our risk
management):**

| Symbol | SMA (current) | MACD+RSI |
|---|---|---|
| CRWD | **66.65%** | -6.77% |
| PANW | 47.69% | 35.42% |
| TWLO | **73.64%** | 0.71% |
| ILMN | **79.19%** | 26.84% |
| IR | **15.85%** | -11.31% |
| PTC | -9.83% | -16.28% |
| CRDO | **87.97%** | 23.01% |
| VTRS | **5.32%** | -8.93% |
| AR | **14.80%** | 3.58% |
| PYPL | -0.26% | **11.22%** |
| IBIT | -9.44% | **10.21%** |
| ETHA | 4.43% | **8.30%** |

**SMA wins on 9 of 12 symbols**, often by a wide margin on the
strongest trend names (CRDO, TWLO, ILMN, CRWD) - the same structural
issue found when plain RSI was tested and rejected on 2026-09-23: this
is a trend-following strategy, and a mean-reversion-flavored entry
(buy oversold, exit on RSI recovery to 75) exits trending winners too
early, giving back exactly the upside SMA crossover exists to capture.

**MACD+RSI wins on 3 of 12** - both crypto proxies (IBIT, ETHA) and
PYPL - a real, consistent signal within this small sample, but not
enough to justify a strategy-level switch.

## Decision: rejected, not adopted

Same conclusion, same root cause, as the 2026-09-23 RSI rejection:
this project's edge comes from riding a trend as it builds, and any
mean-reversion-style filter (RSI overbought/oversold, or this
MACD+RSI combo's RSI-75 exit) works against that edge more often than
it helps. No code change - `strategy.py` unchanged.

## What this doesn't establish

- Small per-symbol sample (3-6 signals bare, similar with risk
  management) on our 9-month window - not a strong test of the
  source's own claimed statistics, which were presumably computed on a
  longer BTC-specific history.
- The crypto-proxy edge (IBIT/ETHA) is a real, consistent pattern in
  this data but hasn't been tested across a longer or different
  window - not proposed as a targeted crypto-only addition here, just
  noted for a future pass if worth pursuing.
- The vaguer "73% win rate" version (an undisclosed third mean-reversion
  filter) was not tested - its source page was blocked by this
  session's network egress proxy, and the exact rule was never
  confirmed.
