# "Awesome trade" threshold sweep — keep 5%, do not lower

**Goal impact: none recommended — `RISK_LIMITS["awesome_trade_min_crossover_pct"]`
stays at 5.0. `config.py` is unchanged.**

## What was asked

After the 11:12 UTC cycle blocked HBAR (crossover_pct 0.40%) and XLM
(crossover_pct 0.50%) on the aggregate-exposure cap, the owner asked to
allow such trades when they show a "strong buy," then asked for a backtest
before changing anything. This project already has a mechanism for exactly
that: a `fresh_buy_cross` whose `crossover_pct` clears
`RISK_LIMITS["awesome_trade_min_crossover_pct"]` (currently 5.0%, the same
bar `scanner_signals.EXCELLENT_CROSSOVER_PCT` uses for `excellent_watch`)
may size against `awesome_trade_aggregate_pct` (100%) instead of the normal
`max_aggregate_position_pct` (60%) — added 2026-09-25, see
`backtest_2026-09-25_aggregate_cap.md`. That study found the override
**never fired at all** across its ~4-year combined sample with the
watchlist composition of the time. This is a fresh test of whether
*lowering* the 5% bar — i.e., loosening what counts as "strong" — helps,
using the current watchlist and `portfolio_backtest.py` directly (the same
production module, unmodified, that study used).

## What was tested

`RISK_LIMITS["awesome_trade_min_crossover_pct"]` swept at **5.0 (current),
4.0, 3.0, 2.0, 1.0**, plus a **`None` control** (override infrastructure
disabled entirely — the pre-2026-09-25 behavior), with
`awesome_trade_aggregate_pct` held fixed at the current production value
(1.00) whenever the override is enabled. Every other parameter held at
current production values: `max_position_pct=0.20`,
`max_concurrent_positions=5`, `max_aggregate_position_pct=0.60`,
`max_trades_per_day=4`, `min_strength_pct=0`, `cooldown_bars=4`, current
stop-loss/take-profit (4%/8% selling 70%), `min_sell_profit_pct=0.0`
(profit gate), no gate-floor time limit — all imported directly from
`exit_criteria.py`/`profit_gate.py`/`config.py`, not hardcoded.

**Four independent real-history windows**, per this project's
worst-case-first, don't-trust-one-window standard:
- **`hourly_dev`** / **`hourly_oos`**: the same two ~90-day hourly windows
  used in today's VPOC study (`backtest_2026-10-02_vpoc_evaluation.md`) —
  2026-07-06 to 2026-10-01 and 2026-04-06 to 2026-07-02.
