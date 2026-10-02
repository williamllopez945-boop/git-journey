# VPOC (Volume Point of Control) evaluation — no change recommended

**Goal impact: none recommended — VPOC does not clear this project's
worst-case-first bar in a way that justifies adoption in any tested form.
`strategy.py`, `scanner_signals.py`, `exit_criteria.py`, and `config.py` are
unchanged.**

## What was asked

Owner asked: "Run a backtest with the VPOC and see if we should incorporate
it to our strategy." The live strategy has no volume-profile concept
anywhere — `scanner_signals.classify` only uses *relative* volume (current
bar's volume vs. its own trailing average, via `volume_filter.py`) as a
binary entry gate, never a price-level volume distribution. This is a real
backtest of whether a rolling Volume Point of Control (the price level that
accumulated the most volume over a lookback window — a support/resistance
"magnet" concept from volume-profile analysis) would help, following the
same worst-case-first, multiple-window, neighboring-parameter methodology as
every other tuning study in this directory (most recently
`backtest_2026-09-30_vwap_evaluation.md`, whose structure this study
mirrors one-for-one for direct comparability) — not a guess.

## VPOC definition

Hourly OHLCV bars don't carry a real intra-bar volume-at-price distribution
(no tick data), so VPOC here is the standard OHLCV-only approximation: over
the trailing *N* bars (this bar included), take the window's low..high
range, split it into 20 equal-width price buckets, and for each bar in the
window distribute that bar's volume across the buckets its own `[low, high]`
range overlaps, proportional to the overlap width (assumes volume is spread
uniformly across each bar's own range — the best available proxy without
tick data). VPOC is the midpoint price of the bucket that received the most
accumulated volume. `None` (filter can't evaluate, never blocks) when fewer
than *N* bars of history exist yet or the window is degenerate (zero price
range) — the same "not enough history" convention `strategy.sma_crossover_signal`
already uses for a `None` SMA. The 20-bucket resolution was fixed, not swept,
to bound scope (same precedent as the VWAP study bounding its variant (c) to
a narrower run) — only the lookback window *N* is swept below.

## Variants tested

Three concrete designs, directly paralleling the VWAP study's own three
variants so the two studies read as a matched pair:

**(a) VPOC entry trend filter (primary).** A `fresh_buy_cross` additionally
requires the close price to be at/above the rolling *N*-bar VPOC, else it is
downgraded to a hold — the same "downgrade, don't invent a new mechanism"
pattern `volume_filter.py`, `rsi_filter.py`, and the VWAP study's own variant
(a) already use. Never blocks a sell/death-cross by default (this codebase's
standing rule: entry filters never gate exits — see README.md). Swept
*N* = 20, 30, 50 bars (30 mirrors the existing SMA30 window; 20/50 are the
neighboring checks).

**(a′) Same filter, but symmetric (secondary/riskier check).** Price below
VPOC also required for a death-cross sell to proceed, not just for a buy —
run once, at *N*=30, to check whether gating exits (something this project
has rejected three times already: trailing-stop, profit-lock, and VWAP's own
a′) changes the verdict for VPOC too.

**(c) VPOC substituted for SMA30 as the slow line (secondary, cheaper
check).** SMA(10) crossing above/below the rolling *N*-bar VPOC instead of
SMA(10) vs SMA(30), using the same `exit_criteria.check_exit` exits as
production. Swept *N* = 20, 30, 50, dev window only (12 series) — bounded
scope, same precedent as the VWAP study's own variant (c).

## Test setup

- **Real production code, unmodified:** `strategy.sma_crossover_signal`
  (baseline only), `exit_criteria.check_exit` (current live defaults: 4%
  stop-loss, 8% take-profit selling 70%, imported directly from
  `exit_criteria.py`), `entry_filter.DEFAULT_MIN_STRENGTH_PCT` (0,
  persistence-only — current production setting), `position_state.DEFAULT_COOLDOWN_HOURS`
  (4 bars — current production setting), and `profit_gate.blocks_sell_cross`
  /`gate_floor_should_force_exit` (`MIN_SELL_PROFIT_PCT`=0.0,
  `GATE_MAX_HOLD_HOURS`=None — current production settings). The baseline in
  every table below is `trading_agent.backtest.backtest()` called exactly
  as-is with these same defaults. The VPOC variants are a small research-only
  harness (not part of `trading_agent/`, not committed to the package, not
  imported by any live path) that reuses these same production functions and
  adds one local helper (`rolling_vpoc`) plus loops structurally identical to
  `backtest.py`'s own, scored with `backtest.summarize()` for baseline and
  variants alike.
- **Test bed — two real historical windows (dev + out-of-sample):**
  - **Dev window:** 2026-07-06 to 2026-10-01 (the most recent ~90 days).
  - **Out-of-sample window:** 2026-04-06 to 2026-07-02 (the preceding ~90
    days) — a genuinely different regime, not a re-split of the same data.
  - **Assets, both windows:** all 10 current `STOCK_WATCHLIST` names (CRWD,
    PANW, TWLO, ILMN, IR, PTC, CRDO, VTRS, AR, PYPL) plus **IBIT/ETHA**
    (crypto still has no historicals source — see README's "Crypto price
    history" section; no crypto history was fabricated). 1h bars, regular
    session, real `get_equity_historicals` OHLCV data, 372-378 bars per
    series.
  - **24 series total** for variants (a)/(a′); variant (c) runs on the dev
    window's 12 series only.
- Position sizing: 100% of available cash per trade, same convention as
  every other `backtest.py`-based study in this directory (isolates signal
  quality from the separate risk-management layer). No transaction costs or
  slippage modeled — same unaddressed limitation flagged by every prior
  study in this directory.
- Ranked **worst-case delta and worst-case absolute outcome first**, per
  this project's standing rule — mean/helped-hurt counts are reported too,
  but never used alone to justify a verdict.

## Baseline (no VPOC), for reference

24-series baseline: mean return **+13.45%**, worst-case return **-13.64%**
(oos/IBIT), worst-case max drawdown **18.26%** (oos/PTC). Dev-window-only
baseline (12 series, used for variant (c)'s comparison): mean **+11.56%**,
worst-case return -2.89% (PTC), worst-case max drawdown 12.54% (CRDO).

## Results — variant (a): VPOC entry trend filter

| VPOC window | Helped | Hurt | Flat | Mean Δ | Worst-case Δ | Worst-case abs. return | Worst-case max DD (own) |
|---|---|---|---|---|---|---|---|
| 20 bars | 6/24 | 5/24 | 13/24 | +0.05% | -8.74% (dev/ETHA) | -9.09% (oos/IBIT, better than -13.64% baseline) | 16.77% (oos/PYPL, better than 18.26% baseline) |
| **30 bars** | 6/24 | 7/24 | 11/24 | -0.36% | -12.92% (dev/AR) | -8.53% (oos/IBIT, better than -13.64% baseline) | 16.77% (oos/PYPL, better than 18.26% baseline) |
| 50 bars | 8/24 | 7/24 | 9/24 | -0.04% | -17.87% (oos/PANW) | -4.07% (oos/AR, unchanged — AR's own baseline) | 16.77% (oos/PYPL, better than 18.26% baseline) |

**Full per-series breakdown, N=30 bars (the flagship config, buy-side only):**

| Regime | Asset | Baseline return | Baseline max DD | VPOC30 return | VPOC30 max DD | Δ return | VPOC30 trades |
|---|---|---|---|---|---|---|---|
| dev | AR | 9.22% | 6.39% | -3.70% | 8.72% | **-12.92%** | 6 |
| dev | CRDO | 10.66% | 12.54% | 15.52% | 11.62% | +4.87% | 10 |
| dev | CRWD | 5.14% | 11.18% | 5.14% | 11.18% | +0.00% | 10 |
| dev | ETHA | 19.44% | 4.84% | 10.70% | 7.12% | -8.74% | 8 |
| dev | IBIT | 13.04% | 6.48% | 13.04% | 6.48% | +0.00% | 8 |
| dev | ILMN | 25.75% | 7.24% | 25.75% | 7.24% | +0.00% | 9 |
| dev | IR | 1.07% | 9.97% | 1.07% | 9.97% | +0.00% | 6 |
| dev | PANW | 14.39% | 7.90% | 14.39% | 7.90% | +0.00% | 11 |
| dev | PTC | -2.89% | 12.17% | -2.89% | 12.17% | +0.00% | 14 |
| dev | PYPL | -2.05% | 10.12% | -2.98% | 10.12% | -0.93% | 7 |
| dev | TWLO | 38.80% | 7.69% | 36.76% | 7.69% | -2.04% | 9 |
| dev | VTRS | 6.13% | 8.06% | 6.13% | 8.06% | +0.00% | 9 |
| oos | AR | -4.07% | 8.03% | -4.07% | 8.03% | +0.00% | 9 |
| oos | CRDO | 16.11% | 8.23% | 21.61% | 7.84% | +5.51% | 13 |
| oos | CRWD | 56.09% | 6.60% | 56.09% | 6.60% | +0.00% | 11 |
| oos | ETHA | 1.44% | 12.83% | 0.82% | 13.36% | -0.62% | 8 |
| oos | IBIT | -13.64% | 16.91% | -8.53% | 12.00% | +5.11% | 7 |
| oos | ILMN | 29.44% | 5.13% | 25.97% | 4.84% | -3.47% | 9 |
| oos | IR | -0.92% | 10.49% | 9.07% | 5.32% | +9.99% | 8 |
| oos | PANW | 51.62% | 4.84% | 39.65% | 4.84% | **-11.97%** | 10 |
| oos | PTC | -2.36% | 18.26% | 4.11% | 12.84% | +6.48% | 6 |
| oos | PYPL | -1.48% | 16.84% | -1.39% | 16.77% | +0.09% | 8 |
| oos | TWLO | 52.70% | 7.15% | 52.70% | 7.15% | +0.00% | 13 |
| oos | VTRS | -0.84% | 12.57% | -0.84% | 12.57% | +0.00% | 12 |

## Results — variant (a′): symmetric (sells also gated by VPOC), N=30

24 series: 11 helped, 12 hurt, 1 flat, mean Δ **-0.29%**. Worst-case delta
-16.82% (oos/ILMN, 29.44% → 12.62%). **Worst-case absolute return regresses**
to -10.03% (oos/AR, vs. -4.07% baseline there). **Worst-case max drawdown
regresses** to 16.45% (dev/IR, vs. 9.97% baseline there — delaying IR's
death-cross sell while price sat below VPOC let a losing position ride
longer).

## Results — variant (c): VPOC as the slow line (dev window only, 12 series)

| VPOC window | Helped | Hurt | Mean Δ | Worst-case Δ | Worst-case abs. return | Worst-case max DD (own) |
|---|---|---|---|---|---|---|
| 20 bars | 7/12 | 5/12 | -3.59% | **-33.25%** (TWLO) | **-20.83%** (CRDO, vs. 10.66% baseline there) | **37.88%** (CRDO, vs. 12.54% baseline) |
| 30 bars | 6/12 | 6/12 | +2.24% | -18.10% (CRDO) | **-7.44%** (CRDO, vs. 10.66% baseline there) | **27.24%** (CRDO, vs. 12.54% baseline) |
| 50 bars | 3/12 | 9/12 | +0.61% | -11.14% (ETHA) | -5.90% (PYPL, vs. -2.05% baseline there) | **20.66%** (CRDO, vs. 12.54% baseline) |

Trade counts roughly double-to-triple at every window (e.g. CRDO: 10 trades
baseline → 36/25/19 at N=20/30/50) — a rolling VPOC is far noisier bar-to-bar
than a smooth 30-bar close SMA, so using it as the slow line turns a
trend-following crossover into something closer to a whipsaw-prone
mean-reversion signal.

## Reading this honestly

**The entry-only filter (a) doesn't clearly hurt the worst case on this test
bed, but it doesn't clearly help it either — there's no robust edge.** At
20 and 30 bars, the filter happens to repair the two worst baseline series
(oos/IBIT's -13.64% and oos/PTC's 18.26% drawdown both improve materially),
nudging worst-case return and worst-case drawdown slightly *better* than
baseline. That sounds promising in isolation, but: (1) roughly half the
series are completely unaffected (11-13 of 24 flat — the filter is inert
more often than it's active, same pattern the VWAP study found, because
price is often already above a 20-30 bar VPOC right when a bullish SMA
cross confirms), (2) the mean delta flips sign across windows (+0.05% at 20
bars, -0.36% at 30 bars, -0.04% at 50 bars) with helped/hurt counts close to
50/50 at every window, and (3) at 50 bars the worst single-series delta
(-17.87% on oos/PANW, a series that returned a strong +51.62% unfiltered)
shows the same wider-window failure mode the VWAP study and the 2026-09-26
SMA-window recheck both found: a laggier line filters out real trend
continuations along with the bad entries. This is noise around zero, not a
discovered edge — the specific worst-case improvement at N=20/30 is a
property of which two series happened to be this test bed's worst cases, not
evidence the filter systematically protects against bad entries.

**Gating exits by VPOC (a′) makes the true worst case worse**, exactly as
every prior exit-gating study has found (trailing-stop, profit-lock, and
VWAP's own a′): delaying IR's death-cross sell while price sat below its own
VPOC let a losing position ride further before the SMA sell it would
otherwise have taken (9.97% → 16.45% max drawdown), and AR's worst absolute
return more than doubled in the negative direction (-4.07% → -10.03%).

**Replacing SMA30 with VPOC outright (c) is the clearest rejection of the
three.** A rolling VPOC level is far choppier bar-to-bar than a 30-bar close
SMA (it jumps whenever the highest-volume bucket in the window changes, even
on a flat-price bar with an unusual volume spike), so using it as the slow
line roughly doubles-to-triples trade counts and produces the worst single
result in this entire study: CRDO's drawdown blows out from 12.54% to 37.88%
at N=20. Worst-case max drawdown is worse than baseline at every window
tested (20.66-37.88% vs. the dev-window baseline's 12.54%) — a severe,
consistent regression, not a cherry-picked one.

## Verdict

**Do not adopt VPOC in any of the three tested forms.** Across every
variant and every neighboring parameter value:
- Variant (a) (entry filter) is not harmful on this specific test bed's
  worst-case metrics, but shows no reproducible mean edge (sign flips across
  windows, ~50/50 helped/hurt, most series unaffected) — the improvement at
  N=20/30 is attributable to which two series were this bed's worst cases,
  not a systematic property of the filter. Adding a new indicator, a new
  tunable (bucket count), and real per-bar computation cost for an effect
  this small and inconsistent is not justified.
- Variant (a′) (symmetric/exit-gated) makes the true worst case worse on
  both worst-case return and worst-case max drawdown — rejected, consistent
  with every prior exit-gating study this project has run.
- Variant (c) (VPOC as slow line) makes worst-case max drawdown dramatically
  worse at every window tested — rejected outright.

No code, config, or CHANGELOG change follows from this. Reported plainly per
this project's standing practice for negative/neutral results.

## Scope and limits

- Crypto series (IBIT/ETHA) are equity ETF proxies, not real crypto history
  — same limitation as every other backtest in this directory (see README's
  "Crypto price history"). A true volume-profile measure is arguably even
  more sensitive to this proxy gap than VWAP was: real crypto trades 24/7
  with no session open/close, so its actual volume-at-price distribution
  could differ meaningfully from these proxies' regular-session-only volume.
  This was not and cannot currently be tested against real crypto history in
  this session.
- VPOC was computed from OHLCV bars only (20 equal-width buckets per
  window, each bar's volume spread uniformly across its own high-low range)
  — a necessary approximation given no tick-level volume-at-price data is
  available; a real volume-profile tool (using actual trade-level data)
  could behave differently. The 20-bucket resolution was fixed, not swept,
  to bound scope.
- Variant (c) was only run on the dev window (12 series), not the full
  24-series bed, given it already showed a severe, consistent regression on
  the smaller check — a wider run was not judged likely to change the
  verdict, but wasn't performed either.
- All runs use 100% cash-per-trade sizing (isolates signal quality), not the
  live 20%-of-portfolio cap, and model no transaction costs/slippage — same
  convention and same caveats as every prior `backtest.py`-based study in
  this directory.
