# Concurrent-positions cap re-check: 5 → 10? — 2026-09-26

Owner request: "Increase to 10 positions if the back testing supports
it." **Result: it doesn't — recommend leaving `max_concurrent_positions`
at 5.** Full data below.

## Method

Same mechanism as `backtest_2026-09-23.md`'s original concurrent-cap
sweep (`portfolio_backtest.py`, the multi-asset simulator that shares
one cash pool and runs the same production entry/exit code across
several bar-aligned series at once), but against a larger, more
diverse, more current test bed than that sweep had available: the 10
real `STOCK_WATCHLIST` names (`get_equity_historicals`, 2026-06-29 →
2026-09-26, 378 hourly bars) plus `IBIT`/`ETHA` as crypto-beta proxies
(no real crypto historicals source exists — same limitation as every
other crypto backtest this project has run). All 12 series verified
bar-aligned (identical 378 timestamps). Current production settings
throughout: `max_position_pct=0.20`, `max_aggregate_position_pct=0.60`,
`cooldown_bars=4`, `min_strength_pct=0`, `max_trades_per_day=3`.

## Result: the cap never binds above 5, at any setting

| Cap | Return | Max DD | Trades | Peak concurrent held |
|---|---|---|---|---|
| 3 | +0.15% | 8.66% | 68 | 3 |
| 4 | +5.59% | 7.24% | 77 | 4 |
| **5** | **+8.94%** | **7.65%** | 80 | 5 |
| 6 | +8.94% | 7.65% | 80 | 5 |
| 7 | +8.94% | 7.65% | 80 | 5 |
| 8 | +8.94% | 7.65% | 80 | 5 |
| 9 | +8.94% | 7.65% | 80 | 5 |
| **10** | **+8.94%** | **7.65%** | 80 | 5 |
| 12 (all) | +8.94% | 7.65% | 80 | 5 |

**Caps 5 through 12 are byte-for-byte identical.** The 60% aggregate
cap combined with 20%-per-position sizing already limits real
simultaneous exposure to a peak of 5 positions — the same "cap becomes
vestigial" mechanism `backtest_2026-09-23.md`'s later re-check found at
50% sizing, just landing at a different number here (5, not 2) because
sizing today (20%) sits between that test's 5% and 50%. **Raising
`max_concurrent_positions` to 10 would change nothing under the
current `RISK_LIMITS` - it's already non-binding at 5.**

## Checked the other direction too: does 10 help once the aggregate cap is ALSO relaxed?

Informational only (not proposing this change) - relaxed
`max_aggregate_pct` to 0.90 to see whether a higher concurrent-cap
would do anything, and whether it would help if it did:

| Cap | Return | Max DD | Trades | Peak concurrent held |
|---|---|---|---|---|
| 5 | **+10.55%** | **7.85%** | 87 | 5 |
| 10 | +6.93% | 9.12% | 102 | 8 |
| 12 | +6.93% | 9.12% | 102 | 8 |

Even with room to open more positions, **cap=10 lets peak concurrency
reach 8 and that's worse on both return and drawdown** than staying at
5 - confirms the original 2026-09-23 finding again, on a fresh, larger,
more diverse dataset: correlated assets firing near-duplicate signals
concentrate risk rather than diversifying it, so more concurrent
positions costs more than it protects here, same as it did in the
original 2-asset and 4-asset test groups.

## Recommendation

**No change.** `RISK_LIMITS["max_concurrent_positions"]` stays at 5 -
not because 10 is unsafe in some new way, but because the backtest the
owner asked for doesn't support it: it's already non-binding at the
current sizing, and even in the scenario where it would bind (a looser
aggregate cap), more concurrency underperforms. If more simultaneous
exposure is wanted, the actual lever is `max_aggregate_position_pct`
and/or `max_position_pct` (position sizing), not the raw concurrency
count - and per the second table above, loosening those doesn't clearly
help either.

`config.py` unchanged. 215/215 tests still passing (no test asserted a
concurrent-cap value that would change).
