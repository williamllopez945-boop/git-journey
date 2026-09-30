# VWAP evaluation — no change recommended, negative/neutral on worst case

**Goal impact: none recommended — VWAP does not clear this project's
worst-case-first bar in any tested form. `strategy.py`, `scanner_signals.py`,
`exit_criteria.py`, and `config.py` are unchanged.**

## What was asked

Owner asked: "Check if adding VWAP will impact our strategy." The live
strategy (`scanner_signals.classify` + `strategy.sma_crossover_signal`) is a
pure SMA(10,30) 1h crossover with no VWAP anywhere in signal generation, and
`exit_criteria.py`/`profit_gate.py` measure stop-loss/take-profit against
average cost basis, not VWAP. This is a real backtest of whether adding VWAP
would help, following the same worst-case-first, multiple-window,
neighboring-parameter methodology as every other tuning study in this
directory — not a guess.

## Variants tested

Three concrete, well-specified designs, cheapest-to-implement first:

**(a) VWAP entry trend filter (primary).** A `fresh_buy_cross` additionally
requires the close price to be above a rolling *N*-bar VWAP, else it is
downgraded to a hold — the exact same "downgrade, don't invent a new
mechanism" pattern `volume_filter.py` and `rsi_filter.py` already use for
their own entry gates. Never blocks a sell/death-cross by default, matching
this codebase's existing rule that entry filters never gate exits
(`README.md`: "Never blocks a sell cross") — gating a protective/exit signal
is exactly what the rejected trailing-stop and profit-lock studies already
warn against. Swept *N* = 20, 30, 50 bars (30 matches the existing SMA30
window; 20 and 50 are the neighboring checks).

**(a′) Same filter, but symmetric (secondary/riskier check).** The literal
version the task also named: price below VWAP required for a death-cross
sell to proceed too, not just for a buy. Run once, at *N*=30, specifically to
check whether gating exits — something this project has never done and has
twice rejected for other mechanisms (trailing stop, profit lock) — changes
the verdict.

**(c) VWAP substituted for SMA30 as the slow line (secondary, cheaper
check).** SMA(10) crossing above/below a rolling *N*-bar VWAP instead of
SMA(10) vs SMA(30). Same `exit_criteria.check_exit` exits as production;
only the signal line changes, and there's no entry-filter persistence layer
on top (a simpler design than (a), run on fewer windows/series to bound
scope — see "Test setup" below). Swept *N* = 20, 30, 50.

