# 15-Minute Opening Range Breakout (ORB) for VOLTRAP — evaluation (2026-09-27, FINAL)

Requested via the ORB evaluation brief posted to `#voltrap-agents-work`
(2026-09-26 23:55, attributed to ChatGPT/Codex). Full baseline rules as
specified there, implemented exactly (see "Baseline rules implemented"
below).

**Final verdict: reject.** The interim pass below (Robinhood-only, ~3
months, one regime) found the baseline roughly breakeven-to-marginally-
positive. The multi-regime re-run against Codex's real, multi-year
Alpaca data (see "Multi-regime re-run" further down — 4-10 years per
symbol, genuine trending/sideways/volatile coverage) reverses that:
worst-case-first, the baseline is a **net loser** (avg R -0.027,
profit factor 0.90 on the weaker of the two chronological splits), not
merely a non-edge. Combined with the structural fit problems below, this
closes the evaluation with a clear reject - not adopted, not paper-tested.

## Current-system fit (structural, independent of backtest results)

Read fresh this task: `trading_agent/config.py` lines 118-171 and
`trading_agent/PLAYBOOK.md`'s full "VOLTRAP" section.

1. **Cadence mismatch.** VOLTRAP runs weekly (Monday entry + daily
   near-close monitor for assignment/expiration). ORB is an intraday,
   same-day 09:30-11:00 ET pattern. There is no existing intraday
   monitoring loop for VOLTRAP to hang an ORB signal on — it would need
   its own new intraday Routine, not a hook into the existing weekly one.
2. **No dollar-risk-per-trade concept.** The brief's sizing formula
   (`floor(risk_budget / stop_distance)`) assumes a per-trade dollar risk
   budget. VOLTRAP's entire risk model is `VOLTRAP_RISK_LIMITS["max_voltrap_pct"]`
   — percent-of-portfolio **options collateral**, not a per-trade equity
   risk figure. There is no field to plug ORB's sizing into without new
   design work (a new, separate budget, same pattern as `WHEEL_RISK_LIMITS`
   in the standing plan for the options-wheel strategy).
3. **Options profitability != stock profitability**, per the brief's own
   caution. VOLTRAP trades premium (CSPs/covered calls), not shares. Even
   a profitable ORB stock signal would need to be reinterpreted as a
   *context signal* (e.g., "don't sell a CSP into a confirmed bearish ORB
   session") rather than a direct share-trading module, since VOLTRAP
   doesn't buy/sell the underlying directly today.
4. **Not live yet regardless.** VOLTRAP is unfunded for real trading
   (~$82 free cash vs. ~$1000+ needed per contract), so nothing here
   changes anything executable in the near term either way.

Net: ORB does not bolt onto VOLTRAP as-is. At best it could inform a new,
separate "avoid selling premium into a strong intraday breakout against
your position" context filter — a materially smaller, different scope
than a standalone ORB trading module.

## Data used (interim pass)

Real (non-`interpolated`), 5-minute, regular-hours bars via
`get_equity_historicals`, all 8 current `VOLTRAP_WATCHLIST` symbols
(`SMCI, MARA, OKLO, CLSK, RGTI, ASST, NVDL, SEDG` — reconfirmed current in
`config.py` before running this): 2026-07-01 to 2026-09-25 (~3 months,
one regime). Split for a rough dev/OOS check: **dev = July**, **OOS =
August-September**.

**Data-gap finding**: Robinhood's pre-listing history for these symbols
is synthetic placeholder data, not real prices — every bar returned for a
narrow window explicitly probed in 2018 (SMCI, `interval=5minute`) had
`interpolated: true` with a flat price and zero volume. `get_equity_historicals`
also hard-caps `interval=5minute` requests at ~5000 bars (~3 months) per
call. Both together mean Robinhood alone cannot support genuine
multi-regime intraday validation for these names — this is exactly why
Codex's Alpaca connector was tasked with a deeper fetch.

## Baseline rules implemented (exact, per the brief)

- Opening range: 09:30:00-09:45:00 ET, 3 x 5-min bars, wicks included.
- Confirmation: first completed 5-min bar after the range whose **close**
  is strictly beyond the range high (long) / low (short).
- Entry: next bar's **open** after the confirmation bar (never the
  confirmation bar itself).
- Entry window: 09:50-10:30 ET inclusive; at most one trade per symbol
  per session.
- Stop: opposite edge of the opening range. Target: 2R from actual entry.
- Time exit: force-close at 11:00 ET.
- Invalid/skip: wrong-side stop, zero-width range, missing required bars,
  or a computed size of 0 shares.
