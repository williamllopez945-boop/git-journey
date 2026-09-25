# Profit-lock stop backtest: 15% trigger / +10% floor (2026-09-25)

## Request

Owner: "Improve the when we hit 15% move stop loss from -10% to 10% so
we can still make a profit. Does this make our chances better with the
back test?" — once a position's unrealized gain reaches 15%, tighten
the stop-loss from -10% (below cost basis) to +10% (above cost basis),
so a reversal after running up can't fully round-trip back into a loss.

This is distinct from the existing (disabled) trailing stop: that one
only activates *after* take-profit has already fired, trailing from the
post-take-profit peak. This is a *pre*-take-profit mechanism, protecting
the run-up between 0% and the 20% take-profit trigger.

## What was built

`exit_criteria.check_exit` gained `peak_price_since_entry`,
`profit_lock_trigger_pct`, `profit_lock_stop_pct` parameters (mirrors
the trailing stop's own `peak_price_since_take_profit`/
`trailing_stop_pct` pattern exactly) and a new `"profit_lock_stop"`
return reason. `backtest.py` tracks `peak_since_entry` (reset on every
fresh buy, updated every bar the position is open) and passes it
through. Both default to `None` (disabled) - same convention as
`TRAILING_STOP_PCT`. 8 new unit tests in `test_exit_criteria.py`
(disabled-by-default, fires-at-floor, exact-threshold, doesn't-fire-
before-trigger-clears, doesn't-fire-while-still-above-floor, stop-loss-
still-checked-first, inert-after-take-profit-already-taken, inert-
without-a-peak) - 157/157 total tests pass.

## What was tested

**Series**: same 48-series set as `backtest_2026-09-25_stop_take.md` -
current watchlist (`IBIT`/`ETHA` + the 10-name `STOCK_WATCHLIST`), 90-day
hourly + 3.7yr daily in 3 regimes.

**Config held fixed at current production values**: `short_window=10`,
`long_window=30`, `min_strength_pct=0`, `cooldown_bars=4`,
`stop_loss_pct=0.10`, `take_profit_pct=0.20`,
`take_profit_sell_fraction=0.70` (i.e. today's already-shipped 1:2
ratio). Only the profit-lock params varied: disabled (baseline) vs.
15%/10% (requested) vs. two neighbors (12%/8%, 18%/12%) to rule out a
lucky single point.

## Result: hurts more than it helps, same root cause as the trailing-stop finding

| Variant | Helped | Hurt | Flat | Mean delta | Worst case | Best case |
|---|---|---|---|---|---|---|
| **15%/10% (requested)** | 2 | 6 | 40 | **-1.36%** | **-25.00%** (CRWD, 2024) | +1.78% |
| 12%/8% (tighter) | 5 | 12 | 31 | -2.79% | -36.63% | +7.68% |
| 18%/12% (looser) | 1 | 4 | 43 | -0.41% | -15.12% | +2.05% |

**Every variant tested has a negative mean delta and a large negative
worst case.** 40 of 48 series were unaffected (`flat`) - the mechanism
only ever matters in the minority of windows where a position both (a)
ran up 15%+ pre-take-profit and (b) then pulled back to 10% or below
before ever reaching the 20% take-profit trigger. In those windows, it
does what it's built to do - lock in the +10% instead of risking a
round-trip - but the cost is real: in the strong-trend regimes where a
position instead kept running past 20% and got a real take-profit event
(`CRWD_regime2_2024`: 72.10% baseline → 47.10% with profit-lock,
`ILMN_regime2_2024`: 61.45% → 39.82%, `ETHA_regime2_2024`: 56.53% →
43.40%), the profit-lock stop exits at +10% on the way to what would
have been a much bigger eventual take-profit realization. Tightening
the trigger/floor (12%/8%) makes this worse on every axis; loosening it
(18%/12%) makes it less bad but still net negative.

**This is the same finding as `backtest_2026-09-24_trailing_stop.md`,
one day earlier, for the mirror-image mechanism:** letting a position
ride loose through its full run rather than clamping it early is
exactly why the 70%/30% take-profit split and the 20% (vs 15%) trigger
both already beat tighter alternatives in this project's prior tuning.
A profit-lock stop before take-profit fights that same conclusion from
the other side of the trigger, for the same underlying reason.

## Decision

**Not adopted.** `PROFIT_LOCK_TRIGGER_PCT`/`PROFIT_LOCK_STOP_PCT` stay
`None` - the mechanism is built, tested, and documented (same treatment
as the trailing stop), but live behavior is unchanged: a position that
runs up 15%+ and then reverses before hitting 20% take-profit currently
rides on the -10% entry-basis stop-loss alone, same as before this
investigation. If revisited, a much higher trigger (closer to the 20%
take-profit level itself, so it's protecting realized gains near the
take-profit line rather than clamping mid-run) or a floor tied to a
fraction of the peak rather than a fixed level might behave
differently - untested here, noted for a future pass rather than
assumed to also fail.