- **`daily_regime1`** / **`daily_regime2`**: ~4 years of daily history was
  requested, but **ETHA's real trading history only starts 2024-07-23**
  (IBIT's starts 2024-01-11) — Robinhood backfills everything before an
  ETF's actual launch with a flat, zero-volume `interpolated: true`
  placeholder, which would silently corrupt any backtest that didn't check
  for it. All 12 series were truncated to their common real-data start
  (2024-07-23) and the resulting ~551-day span was split into two
  roughly-equal regimes (2024-07-23 to 2025-08-26, and 2025-08-27 to
  2026-10-01) — shorter than the prior study's 3.7-year span, but real data
  throughout, with no interpolated placeholder bars included.
- All 12 series: current `STOCK_WATCHLIST` (CRWD, PANW, TWLO, ILMN, IR,
  PTC, CRDO, VTRS, AR, PYPL) plus IBIT/ETHA crypto proxies (crypto still
  has no historicals source — no crypto history fabricated).
- `daily_full` (the two daily regimes combined) is reported for reference
  only, same convention as the original study — it is not independent of
  `daily_regime1`/`2` and is excluded from the worst-case ranking below.

## Results

| Window | thr=None | thr=5.0 (current) | thr=4.0 | thr=3.0 | thr=2.0 | thr=1.0 |
|---|---|---|---|---|---|---|
| daily_full (ref.) | +23.35% / 11.01dd | +31.92% / 10.52dd | +33.10% / 10.53dd | +31.37% / 10.53dd | +29.83% / 11.58dd | +42.21% / 11.67dd |
| daily_regime1 | +16.14% / 6.37dd | +23.49% / 6.57dd | +24.33% / 6.57dd | +24.33% / 6.57dd | +24.33% / 6.57dd | +35.72% / 6.83dd |
| daily_regime2 | +6.81% / 10.08dd | +6.78% / 10.11dd | +6.78% / 10.11dd | +7.63% / 10.11dd | +6.55% / **11.01dd** | +7.88% / **11.07dd** |
| hourly_dev | +4.24% / 6.14dd | +4.24% / 6.14dd | +4.24% / 6.14dd | +4.24% / 6.14dd | +4.24% / 6.14dd | **+1.00%** / 6.34dd |
| hourly_oos | +13.94% / 4.10dd | +13.94% / 4.10dd | +13.94% / 4.10dd | +13.94% / 4.10dd | +13.93% / 4.11dd | +18.06% / 4.11dd |

**Worst-case across the 4 independent windows (daily_regime1/2 +
hourly_dev/oos), per threshold:**

| Threshold | Worst-case return | Worst-case max DD | Mean return (4 windows) |
|---|---|---|---|
| None (no override) | +4.24% (hourly_dev) | 10.08% (regime2) | +10.28% |
| **5.0 (current)** | **+4.24%** (hourly_dev) | **10.11%** (regime2) | +12.11% |
| 4.0 | +4.24% (hourly_dev) | 10.11% (regime2) | +12.32% |
| 3.0 | +4.24% (hourly_dev) | 10.11% (regime2) | +12.53% |
| 2.0 | +4.24% (hourly_dev) | **11.01%** (regime2) | +12.26% |
| 1.0 | **+1.00%** (hourly_dev) | **11.07%** (regime2) | **+15.67%** (best mean) |

## Reading this honestly

**Unlike the original 2026-09-25 study, the override is not fully dormant
with the current watchlist** — `daily_regime1` shows one extra/differently
sized buy at the current 5% threshold versus the `None` control (28 buys →
29), and several other windows show small return deltas even at 5.0. The
watchlist has changed twice since that study (CHKP/HUBS → CRDO/PYPL,
MAIR → VTRS), and the new names apparently do occasionally throw a 5%+
crossover while the aggregate budget is already tight. The effect at the
current 5% setting is still small and not a worst-case regression (worst
return and worst drawdown both move by ≤0.03 percentage points versus no
override at all) — "cheap, tested insurance for the rare case it applies"
remains an accurate description.

**3-4% ties the current worst case exactly while nudging mean return up a
little** (+12.11% → +12.32-12.53% across the 4 windows) — a small, genuine,
not-obviously-harmful loosening on this test bed. This is the most
defensible change if the goal were purely "let slightly-less-extreme strong
signals through."

**2% is where it turns bad, and 1% is a clear rejection.** At 2%,
`daily_regime2`'s worst-case drawdown jumps from 10.11% to 11.01% for a
*worse* mean return in that window (6.55% vs 6.78%) — no benefit for the
added risk. At 1%, the pattern is unambiguous: worst-case return drops from
+4.24% to **+1.00%** (`hourly_dev`) and worst-case drawdown rises from
10.11% to **11.07%** (`daily_regime2`), even though 1% has the *best* mean
return of every threshold tested (+15.67%). This is the same
better-mean-worse-worst-case tradeoff this project has rejected every time
it's come up (trailing-stop, profit-lock, VWAP, VPOC) — a looser "strong"
bar lets in more marginal signals, and more of them means more exposure to
the specific sequencing/cascade risk described below, not a free lunch.

**The regression isn't one bad trade — it's a sequencing cascade.**
Inspecting `hourly_dev`'s trade list at 1% vs. 5% directly: lowering the
threshold doesn't just add a few new "awesome" buys, it changes the *size*
of several early entries (e.g. CRDO's first buy: 0.0515 units at 5% vs.
0.0467 at 1%), which changes how much shared cash and aggregate budget is
available for the *next* signal in a multi-asset shared-cash-pool
simulation, which cascades into a materially different set of later trades
entirely (9 buys present only at 5.0, a different 9 present only at 1.0,
out of ~31 total buys). There is no single clean "this trade caused it" — a
lower bar reshuffles the whole sequence, and in this window that
reshuffling happened to land on a worse outcome. This is a structural
property of sizing against a shared, finite budget, not a fluke specific to
one asset.

**Practically, none of this would have unblocked today's HBAR/XLM
signals regardless.** HBAR's crossover_pct was 0.40%, XLM's was 0.50% — both
are 2-12x below even the most aggressive threshold tested here (1%), let
alone the defensible 3-4% range. There is no backtest-supported version of
the "awesome trade" override, at any threshold worth adopting, that would
have classified either signal as "strong." The original block was correct.

## Verdict

**Keep `awesome_trade_min_crossover_pct` at 5.0.** The current setting is
not a worst-case regression and remains appropriately rare. Lowering to
3-4% is defensible on this test bed (ties the worst case, small mean
upside) but the improvement is marginal and not worth a config change on
its own; lowering to 1-2% is rejected outright (worse worst-case return
and/or drawdown). No code or config change follows from this. Reported
plainly per this project's standing practice.

## Scope and limits

- Crypto series (IBIT/ETHA) are equity ETF proxies, not real crypto history
  — same limitation as every other backtest in this directory.
- The daily test bed is ~2.25 years (2024-07-23 to 2026-10-01), shorter
  than the original study's 3.7 years, because ETHA's real trading history
  doesn't go back further — extending it would require either dropping
  ETHA from the daily test bed (changing the asset mix mid-study) or
  accepting the interpolated placeholder data the original study's own
  window may have silently included without checking for it.
- This only tested the entry-side `awesome_trade_min_crossover_pct` bar.
  `awesome_trade_aggregate_pct` (currently 100%) was held fixed throughout,
  not swept — the original study found no evidence it needed revisiting,
  and this backtest gave no new reason to either.
- Position sizing uses the full shared-cash-pool, multi-asset
  `portfolio_backtest.py` mechanics (not `backtest.py`'s single-asset,
  100%-cash-per-trade convention) since the override's effect is inherently
  about shared aggregate budget — same convention as the original
  2026-09-25 study. No transaction costs or slippage modeled, same
  unaddressed limitation as every prior study in this directory.
