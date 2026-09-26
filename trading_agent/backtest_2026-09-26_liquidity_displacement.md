# Liquidity displacement / sweep gate — tested, NOT adopted

**Goal impact: none — a proposed entry filter that backtest evidence
ruled out before it touched live behavior.**

## What was asked

Owner asked about "liquidity displacement" (an ICT / Smart Money
Concepts retail-trading term — a fast-moving "displacement" candle,
often following a "liquidity sweep" through a recent swing high/low)
and whether any piece of it could improve the current SMA-crossover
strategy.

## Why this needed a real test, not just an opinion

"Liquidity displacement" has no standard quantitative definition in
academic or quant literature — it's practitioner terminology from
trading-education content, not a parameterized model. Rather than
dismiss it on vibes or adopt it on vibes, it was operationalized into a
concrete, testable rule and backtested against the same real data this
project already uses for every other parameter decision.

**Operationalized definition:**
- **Sweep** at bar *j*: `low[j] < min(low[j-lookback:j])` (price
  undercuts the recent swing low) **and** `close[j] > that same prior
  low` (closes back above it — a false breakdown, not a real one).
- **Displacement** at bar *j*: `close[j] - open[j] > displacement_mult
  × avg(|close-open|` over the same lookback window) — an unusually
  large bullish body.
- **Gate confirmed** at entry bar *i*: a sweep+displacement bar
  occurred within `confirm_window` bars before *i*.

Applied only as an additional **entry** gate on top of the existing
production buy logic (`entry_filter.confirmed_signal`, cooldown,
volume filter) — same shape as the already-live `rsi_filter.py` /
`volume_filter.py` gates. Exits (stop-loss/take-profit) were untouched.

## Test setup

Same 12-series test bed used for every other recheck this session: all
10 `STOCK_WATCHLIST` names (real `get_equity_historicals`, 90-day
hourly) + `IBIT`/`ETHA` crypto proxies (crypto still has no real
historicals source). Compared production defaults (min_strength_pct=0,
cooldown=4 bars, volume_min_ratio=1.0, current stop-loss/take-profit)
with vs. without the gate, using the real `exit_criteria.check_exit`
and `entry_filter.confirmed_signal` code paths for both variants.

Swept the gate's own parameters (lookback 10–20, displacement_mult
1.0–1.5, confirm_window 3–30 bars) to rule out one unlucky
parameterization before concluding anything:

| confirm_window | lookback | mult | buy entries (base→gated) | helped | hurt | mean Δ | worst Δ | best Δ |
|---|---|---|---|---|---|---|---|---|
| 3 | 20 | 1.5 | 38 → 0 | 0 | 0 | n/a | n/a | n/a |
| 15 | 10 | 1.2 | 38 → 7 | 5 | 7 | -6.13pp | -36.11pp | +7.04pp |
| 20 | 10 | 1.0 | 38 → 10 | 5 | 7 | -4.11pp | -23.52pp | +7.04pp |
| 30 | 10 | 1.0 | 38 → 19 | 5 | 7 | -4.16pp | -24.10pp | +4.71pp |
| 20 | 20 | 1.0 | 38 → 5 | 5 | 7 | -3.63pp | -21.05pp | +10.05pp |

## Result: no, don't adopt

**Every parameterization tested hurt more than it helped**, same 5
helped / 7 hurt split each time, mean return delta negative in all five
variants (-3.6pp to -6.1pp), worst case a real -21 to -36 percentage
points. At the tightest, most literal reading of the ICT definition
(sweep+displacement required within 3 bars of the SMA-crossover
confirmation), the gate rejected **100% of buy entries across all 12
series** — the two signals operate on fundamentally different
timeframes (a displacement candle is an immediate, fast reaction; the
SMA(10,30) crossover is a lagging confirmation that typically doesn't
fire until well after any triggering move has already happened), so
requiring them to coincide closely is close to mutually exclusive by
construction, not a real filter.

Loosening the window let some real entries back in, but the gate
consistently cut good, profitable trades that had no detectable sweep
pattern behind them (CRDO's +36.11% and IBIT's +21.05% baseline
round-trips were among the biggest losses when gated out) without a
compensating set of avoided losers large enough to offset it.

**Not adopted.** No config changes, no new files wired into
`run_cycle.py`/`PLAYBOOK.md` — this stays a documented, tested,
rejected idea, same treatment as the trailing-stop and profit-lock
findings. `WATCHLIST`/`STOCK_WATCHLIST`/`RISK_LIMITS` unchanged.