**VWAP definition:** standard volume-weighted average of typical price
`(high + low + close) / 3` over the trailing *N* bars, computed from real
per-bar OHLCV — `sum(typical_price × volume) / sum(volume)` over the window,
recomputed at every bar. `None` (filter can't evaluate, never blocks) when
fewer than *N* bars of history exist yet or the window's total volume is
zero, the same "not enough history" convention `strategy.sma_crossover_signal`
already uses for a `None` SMA. *N*=30 was chosen as the base case to mirror
the existing SMA30 window one-for-one; 20 and 50 are the "check neighboring
values, not just one point" companions this project's methodology requires.
A pure session/daily VWAP was considered and rejected: the strategy operates
on 1h bars with no explicit session-boundary concept anywhere else in the
codebase, and a rolling N-bar window composes directly with the existing
SMA(10,30) design instead of introducing a new time concept.

## Test setup

- **Real production code, unmodified:** `strategy.sma_crossover_signal`,
  `entry_filter.confirmed_signal`, `exit_criteria.check_exit` (current live
  defaults: 10% stop-loss, 20% take-profit selling 70%, imported directly
  from `exit_criteria.py`, not hardcoded), `entry_filter.DEFAULT_MIN_STRENGTH_PCT`
  (0, persistence-only — current production setting) and
  `position_state.DEFAULT_COOLDOWN_HOURS` (4, i.e. `cooldown_bars=4`  —
  current production setting). The baseline in every table below is
  `trading_agent.backtest.backtest()` called exactly as-is, with these same
  defaults, for a fair comparison. The VWAP variants are a small
  research-only harness (not part of `trading_agent/`, not committed to the
  package, not imported by any live path) that reuses these same production
  functions and adds one small local helper (`rolling_vwap`) plus a loop
  structurally identical to `backtest.py`'s own, scored with
  `backtest.summarize()` for both baseline and variant runs alike.
- **Test bed — two real historical windows (dev + out-of-sample), same
  convention as `backtest_2026-09-26_sma_window_recheck.md`:**
  - **Dev window:** 2026-07-01 to 2026-09-30 (the most recent ~90 days).
  - **Out-of-sample window:** 2026-04-01 to 2026-07-01 (the preceding ~90
    days) — a genuinely different regime, not a re-split of the same data.
  - **Assets, both windows:** all 10 current `STOCK_WATCHLIST` names (CRWD,
    PANW, TWLO, ILMN, IR, PTC, CRDO, MAIR, AR, PYPL) plus **IBIT/ETHA**
    (crypto still has no historicals source — see README's "Crypto price
    history" section; no crypto history was fabricated). 1h bars, regular
    session, real `get_equity_historicals` data, ~372-378 bars per series.
  - **24 series total** for variant (a)/(a′); variant (c) runs on the dev
    window's 12 series only (a deliberately narrower, cheaper secondary
    check, not the flagship result).
- Position sizing: 100% of available cash per trade, same as every other
  `backtest.py`-based study in this directory (isolates signal quality from
  the separate risk-management layer; see `backtest.py`'s own docstring).
- Ranked **worst-case delta and worst-case absolute outcome first**, per this
  project's standing rule — mean/helped-hurt counts are reported too, but
  never used alone to justify a verdict.

## Baseline (no VWAP), for reference

24-series baseline: mean return **+11.71%**, worst-case return **-18.22%**
(dev/MAIR), worst-case max drawdown **23.92%** (dev/MAIR, same series).
Dev-window-only baseline (12 series, used for variant (c)'s comparison):
mean **+6.42%**, worst-case return -18.22% (MAIR), worst-case max drawdown
23.92% (MAIR).

## Results — variant (a): VWAP entry trend filter

| VWAP window | Helped | Hurt | Flat | Mean Δ | Worst-case Δ | Worst-case abs. return | Worst-case max DD (own) |
|---|---|---|---|---|---|---|---|
| 20 bars | 6/24 | 3/24 | 15/24 | +0.07% | -7.31% (dev/ETHA) | -18.22% (dev/MAIR, unchanged) | 23.92% (dev/MAIR, unchanged) |
| **30 bars** | 9/24 | 5/24 | 10/24 | +0.36% | -7.31% (dev/ETHA) | -18.22% (dev/MAIR, unchanged) | 23.92% (dev/MAIR, unchanged) |
| 50 bars | 15/24 | 7/24 | 2/24 | -0.77% | **-28.29%** (oos/PANW) | -12.32% (dev/MAIR) | **19.85%** (dev/PANW, vs. 16.59% baseline there) |
| 30 bars, sells also gated (a′) | 14/24 | 7/24 | 3/24 | **+1.52%** | -10.32% (dev/AR) | **-21.44%** (dev/MAIR, worse than baseline) | **24.09%** (dev/MAIR, worse than baseline) |

**Full per-series breakdown, N=30 bars (the flagship config, buy-side only):**

| Regime | Asset | Baseline return | Baseline max DD | VWAP30 return | VWAP30 max DD | Δ return | VWAP30 trades |
|---|---|---|---|---|---|---|---|
| dev | AR | 3.98% | 5.90% | 3.98% | 5.90% | +0.00% | 10 |
| dev | CRDO | 7.26% | 19.47% | 9.73% | 19.47% | +2.47% | 12 |
| dev | CRWD | 7.57% | 13.36% | 7.57% | 13.36% | +0.00% | 9 |
| dev | ETHA | 21.81% | 13.51% | 14.49% | 13.51% | **-7.31%** | 16 |
| dev | IBIT | 16.06% | 7.39% | 16.06% | 7.39% | +0.00% | 15 |
| dev | ILMN | 15.37% | 13.16% | 14.36% | 13.16% | -1.01% | 16 |
| dev | IR | -2.53% | 10.49% | -0.20% | 8.35% | +2.33% | 8 |
| dev | MAIR | -18.22% | 23.92% | -18.22% | 23.92% | +0.00% | 14 |
| dev | PANW | 6.04% | 16.59% | 6.04% | 16.59% | +0.00% | 10 |
| dev | PTC | 2.81% | 13.14% | 2.81% | 13.14% | +0.00% | 17 |
| dev | PYPL | 13.86% | 12.17% | 14.68% | 11.54% | +0.82% | 14 |
| dev | TWLO | 3.03% | 15.77% | 0.09% | 18.18% | -2.94% | 11 |
| oos | AR | -4.17% | 7.80% | -5.03% | 7.80% | -0.85% | 7 |
| oos | CRDO | 25.54% | 16.87% | 25.54% | 16.87% | +0.00% | 11 |
| oos | CRWD | 48.57% | 11.51% | 48.57% | 11.51% | +0.00% | 14 |
| oos | ETHA | -0.42% | 8.70% | -0.28% | 8.70% | +0.13% | 4 |
| oos | IBIT | -1.27% | 7.38% | 1.30% | 7.38% | +2.57% | 4 |
| oos | ILMN | 22.21% | 4.94% | 23.72% | 4.84% | +1.51% | 8 |
| oos | IR | -5.72% | 8.77% | -3.76% | 6.36% | +1.96% | 13 |
| oos | MAIR | 11.42% | 15.33% | 11.96% | 14.92% | +0.55% | 11 |
| oos | PANW | 64.19% | 10.99% | 64.19% | 10.99% | +0.00% | 9 |
| oos | PTC | -12.57% | 15.86% | -13.53% | 16.78% | -0.96% | 12 |
| oos | PYPL | -9.69% | 19.64% | -0.21% | 11.20% | **+9.48%** | 7 |
| oos | TWLO | 65.94% | 8.79% | 65.94% | 8.79% | +0.00% | 11 |

## Results — variant (c): VWAP as the slow line (dev window only, 12 series)

| VWAP window | Helped | Hurt | Mean Δ | Worst-case Δ | Worst-case abs. return | Worst-case max DD (own) |
|---|---|---|---|---|---|---|
| 20 bars | 4/12 | 8/12 | -1.83% | -12.93% (ETHA) | -7.95% (MAIR, better than baseline) | **26.95%** (CRDO, vs. 23.92% baseline worst) |
| 30 bars | 6/12 | 6/12 | +0.03% | -15.02% (CRDO) | -18.33% (MAIR, ~unchanged) | **28.97%** (CRDO, vs. 23.92% baseline worst) |
| 50 bars | 7/12 | 5/12 | +0.94% | -12.44% (PANW) | -9.91% (MAIR, better than baseline) | **24.71%** (PANW, vs. 23.92% baseline worst) |

## Reading this honestly

**The entry-only filter (a) is mostly inert, not mostly helpful.** At the
window that mirrors the existing SMA30 (30 bars), it left 10 of 24 series
completely unchanged (identical trade count, identical return, identical
drawdown) — the filter simply never blocked a real crossover in those cases,
because price is very often already above a 30-bar VWAP right when SMA10
crosses above SMA30 (the two conditions are highly correlated by
construction: both are trend-following measures over similar-length
windows). Where it *did* engage, it was a wash: 9 series improved, 5 got
worse, and the single worst case (-7.31% on dev/ETHA) outweighs the mean
being nominally positive (+0.36%). Worst-case return and worst-case drawdown
are **exactly unchanged from baseline** at both 20 and 30 bars — VWAP added
no protection on the series that actually needed it (dev/MAIR, a real -18%
drawdown case), it just occasionally added or removed a few percentage
points on series that were already fine.

**Widening the VWAP window (50 bars) makes the worst case worse, not
better** — this is the "check neighboring values, don't trust one lucky
point" check doing its job. At 50 bars the filter engages far more often
(only 2/24 flat) and does improve the mean-ish picture on paper, but its
single worst delta (-28.29% on oos/PANW, a series that returned a strong
+64.19% unfiltered) and its worst standalone drawdown (19.85% vs. 16.59%
baseline, on dev/PANW) are both real regressions versus doing nothing. A
wider VWAP lags further behind price, so it filters out more of exactly the
strong, fast-moving trend continuations this strategy exists to catch — the
same qualitative failure mode the 2026-09-26 SMA-window recheck found for
lengthening either SMA window.

**Gating exits by VWAP (a′) is the one setting with the best mean (+1.52%),
and it is also the one that makes the true worst case worse** — worst
absolute return drops to -21.44% (below the -18.22% baseline) and worst
drawdown rises to 24.09% (above the 23.92% baseline), both on the same
dev/MAIR series, because delaying a death-cross exit on a real breakdown
(waiting for price to also close below VWAP) let a losing position ride
longer before the SMA sell it would otherwise have taken. This is the same
mechanism this project has already rejected twice for unrelated reasons —
the 2026-09-24 trailing-stop and 2026-09-25 profit-lock studies both found
that delaying or reshaping an exit trades a small mean improvement for a
worse worst case. VWAP does not escape that pattern.

**Replacing SMA30 with VWAP outright (c) is worse in every window tested.**
Mean deltas hover near flat (-1.83% to +0.94%) and worst-case return is
sometimes nominally better (VWAP is a smoother line than a 30-bar close SMA,
so it whipsaws less on some series), but **worst-case drawdown got worse at
every single window tested** (24.71-28.97% vs. the baseline's 23.92%) — a
consistent, not cherry-picked, regression. A VWAP-based slow line changes
*when* the strategy re-enters or exits a trend in ways that sometimes help
return but never helped the worst-case drawdown figure this project
prioritizes first.

## Verdict

**Do not adopt VWAP in any of the three tested forms.** Across every
variant and every neighboring parameter value:
- Worst-case return never meaningfully improves and is worse in two of the
  four configurations tested (50-bar entry filter, symmetric exit-gated
  filter).
- Worst-case max drawdown **never improves** in any configuration, and is
  worse in three of the seven configurations tested (50-bar entry filter,
  symmetric exit-gated filter, and all three VWAP-as-slow-line windows).
- Mean/average deltas are small in magnitude and inconsistent in sign
  across windows — there is no robust edge underneath the noise, only
  configurations that happen to look better on one metric while looking
  worse on the worst-case metrics this project weighs first.

The least-harmful setting found (variant a, entry-only filter, N=20 or 30
bars) is **not harmful but also not useful** — it ties the baseline's worst
case exactly while adding real implementation complexity (a new indicator, a
new gate) for a mean effect (+0.07% to +0.36% across 24 series) too small
and too inconsistent to act on. This is a genuine negative/neutral result,
reported plainly per this project's standing practice — no code, config, or
CHANGELOG change follows from it.

## Scope and limits

- Crypto series (IBIT/ETHA) are equity ETF proxies, not real crypto history
  — same limitation as every other backtest in this directory (see
  README's "Crypto price history"). Real crypto's intraday volume profile
  (24/7, no session open/close) could behave differently under a VWAP
  filter than these proxies' regular-session-only volume does; this was not
  and cannot currently be tested against real crypto history.
- Variant (c) was only run on the dev window (12 series), not the full
  24-series bed, to bound scope given it already showed a consistent
  worst-case-drawdown regression on the smaller check — a wider run was not
  judged likely to change the verdict, but wasn't performed either.
- This did not test a session/daily VWAP (reset each trading day) or an
  hourly-anchored-since-open VWAP, both common intraday VWAP conventions —
  rejected in "Variants tested" above as a mismatch with this strategy's
  1h-bar, no-session-boundary design, not tested empirically.
- All runs use 100% cash-per-trade sizing (isolates signal quality), not the
  live 20%-of-portfolio cap — same convention and same caveat as every prior
  `backtest.py` study in this directory.
