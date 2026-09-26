# SMA(10,30) window re-check — no change, reconfirmed on the current watchlist

**Goal impact: none — confirms an existing choice with fresh, more
relevant data rather than changing it.**

## What was asked

Owner asked whether SMA(10,30) — the core crossover signal `strategy.py`
uses for both crypto and stocks — is still the best window pair.

## Why this needed a fresh check, not just citing the old result

`backtest_2026-09-23.md`'s "SMA window sweep" already tested this
question once and kept (10,30) — but that sweep ran against an
**11-series set that was entirely crypto proxies** (IBIT/ETHA hourly +
GBTC split into 6 regimes + VSOL/BSOL/GSOL daily), never against any
`STOCK_WATCHLIST` name, and the watchlist itself has been revised
several times since (meme-coin removal, the large-cap stock swap, and
today's crypto/stock/VOLTRAP reviews). A three-day-old result on a
different asset set isn't good enough evidence for a shared-risk-budget
strategy that now trades both crypto and stocks together — re-ran it
against the **current** test bed instead.

## Test setup

Same 12-series bed used for every other recheck this session: all 10
current `STOCK_WATCHLIST` names (real `get_equity_historicals`, 90-day
hourly) + `IBIT`/`ETHA` (crypto still has no real historicals source).
Same methodology as the original sweep: real production code
(`backtest.backtest`, using `entry_filter.confirmed_signal` +
`exit_criteria.check_exit`), `min_strength_pct=0` (current production
setting), `cooldown_bars` scaled proportionally to each candidate's
`long_window` at the same 0.4× ratio the live 4h/(10,30) config already
uses, ranked **worst-case delta vs the (10,30) baseline first**
(this project's standing rule).

Candidates: (5,15), (5,20), (5,30), (8,25), (10,20), (10,30) [current],
(10,40), (15,30), (15,45), (20,50) — identical list to the original sweep.

## Result

| Window | Regimes helped | Mean delta vs (10,30) | Worst-case delta |
|---|---|---|---|
| **(10,30) — current** | baseline | 0.00% | 0.00% |
| (10,40) | 5/12 | -2.87% | -11.11% |
| (5,30) | 5/12 | +0.88% | -13.23% |
| (8,25) | 6/12 | -0.02% | -14.01% |
| (5,15) | 7/12 | +2.48% | -17.11% |
| (15,30) | 5/12 | -1.10% | -18.13% |
| (15,45) | 4/12 | -1.95% | -21.68% |
| (10,20) | 3/12 | -4.72% | -26.92% |
| (5,20) | 6/12 | -5.47% | -30.57% |
| (20,50) | 4/12 | -3.56% | -51.94% |

**No change — (10,30) remains the most worst-case-robust window pair,
now confirmed on the actual current watchlist.** Every alternative has
at least one symbol where it does meaningfully worse than (10,30) does
on that same symbol — worst-case deltas range from -11% to -52% — even
the two candidates with a slightly better *mean* delta ((5,15) at
+2.48%, (5,30) at +0.88%) still carry a worse worst case (-17.11% and
-13.23% respectively) than staying put. `(10,30)`'s own absolute
performance on this test bed: mean return +8.6% across the 12 series,
worst case -15.69% (MAIR) — a reasonable, not cherry-picked, baseline.

This reproduces the qualitative conclusion of the original 2026-09-23
sweep (shortening either window whipsaws in choppy conditions;
lengthening either misses the trend moves the strategy exists to catch)
with different absolute numbers on a materially different, more
relevant asset set — a genuine reconfirmation, not a restated old
result.

**`strategy.py`'s `short_window=10, long_window=30` unchanged.** No
config or code changes.
