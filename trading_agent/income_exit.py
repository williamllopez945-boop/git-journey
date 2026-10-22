"""Exit rule for the income sleeve (YieldMax-style weekly-distribution
basket ETFs - see PLAYBOOK.md's "Income sleeve" section).

A new, separate constant set and function - NOT exit_criteria.py's
STOP_LOSS_PCT/TAKE_PROFIT_PCT (per this project's per-sleeve-constants
convention; VOLTRAP keeps its own limits too). exit_criteria.check_exit
is also tuned for a strategy that fully exits on every death cross -
these ETFs are a weekly-income base meant to be held, so this sleeve
uses a looser stop and a partial trim instead of a tight stop/take-profit
pair.

Same (reason, sell_fraction) return shape as exit_criteria.check_exit
for drop-in familiarity, but the thresholds mean something different
here:

INCOME_STOP_LOSS_PCT is deliberately looser than exit_criteria.py's 4%.
These ETFs' share price structurally drifts down with every weekly
distribution paid (return of capital, not just yield) - a tight stop
sized for a trend-following strategy would fire on routine NAV decay,
not on an actual adverse move. 15% gives real room before cutting.

INCOME_TRIM_TRIGGER_PCT/INCOME_TRIM_SELL_FRACTION lock in part of a price
gain (on top of distributions already collected) without fully exiting
the income position - the same "keep most of the position, bank some
gain" idea as exit_criteria.py's take-profit, just at different levels
since the two strategies' typical holding period and volatility differ.
"""

INCOME_STOP_LOSS_PCT = 0.15        # exit the full position if price drops
                                    # this far below cost basis - looser
                                    # than the main bot's 4% on purpose,
                                    # see module docstring.
INCOME_TRIM_TRIGGER_PCT = 0.10     # price gain (not counting distributions
                                    # received) that triggers a partial trim.
INCOME_TRIM_SELL_FRACTION = 0.50   # fraction of the position sold at the
                                    # trim trigger; the rest keeps riding
                                    # (and keeps collecting distributions).


def check_income_exit(current_price, avg_cost_basis, trim_already_taken,
                       stop_loss_pct=INCOME_STOP_LOSS_PCT,
                       trim_trigger_pct=INCOME_TRIM_TRIGGER_PCT,
                       trim_sell_fraction=INCOME_TRIM_SELL_FRACTION):
    """Evaluate one income-sleeve position against the stop-loss/trim rule.

    Returns (reason, sell_fraction):
      ("stop_loss", 1.0)        - exit the entire position (checked first,
                                   regardless of trim state)
      ("trim", fraction)        - sell trim_sell_fraction of the position;
                                   only fires once per position
                                   (trim_already_taken guards repeats)
      (None, 0.0)                - nothing fired; keep holding and
                                   collecting distributions
    """
    if avg_cost_basis <= 0:
        return (None, 0.0)

    pct_change = (current_price - avg_cost_basis) / avg_cost_basis

    if pct_change <= -stop_loss_pct:
        return ("stop_loss", 1.0)

    if trim_already_taken:
        return (None, 0.0)

    if pct_change >= trim_trigger_pct:
        return ("trim", trim_sell_fraction)

    return (None, 0.0)
