# Sustained excellent_watch entry — rejected, no change to scanner_signals.py

**Goal impact: none recommended — `scanner_signals.classify`'s entry logic
stays as-is (entries only on a confirmed fresh cross). No code or config
change.**

## What was asked

Owner observed that CRWD/PANW sat in `excellent_watch` for several
consecutive hourly cycles (2026-10-19/20) without ever generating a
`fresh_buy_cross`/`fresh_sell_cross`, and asked whether the entry
criteria could be loosened to "catch extended moves" — specifically,
whether a position should be allowed to open off a *sustained*
`excellent_watch` reading (a wide, persisting SMA10/SMA30 gap) even when
the state didn't just flip.

## What was tested

A standalone variant (not committed — scratch script only) layered on
top of `exit_criteria.check_exit`/`profit_gate` (unmodified, real
production code): if flat, no fresh cross this bar, SMA10 > SMA30, and
`|crossover_pct| >= 5%` (the same `EXCELLENT_CROSSOVER_PCT` constant
`scanner_signals.py` already uses for the watch-only alert) has held for
at least `sustained_entry_bars` consecutive bars since the last
bullish/bearish flip, enter anyway — guarded by an "already entered this
bullish run" flag so it can't fire every bar once satisfied.

Swept `sustained_entry_bars` ∈ {3, 6, 12} hourly bars, and separately
whether that guard resets only on a state flip (default) or also on any
full exit within the same still-bullish run (`reset_on_exit=True`, a more
generous variant that allows re-entering right after a stop-out if the
trend hasn't actually reversed).

**Baseline** is `backtest.backtest(..., min_strength_pct=0)` — this
explicitly passes `min_strength_pct=0` rather than relying on
`backtest.backtest()`'s own default (`None`), because `None` uses the
raw, unconfirmed `strategy.sma_crossover_signal` instead of
`entry_filter.confirmed_signal`'s 1-bar persistence check that live
production's `scanner_signals.classify` actually uses. Using the
default would have made the "baseline vs variant" comparison invalid
(confirmed by first running it with the wrong default: several series
showed spurious differences in trade count that had nothing to do with
the sustained-entry logic, until this was caught and fixed).

Same two independent real-history windows as
`backtest_2026-10-14_stock_sma_window_sweep.md` (worst-case-first,
don't-trust-one-window standard): `hourly_dev` (2026-07-06 to 2026-09-30,
372 bars/symbol) and `hourly_oos` (2026-04-06 to 2026-07-01, 366
bars/symbol), all 5 current `STOCK_WATCHLIST` symbols (TWLO, ILMN, PTC,
CRWD, PANW), real `get_equity_historicals` hourly bars, `fee_pct=0.001`,
current production stop-loss/take-profit (4%/8%, sell 70%) and
`min_sell_profit_pct=0.0` profit gate.

## Results

**10/10 series (5 symbols × 2 windows), every `sustained_entry_bars`
value, default guard (reset only on state flip): zero behavioral
difference from baseline.** The sustained-entry condition never fired a
single trade that didn't already happen via the normal fresh-cross path.

Diagnosing why: in every case where a bullish run's gap reached or
approached 5% while the strategy was flat, a fresh cross had *already*
fired near the start of that same run and opened a position (confirmed
directly — e.g. PANW `hourly_dev` reaches 5.81% crossover at bar 237
while flat, but only because the position opened at that run's start
(bar 231) was already stopped out at bar 234, and the "already entered
this run" guard correctly still counts that as "had our shot"). The
fresh-cross-plus-1-bar-confirmation logic already catches essentially
every move that goes on to reach `excellent_watch` territory in this
real data — there was no missed entry for a looser rule to pick up.

**With the more generous `reset_on_exit=True` guard** (allows
re-entering after a stop-out within the same still-bullish run), the
story changes in exactly **1 of 10 series** — PANW `hourly_dev`, at
`sustained_entry_bars` 3 and 6 (disappears again at 12, since the run
never gets that long before flipping):

| metric | baseline | variant (reset_on_exit) |
|---|---:|---:|
| return | **+13.72%** | **+1.90%** |
| max drawdown | 8.20% | 17.74% |
| win rate | 66.7% | 57.1% |
| round trips | 6 | 7 |

The other 9/10 series are unaffected even with this more generous guard.

## Decision

**Not adopted.** Worst-case-first, the only real-data case this change
ever touches is a clear loss: it re-buys back into a move immediately
after being stopped out of the same run, which needed a second
protective exit and converted a solid return into a near-flat one with
more than double the drawdown — exactly the re-entry/whipsaw risk
`entry_filter.py`'s 1-bar confirmation delay and `scanner_signals.py`'s
2-cycle pending-state design already exist to avoid (see
`entry_filter.py`'s own docstring and `backtest_2026-09-23.md`). The
other 9/10 series show the rule simply never does anything, because the
existing fresh-cross logic already captures the move before the gap
widens enough to be "sustained."

**Separately, structural point for the specific CRWD/PANW case that
prompted this**: that was a *bearish* sustained `excellent_watch` (SMA10
well below SMA30), and this bot is long-only (no shorting). A sustained
entry rule, loosened any way, can only ever open a NEW long position on
a sustained *bullish* reading — it has no mechanism to act on an
extended bearish move with no held position to protect. So even had this
backtest come back positive, it would not have changed anything about
today's actual CRWD/PANW situation; it only affects potential missed
bullish entries, which — per the results above — essentially don't occur
in this data.

## What this doesn't establish

- Only 2 real windows, ~1 year combined, 5 symbols — a longer or
  different regime could behave differently, same caveat every prior
  study here carries.
- Only tested the `reset_on_exit` guard as a binary toggle, not partial
  re-entry sizing or a cooldown-after-stop-out hybrid.
- `sustained_entry_bars` swept at 3/6/12 only; finer-grained values
  weren't tried, though the one case that mattered (PANW dev) was a loss
  at both values where it fired, which doesn't suggest a finer sweep
  would flip the conclusion.
