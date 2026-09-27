# 15-Minute Opening Range Breakout (ORB) for VOLTRAP — evaluation (2026-09-27, INTERIM)

Requested via the ORB evaluation brief posted to `#voltrap-agents-work`
(2026-09-26 23:55, attributed to ChatGPT/Codex). Full baseline rules as
specified there, implemented exactly (see "Baseline rules implemented"
below). This document is **interim**: the brief requires chronological
development + out-of-sample validation "across trending, sideways, and
volatile markets," and right now the only real intraday data available is
~3 months from Robinhood, one regime, no crash/chop/trend variety. A
second pass is planned once Codex's Alpaca-sourced multi-regime 5-minute
dataset lands (`codex/orb-alpaca-data`, handoff in progress as of this
writing). **Do not treat the adopt/paper-test/reject call below as final.**

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

## Data used (this interim pass)

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

## Results (dev = July, OOS = Aug-Sep, all 8 symbols)

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

## Worst-case-first read

Dev, the weaker split, is roughly breakeven (avg R ≈ 0.00, PF 1.01) —
not a demonstrated edge. OOS is modestly positive (avg R +0.03, PF 1.12)
but on a profit factor that thin, realistic costs (real bid/ask spread
on lower-liquidity names like RGTI/ASST, actual commission-free-but-wider
effective spread) could plausibly erase it. Treating the weaker result as
binding (this project's standing rule), **the evidence so far does not
show a real edge** — it's statistically consistent with noise around
zero, same conclusion pattern as the trailing-stop/profit-lock/RSI ideas
rejected earlier this project.

## Deliverable

- **Current-system fit**: poor structural fit as a standalone module —
  cadence mismatch (weekly vs. intraday), no dollar-risk-budget field to
  size into, and options ≠ stock profitability (see above). At best a
  future context-signal role, not a trading module, and that's a
  materially different, smaller scope than what was evaluated here.
- **Data gaps**: Robinhood-only data covers 3 months, 1 regime; no
  trending/sideways/volatile split as the brief requires. Deeper data is
  in progress via Codex's Alpaca connector (`codex/orb-alpaca-data`).
- **Test results**: baseline-only (no variants tested yet). Combined
  worst-case-first result is breakeven-to-marginally-positive (avg R
  0.00 to +0.03, PF 1.01-1.12), driven almost entirely by time-exits
  rather than the designed stop/target mechanics.
- **Recommendation (interim): reject for now / do not implement.**
  Neither the structural fit nor the evidence supports building this as
  a live or even paper-tested module today. Nothing is implemented in
  `trading_agent/` — no code shipped, no config touched, matching the
  brief's "disabled by default" instruction by the simplest possible
  means (not building it yet).
- **Next step**: once Codex's multi-regime Alpaca dataset lands, re-run
  this same baseline (and, only if baseline clears worst-case-first,
  the six variants) across real trending/sideways/volatile windows
  before any different conclusion is drawn. This document will be
  updated or superseded at that point, not silently replaced.
