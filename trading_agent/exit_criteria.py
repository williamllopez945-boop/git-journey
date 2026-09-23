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
(not mean or win-count) - every alternative combination tested had a
worse worst-case outcome than the original 10%/15%, so those two values
are unchanged, now empirically validated rather than just an initial
guess. TAKE_PROFIT_SELL_FRACTION did improve on the same sweep: 70%
raised the mean delta (+6.77%) and win count (7/11) with only a small,
smooth worst-case cost (-3.38%, confirmed not a lucky single point by
checking neighboring values 65-75%) - a much more favorable risk/reward
trade than the stop-loss/take-profit level sweep showed, so it was
changed from the original 80%.
"""

STOP_LOSS_PCT = 0.10              # exit the full position if price drops
                                   # this far below the average cost basis
TAKE_PROFIT_PCT = 0.15            # trigger level for partial profit-taking
TAKE_PROFIT_SELL_FRACTION = 0.70  # fraction of the position sold at the
                                   # take-profit trigger; the rest keeps riding


def check_exit(current_price, avg_cost_basis, take_profit_already_taken,
                stop_loss_pct=STOP_LOSS_PCT, take_profit_pct=TAKE_PROFIT_PCT,
                take_profit_sell_fraction=TAKE_PROFIT_SELL_FRACTION):
    """Evaluate one position against the stop-loss/take-profit rules.

    stop_loss_pct/take_profit_pct/take_profit_sell_fraction override the
    module-level defaults when given - lets backtest.py sweep these
    values instead of only ever testing the hardcoded defaults. Live
    callers (PLAYBOOK.md) never pass these; they use the tuned defaults.

    Returns (reason, sell_fraction):
      ("stop_loss", 1.0)          - exit the entire position
      ("take_profit", fraction)   - sell take_profit_sell_fraction of the
                                     position; only fires once per position
                                     (take_profit_already_taken guards repeats)
      (None, 0.0)                  - neither rule fired; other logic (e.g.
                                     the SMA death cross) still applies
    """
    if avg_cost_basis <= 0:
        return (None, 0.0)

    pct_change = (current_price - avg_cost_basis) / avg_cost_basis

    if pct_change <= -stop_loss_pct:
        return ("stop_loss", 1.0)

    if pct_change >= take_profit_pct and not take_profit_already_taken:
        return ("take_profit", take_profit_sell_fraction)

    return (None, 0.0)
