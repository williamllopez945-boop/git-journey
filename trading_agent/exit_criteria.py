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
"""

STOP_LOSS_PCT = 0.10              # exit the full position if price drops
                                   # this far below the average cost basis
TAKE_PROFIT_PCT = 0.15            # trigger level for partial profit-taking
TAKE_PROFIT_SELL_FRACTION = 0.80  # fraction of the position sold at the
                                   # take-profit trigger; the rest keeps riding


def check_exit(current_price, avg_cost_basis, take_profit_already_taken):
    """Evaluate one position against the stop-loss/take-profit rules.

    Returns (reason, sell_fraction):
      ("stop_loss", 1.0)     - exit the entire position
      ("take_profit", 0.80)  - sell TAKE_PROFIT_SELL_FRACTION of the
                                position; only fires once per position
                                (take_profit_already_taken guards repeats)
      (None, 0.0)             - neither rule fired; other logic (e.g. the
                                SMA death cross) still applies separately
    """
    if avg_cost_basis <= 0:
        return (None, 0.0)

    pct_change = (current_price - avg_cost_basis) / avg_cost_basis

    if pct_change <= -STOP_LOSS_PCT:
        return ("stop_loss", 1.0)

    if pct_change >= TAKE_PROFIT_PCT and not take_profit_already_taken:
        return ("take_profit", TAKE_PROFIT_SELL_FRACTION)

    return (None, 0.0)
