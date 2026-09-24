# Trailing-stop-on-remainder backtest (2026-09-24)

## Request

Owner: "setting limit orders to the best price from our analysis and if
a trailing order into profit benefits us, use that as well. If
available and the math is good."

Two separate asks, handled separately:
1. **Limit order pricing** — see the PLAYBOOK.md/config.py changes in
   the same commit as this file; crypto orders were found to be using
   plain `market` orders (accepting up to ~1%/~5% buy/sell slippage per
   `place_crypto_order`'s own documented collar), while stocks already
   use marketable limit orders. Switching crypto to match stocks is a
   pure slippage-cap correction, not a signal/timing change, so it
   didn't need backtesting the way this trailing-stop question does.
2. **Trailing stop "into profit"** — this file. RobinHood's order API
   has no native trailing-stop order type (checked directly against
   `place_crypto_order`/`place_equity_order`'s schemas: only
   market/limit/stop_loss/stop_limit exist for crypto,
   market/limit/stop_market/stop_limit for equities). A trailing stop
   is only implementable in software, evaluated each cycle exactly like
   the existing stop-loss/take-profit checks — not as a resting broker
   order (also: `cancel_crypto_order`/`cancel_equity_order`, which a
   "walk the stop up" design would need, explicitly require confirming
   with the owner before each call per their own tool descriptions,
   incompatible with unattended hourly automation).

## What was tested

`exit_criteria.check_exit` and `backtest.py` were extended (same commit)
to support a `trailing_stop_pct` parameter: once take-profit has fired
and sold `TAKE_PROFIT_SELL_FRACTION` (70%), the remaining 30% is
currently protected only by the *original* `stop_loss_pct` (10%)
measured from entry cost basis. The new mechanism would instead track
the highest price seen since take-profit fired and exit the remainder
if price pulls back `trailing_stop_pct` from that peak — full code and
test coverage in `exit_criteria.py` / `tests/test_exit_criteria.py`,
merged regardless of the result below (the mechanism is correct and
tested; whether to *turn it on* is the question this file answers).

**Series used** (12 total, real market data via `get_equity_historicals`,
same source and methodology as `backtest_2026-09-23.md`):
- 6 short series, 90 days hourly: IBIT, ETHA, GBTC, CRWD, PANW, TWLO
  (crypto ETF proxies + 3 live `STOCK_WATCHLIST` symbols)
- 6 long series: GBTC's full 2020-01-02 to 2026-09-23 daily history
  (1,690 bars) split into 6 roughly-equal regimes, same technique as
  the original stop-loss/take-profit sweep

**Parameters held fixed at their tuned defaults** (`entry_filter`,
`position_state`, `exit_criteria`): `min_strength_pct=0`,
`cooldown_bars=4`, `stop_loss_pct=0.10`, `take_profit_pct=0.15`,
`take_profit_sell_fraction=0.70`, SMA(10,30). Only `trailing_stop_pct`
was swept: `None` (baseline, current live behavior), 3%, 5%, 7%, 10%, 15%.

**First check: does this even get enough trials to be trustworthy?**
The 6 short series produced only 1 take-profit event each (6 total) —
too thin to trust any single number, the exact overfitting trap this
codebase already got burned by once on `max_trades_per_day`. The 6
GBTC regimes added 11 more (16 total), enough to see a real pattern
rather than noise from one lucky/unlucky trade.

## Result: the math is not good — trailing stop hurts, often severely

| trailing_stop_pct | mean delta vs. baseline | worst-case delta | series helped | series hurt |
|---|---|---|---|---|
| 3%  | -7.40pp  | -70.58pp | 3 | 7 |
| 5%  | -6.33pp  | -54.04pp | 2 | 4 |
| 7%  | -5.29pp  | -45.77pp | 1 | 4 |
| 10% | -3.95pp  | -47.82pp | 2 | 3 |
| 15% | -4.78pp  | -49.84pp | 0 | 3 |

Every single candidate value has a **negative mean delta and a large
negative worst case** across the 12-series set. The worst case is
consistently GBTC's strongest bull regime (`GBTC_regime1`): -45pp to
-71pp depending on tightness. That's not noise — it's the mechanism
doing exactly what a trailing stop does: exit on the first meaningful
pullback within an ongoing trend. During GBTC's biggest rallies, the
remaining 30% (deliberately left unprotected by anything but the wide
10% entry-basis stop-loss, per `TAKE_PROFIT_SELL_FRACTION`'s own
2026-09-23 tuning) rides the rest of a very large move. A trailing stop
— at *any* tightness tested — clips that short on the first normal
pullback, well before the trend actually ends.

This is the same finding the original `TAKE_PROFIT_SELL_FRACTION` sweep
already made from the other direction: letting the remainder ride
loose, not tight, is *why* 70%/30% beat 80%/20% and other splits in the
first place. A trailing stop on the remainder fights that same
conclusion.

## Decision

**`exit_criteria.TRAILING_STOP_PCT` stays `None` — the feature is
built, tested, and documented, but disabled.** Not adopted. The
mechanism remains available (any future re-test just needs to pass
`trailing_stop_pct=<value>` to `backtest()` or `check_exit()`) but
nothing in `PLAYBOOK.md` or the live cycle calls it with a non-None
value, so live behavior is unchanged: the post-take-profit remainder
keeps riding on the original entry-basis stop-loss alone, exactly as
before this investigation.

If this gets revisited later, a size-scaled trailing stop (wider on
volatile assets, tighter on calm ones) or a stop that only arms after a
much larger cushion (e.g. don't trail until price is 2x the
take-profit level above cost) might behave differently — untested here,
noted for a future pass rather than assumed to also fail.
