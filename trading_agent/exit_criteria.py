"""Per-position exit rules: stop-loss and partial take-profit, independent
of the SMA crossover signal. These are protective/profit-locking checks
that run alongside strategy.py's death-cross sell signal - whichever
condition is met first (or both) triggers an exit for that portion of the
position.

Unlike new entries, these exits are never blocked by can_trade(), the
circuit breaker, or the auto_execute_max_usd size cap once DRY_RUN is
False - those gates limit new risk-taking, and applying them to an exit
would mean being unable to cut a loss or lock in a gain exactly when it
matters. DRY_RUN itself still applies: no exit executes while it's True.

Tuning (backtest_2026-09-23.md's stop-loss/take-profit sweep): swept
stop_loss_pct and take_profit_pct together against the 11-series
robustness set (IBIT/ETHA plus GBTC's 6 regimes plus 3 Solana ETFs),
ranking by worst-case regime delta vs each series' own baseline first
(not mean or win-count) - every combination tested that day ((8%/50%),
(10%/50%)) had a worse worst-case outcome than the original 10%/15%.
That sweep never tested a 10%/20% combination specifically - see
backtest_2026-09-25_stop_take.md for that value (owner-requested 1:2
risk/reward ratio), which DID clear the bar (worst case -8.06% vs the
50%-take-profit combinations' -25.84% to -75.26%) and is now live -
TAKE_PROFIT_PCT is 20%, STOP_LOSS_PCT unchanged at 10%.
TAKE_PROFIT_SELL_FRACTION did improve on the original 10%/15% sweep: 70%
raised the mean delta (+6.77%) and win count (7/11) with only a small,
smooth worst-case cost (-3.38%, confirmed not a lucky single point by
checking neighboring values 65-75%) - a much more favorable risk/reward
trade than the stop-loss/take-profit level sweep showed, so it was
changed from the original 80%.

Trailing stop on the post-take-profit remainder (2026-09-24, owner
request - "if a trailing order into profit benefits us, use that as
well, if the math is good"): RobinHood's order API has no native
trailing-stop order type (confirmed against place_crypto_order/
place_equity_order's own schemas - only market/limit/stop_loss/
stop_limit exist), so this is implemented in software, evaluated each
cycle like the rest of check_exit, not as a resting broker order. Once
take-profit has fired and sold TAKE_PROFIT_SELL_FRACTION, the remaining
position was previously protected only by the ORIGINAL stop_loss_pct
measured from entry cost basis - meaning a run to +40% that reversed
could ride the remainder all the way back down to -10% from entry
before exiting, giving back nearly the whole gain. trailing_stop_pct
(when set) replaces that with a stop measured from the highest price
seen since take-profit fired, locking in more of a large move instead
of giving it all back. See backtest_2026-09-24_trailing_stop.md for the
sweep behind the chosen default - see also TRAILING_STOP_PCT below for
whether a value was actually adopted or left disabled (None).
"""

STOP_LOSS_PCT = 0.10              # exit the full position if price drops
                                   # this far below the average cost basis
TAKE_PROFIT_PCT = 0.20            # trigger level for partial profit-taking.
                                   # Raised from 15% 2026-09-25 (owner request,
                                   # a 1:2 risk/reward ratio against the 10%
                                   # stop-loss) - backtested first against 48
                                   # real series (current watchlist composition,
                                   # 90-day hourly + 3 daily regimes): 22 helped/
                                   # 9 hurt/17 flat, mean delta +2.02%, worst
                                   # case -8.06% - a real but bounded cost, well
                                   # inside what the original 2026-09-23 sweep
                                   # already rejected at other levels (-25.84%
                                   # to -75.26% for 50% take-profit). See
                                   # backtest_2026-09-25_stop_take.md.
TAKE_PROFIT_SELL_FRACTION = 0.70  # fraction of the position sold at the
                                   # take-profit trigger; the rest keeps riding
TRAILING_STOP_PCT = None          # see backtest_2026-09-24_trailing_stop.md;
                                   # None disables the trailing stop entirely
                                   # (pre-2026-09-24 behavior: the remainder
                                   # rides on the original entry-basis
                                   # stop-loss alone)


def check_exit(current_price, avg_cost_basis, take_profit_already_taken,
                peak_price_since_take_profit=None,
                stop_loss_pct=STOP_LOSS_PCT, take_profit_pct=TAKE_PROFIT_PCT,
                take_profit_sell_fraction=TAKE_PROFIT_SELL_FRACTION,
                trailing_stop_pct=TRAILING_STOP_PCT):
    """Evaluate one position against the stop-loss/take-profit/trailing-stop
    rules.

    peak_price_since_take_profit: the highest price observed since
    take-profit fired for this position (the caller tracks and persists
    this - e.g. PositionStateStore - updating it to max(existing, current_price)
    every cycle the position is open and take_profit_already_taken is True).
    Required for the trailing-stop check to do anything; ignored otherwise.

    stop_loss_pct/take_profit_pct/take_profit_sell_fraction/trailing_stop_pct
    override the module-level defaults when given - lets backtest.py sweep
    these values instead of only ever testing the hardcoded defaults. Live
    callers (PLAYBOOK.md) never pass these; they use the tuned defaults.

    Returns (reason, sell_fraction):
      ("stop_loss", 1.0)          - exit the entire position (from entry
                                     cost basis - always checked first,
                                     regardless of take-profit/trailing state)
      ("take_profit", fraction)   - sell take_profit_sell_fraction of the
                                     position; only fires once per position
                                     (take_profit_already_taken guards repeats)
      ("trailing_stop", 1.0)      - only reachable after take-profit already
                                     fired and trailing_stop_pct is set: sell
                                     the remainder because price has pulled
                                     back trailing_stop_pct from its post-
                                     take-profit peak
      (None, 0.0)                  - nothing fired; other logic (e.g. the
                                     SMA death cross) still applies
    """
    if avg_cost_basis <= 0:
        return (None, 0.0)

    pct_change = (current_price - avg_cost_basis) / avg_cost_basis

    if pct_change <= -stop_loss_pct:
        return ("stop_loss", 1.0)

    if take_profit_already_taken:
        if (
            trailing_stop_pct is not None
            and peak_price_since_take_profit is not None
            and peak_price_since_take_profit > 0
        ):
            drawdown_from_peak = (
                (peak_price_since_take_profit - current_price) / peak_price_since_take_profit
            )
            if drawdown_from_peak >= trailing_stop_pct:
                return ("trailing_stop", 1.0)
        return (None, 0.0)

    if pct_change >= take_profit_pct:
        return ("take_profit", take_profit_sell_fraction)

    return (None, 0.0)
