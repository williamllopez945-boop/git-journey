# 24h gate floor removed (2026-09-29)

Owner requested removing `profit_gate.py`'s 24h gate-floor time backstop
(adopted 2026-09-28), after a review of the signal-driven sell path.
Backtested first, per COLLABORATION.md.

## Method

Same fresh data as today's walk-forward re-run (12 symbols incl.
`VTRS`, 1149-bar real aligned window, 4 folds), production settings
otherwise (SMA(10,30), 4% SL, 8% TP/70% partial, gate 0% breakeven,
`fee_pct=0.001`). Compared `gate_max_hold_bars=24` (current) against
`None` (floor removed, gate can hold indefinitely), both isolated and
portfolio-level.

## Result: mostly neutral-to-positive, one real caveat

**All 12 combined, portfolio-level:**

| Variant | F1 | F2 | F3 | F4 | Full | Full MaxDD |
|---|---|---|---|---|---|---|
| 24h floor (current) | 10.84% | 8.97% | 12.16% | 6.34% | 39.05% | 6.44% |
| No floor | 10.84% | 8.97% | 12.16% | **6.86%** | **42.56%** | **5.41%** |

F1-F3 are byte-identical - the floor rarely actually triggers in this
9-month window (most gate-blocked positions recover to breakeven or hit
stop-loss before 24h elapses). Full-period return and combined
drawdown both improve without it.

**Caveat**: stocks alone see worse full-period drawdown without the
floor (6.41% -> 7.60%) even as return improves (37.30% -> 41.13%) - a
position that never recovers and never hits stop-loss sits stuck
longer without the floor, and that shows up as worse worst-case risk
on the stock sleeve specifically.

**Isolated per-symbol**: mostly identical between the two variants
(the floor didn't trigger for most names in this window); the few
symbols that did differ (`ILMN`, `VTRS`, `IBIT`, `ETHA`) all improved
without the floor, except `PYPL`'s full-period return which was
marginally worse (0.04% -> -0.26%, ~0.3pp).

## Decision: removed, per owner request, evidence accepted as mixed-but-acceptable

The floor triggered rarely enough in this data that this isn't a
strong test either way - full-period numbers mostly favor removal, one
real (if narrow) worst-case drawdown cost on stocks was flagged and
the owner chose to proceed anyway. `profit_gate.GATE_MAX_HOLD_HOURS`
set to `None` (was `24`). No other code changed - the mechanism itself
(`gate_floor_should_force_exit`) already handles `None` as "disabled,"
unchanged behavior. 247/247 tests passing (no test depended on the
module-level default).

## What this doesn't establish

- Low confidence either way given how rarely the floor actually fired
  in this specific 9-month window - a longer sideways/underwater
  stretch not represented here could show a larger effect.
- Same standing gaps as every backtest this session: crypto proxies
  only, same-bar fill timing, one fee level not a sweep.