- Same-bar stop-and-target ambiguity: resolved **stop-first** (worst-case,
  this project's standing convention).
- Sizing: **no real VOLTRAP dollar-risk-budget field exists** (see above),
  so a nominal fixed $500 risk-budget proxy was used purely to compute
  R-multiples/expectancy — explicitly a modeling stand-in, not a real
  parameter.
- Costs: a flat 5bps round-trip slippage estimate (half on entry, half on
  exit) — a stated assumption, not a measured one; no commission
  (Robinhood is commission-free on equities).
- Variants (retest, VWAP, trend filter, relative volume, range-size
  filter, news exclusion) were **not** tested this pass — baseline first,
  per the brief ("do not assume added filters improve performance").

## Results, interim pass (dev = July, OOS = Aug-Sep, all 8 symbols)

| Symbol | Period | Trades | No-trade days | Win% | Avg R | PF | Total P&L | Max DD |
|---|---|---|---|---|---|---|---|---|
| SMCI | dev | 18 | 4 | 44.4% | 0.01 | 1.04 | $81.91 | -$1118.65 |
| SMCI | oos | 27 | 12 | 51.9% | 0.05 | 1.26 | $640.88 | -$1053.80 |
| MARA | dev | 16 | 6 | 68.8% | 0.32 | 4.76 | $2576.96 | -$379.30 |
| MARA | oos | 27 | 12 | 48.1% | 0.05 | 1.27 | $737.64 | -$1041.80 |
| OKLO | dev | 16 | 6 | 56.2% | -0.00 | 0.98 | -$30.61 | -$754.62 |
| OKLO | oos | 25 | 14 | 48.0% | 0.08 | 1.41 | $1023.90 | -$1472.49 |
| CLSK | dev | 16 | 6 | 50.0% | 0.02 | 1.16 | $195.49 | -$956.86 |
| CLSK | oos | 28 | 11 | 57.1% | 0.05 | 1.19 | $680.71 | -$1318.24 |
| RGTI | dev | 18 | 4 | 38.9% | -0.13 | 0.57 | -$1136.84 | -$1998.87 |
| RGTI | oos | 22 | 17 | 45.5% | -0.04 | 0.84 | -$409.07 | -$1113.69 |
| ASST | dev | 18 | 4 | 38.9% | -0.23 | 0.30 | -$2032.02 | -$2299.63 |
| ASST | oos | 28 | 11 | 39.3% | 0.04 | 1.18 | $498.18 | -$1164.46 |
| NVDL | dev | 19 | 3 | 42.1% | -0.11 | 0.54 | -$1008.83 | -$1095.55 |
| NVDL | oos | 31 | 8 | 51.6% | 0.02 | 1.12 | $372.15 | -$1181.10 |
| SEDG | dev | 15 | 7 | 60.0% | 0.21 | 2.42 | $1545.90 | -$508.09 |
| SEDG | oos | 28 | 11 | 46.4% | -0.05 | 0.80 | -$762.30 | -$2652.33 |

**Combined (all 8 symbols):**
- **Dev (July):** 136 trades, 40 no-trade days, win rate 49.3%, avg R
  0.00, profit factor 1.01, total P&L +$191.96, max drawdown -$3599.93.
- **OOS (Aug-Sep):** 216 trades, 96 no-trade days, win rate 48.6%, avg R
  +0.03, profit factor 1.12, total P&L +$2782.10, max drawdown -$5680.27.

**Key mechanical finding**: exits are overwhelmingly the 11:00 ET
**time exit**, not the designed stop/target — 125/136 dev trades and
196/216 OOS trades closed on time exit; only 11 dev / 15 OOS hit the
stop, and the 2R target was hit **0 times in dev and only 5 times in
OOS**, out of 352 total trades. The opening-range-derived stop distance
is wide enough, and the 09:50-11:00 window short enough, that this exact
baseline rarely lets its own designed risk:reward play out — most trades
are effectively a bet on wherever price sits at 11:00 relative to entry,
not on the 2R breakout thesis the rules describe.

Per-symbol results are noisy and don't hold direction between the two
splits (RGTI negative both halves; ASST negative dev/positive OOS; SEDG
positive dev/negative OOS) — consistent with 3 months of single-regime
data being too thin to trust individual-symbol edges either way.

## Worst-case-first read, interim pass

Dev, the weaker split, is roughly breakeven (avg R ≈ 0.00, PF 1.01) —
not a demonstrated edge. OOS is modestly positive (avg R +0.03, PF 1.12)
but on a profit factor that thin, realistic costs (real bid/ask spread
on lower-liquidity names like RGTI/ASST, actual commission-free-but-wider
effective spread) could plausibly erase it. Treating the weaker result as
binding (this project's standing rule), **the evidence so far does not
show a real edge** — it's statistically consistent with noise around
zero, same conclusion pattern as the trailing-stop/profit-lock/RSI ideas
rejected earlier this project. (Reversed and superseded by the
multi-regime re-run below — noted here as the record of what the thin
data suggested first, per this project's practice of not silently
replacing an earlier finding.)

## Multi-regime re-run (2026-09-27, later same day)

Codex's ORB data handoff (`codex/orb-alpaca-data`) landed as a git bundle
via Slack (GitHub branch writes were blocked on Codex's end; the owner
downloaded and attached the bundle directly). Independently verified
before use — row counts, SHA-256 hashes, timestamp integrity, and OHLCV
bounds checked across all 956,660 rows, full test suite 215/215 passed —
see `docs/handoffs/orb-alpaca-data.review-claude.md` on
`claude/review-orb-alpaca-data` for the full review (no findings).
Merged into this branch (`research_agent/data/orb_5min/*.csv`).

**Real coverage per symbol** (vs. the interim pass's single 3-month
window): SMCI and SEDG back to 2016 (~10.7 years), MARA to 2017 (~9
years), CLSK to 2020, RGTI/OKLO to 2021, NVDL to 2022, ASST (newest
listing) to 2023 (~3.7 years) - all through 2026-09-25. This spans
multiple real bull/bear/chop cycles per symbol, not one narrow window,
satisfying the brief's "trending, sideways, and volatile markets"
requirement in a way the interim pass explicitly could not.

**One bug fixed vs. the interim script**: that script hardcoded a UTC-4
(EDT) offset for the 09:30/09:45/10:30/11:00 ET session boundaries, which
happened to be correct for its single July-September window but is wrong
for roughly half the year (EST, UTC-5). This re-run converts every bar's
UTC timestamp to real `America/New_York` local time via `zoneinfo` before
applying any session-time rule, so daylight-saving transitions across
years are handled correctly. Same exact baseline rules and cost/sizing
assumptions otherwise (opening range, confirmation, entry window, 2R
target, opposite-edge stop, 11:00 ET time exit, stop-first same-bar
tiebreak, $500 nominal risk-budget proxy, 5bps round-trip slippage).

**Split**: chronological, per symbol - first half of each symbol's real
history is dev, second half is out-of-sample, since each symbol's history
starts on a different real date.

| Symbol | Period | Date range | Trades | No-trade days | Win% | Avg R | PF | Total P&L | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| SMCI | dev | 2016-01-04..2022-01-19 | 689 | 275 | 42.7% | -0.048 | 0.84 | -$16,526.64 | -$23,241.20 |
| SMCI | oos | 2022-01-20..2026-09-25 | 886 | 271 | 48.1% | -0.002 | 0.99 | -$796.02 | -$9,723.47 |
| MARA | dev | 2017-10-30..2022-04-08 | 628 | 323 | 43.3% | -0.023 | 0.92 | -$7,161.55 | -$14,022.38 |
| MARA | oos | 2022-04-11..2026-09-25 | 882 | 237 | 45.0% | -0.028 | 0.90 | -$12,315.65 | -$19,935.98 |
| OKLO | dev | 2021-07-08..2024-03-07 | 19 | 38 | 31.6% | -0.282 | 0.17 | -$2,679.74 | -$2,770.78 |
| OKLO | oos | 2024-03-08..2026-09-25 | 470 | 159 | 48.1% | 0.043 | 1.20 | $10,073.44 | -$2,940.86 |
| CLSK | dev | 2020-01-24..2023-05-22 | 613 | 182 | 48.1% | -0.009 | 0.97 | -$2,702.66 | -$11,693.60 |
| CLSK | oos | 2023-05-23..2026-09-25 | 648 | 189 | 46.9% | -0.019 | 0.93 | -$6,148.09 | -$12,400.09 |
| RGTI | dev | 2021-04-22..2024-01-22 | 377 | 180 | 46.7% | -0.011 | 0.96 | -$2,036.17 | -$7,056.17 |
| RGTI | oos | 2024-01-23..2026-09-25 | 500 | 172 | 49.8% | 0.016 | 1.07 | $3,944.78 | -$3,843.00 |
| ASST | dev | 2023-02-03..2024-11-26 | 128 | 68 | 50.0% | 0.084 | 1.26 | $5,364.23 | -$3,450.85 |
| ASST | oos | 2024-11-27..2026-09-25 | 310 | 125 | 45.5% | 0.015 | 1.07 | $2,333.03 | -$6,193.17 |
| NVDL | dev | 2022-12-13..2024-11-01 | 331 | 90 | 48.6% | -0.012 | 0.95 | -$1,989.61 | -$6,533.83 |
| NVDL | oos | 2024-11-04..2026-09-25 | 363 | 111 | 48.5% | -0.019 | 0.92 | -$3,496.91 | -$5,132.28 |
| SEDG | dev | 2016-01-04..2021-05-12 | 927 | 413 | 46.4% | -0.050 | 0.81 | -$23,147.72 | -$24,621.31 |
| SEDG | oos | 2021-05-13..2026-09-25 | 1,003 | 346 | 45.9% | -0.036 | 0.86 | -$17,826.42 | -$20,866.23 |

**Combined (all 8 symbols):**
- **Dev:** 3,712 trades, 1,569 no-trade days, win rate 45.7%, avg R
  **-0.027**, profit factor **0.90**, total P&L -$50,879.87, max drawdown
  -$61,435.90.
- **OOS:** 5,062 trades, 1,610 no-trade days, win rate 47.0%, avg R
  -0.010, profit factor 0.96, total P&L -$24,231.84, max drawdown
  -$55,212.64.

**The time-exit finding holds up at scale**: 3,087/3,712 dev trades
(83%) and 4,415/5,062 OOS trades (87%) closed on the 11:00 ET time exit;
the 2R target was hit only 116 dev / 93 OOS times out of 8,774 total
trades (~2.4%). This is the same mechanical pattern the interim pass
found on 352 trades, now confirmed on a dataset 25x larger, across real
multi-year regimes: this specific baseline (opening-range-width stop,
09:50-11:00 window) essentially never lets its designed 2R thesis play
out - most trades are a bet on the 11:00 price relative to entry, not a
breakout continuation trade.

**Per-symbol consistency**: 6 of 8 symbols are negative in avg R on
*both* chronological halves (SMCI, MARA, CLSK, RGTI-dev/NVDL, SEDG - RGTI
and OKLO turn slightly positive only in their second, more recent half).
Only ASST is positive on both halves, and it has the shortest real
history (3.7 years) and smallest sample (438 trades total) of the eight -
the least reliable single data point here, not the strongest.
OKLO-dev's -0.282 avg R comes from only 19 trades and is too thin to
trust either way; excluding it from the combined dev figure would still
leave the other 7 symbols' combined dev result solidly negative.

## Worst-case-first read, final

Both chronological splits are net negative (avg R -0.027 dev / -0.010
OOS, profit factor 0.90 / 0.96) - a stronger and more consistent result
than the interim pass's noise-around-zero finding, in the opposite
direction. Treating the weaker split as binding, this baseline **loses
money** before even accounting for real bid/ask spread (the $500
nominal-risk sizing and 5bps slippage assumption are the only cost model
applied; real spread on names like OKLO/RGTI/ASST at various points in
their history would very likely widen this further, not narrow it).

## Deliverable

- **Current-system fit**: poor structural fit as a standalone module —
  cadence mismatch (weekly vs. intraday), no dollar-risk-budget field to
  size into, and options ≠ stock profitability (see "Current-system fit"
  above). At best a future context-signal role, not a trading module -
  and even that role would need its own positive-edge signal, which this
  baseline does not provide.
- **Data gaps**: closed. Real multi-year (3.7-10.7 years per symbol),
  multi-regime data now used throughout, reviewed and verified (see
  `docs/handoffs/orb-alpaca-data.review-claude.md`).
- **Test results**: baseline-only (the six variants were never reached -
  the brief's own baseline fails worst-case-first, and testing variants
  on top of a losing baseline without a specific reason to expect
  reversal would be exactly the "assume added filters improve
  performance" the brief warns against).
- **Recommendation (final): reject.** Both the structural fit and the
  multi-regime evidence say no. Nothing was implemented in
  `trading_agent/` at any point in this evaluation — no code shipped, no
  config touched, matching the brief's "disabled by default" instruction
  by the simplest possible means.
- **Status**: closed. Re-open only with a materially different baseline
  design (a different entry trigger, stop, or target scheme) and new
  evidence - not a re-run of these exact rules on the same data.
- **Raw data removed** (owner request, same day): the 48MB of
  `research_agent/data/orb_5min/*.csv` was deleted after this verdict -
  a one-off dataset for a rejected experiment, tied to the current
  `VOLTRAP_WATCHLIST` (which is itself periodically revised), isn't worth
  the repo weight with no approved follow-on use. Everything substantive
  (coverage, hashes, per-symbol results) is preserved above and in
  `docs/handoffs/orb-alpaca-data.review-claude.md`; re-fetching from
  Alpaca would be needed if this exact data is wanted again.
