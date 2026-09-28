"""Per-position exit rules: stop-loss and partial take-profit, independent
of the SMA crossover signal. These are protective/profit-locking checks
that run alongside strategy.py's death-cross sell signal - whichever
condition is met first (or both) triggers an exit for that portion of the
position.

Unlike new entries, these exits are never blocked by can_trade(), the
circuit breaker, or the auto_execute_max_pct size cap once DRY_RUN is
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
50%-take-profit combinations' -25.84% to -75.26%).
TAKE_PROFIT_SELL_FRACTION did improve on the original 10%/15% sweep: 70%
raised the mean delta (+6.77%) and win count (7/11) with only a small,
smooth worst-case cost (-3.38%, confirmed not a lucky single point by
checking neighboring values 65-75%) - a much more favorable risk/reward
trade than the stop-loss/take-profit level sweep showed, so it was
changed from the original 80%.

Tighter stop-loss/take-profit, 10%/20% -> 4%/8% (2026-09-28, owner
request - "tighter (smaller moves)"): re-swept stop_loss_pct/
take_profit_pct together against real historicals (STOCK_WATCHLIST +
IBIT/ETHA proxies), worst-case-first, checking neighbors rather than
trusting the first improvement seen. An initial pass looked best at
5%/10%; extending the sweep further found 4%/8% was the true
worst-case-optimal point - below 4%/8% whipsaw losses on otherwise-fine
assets (TWLO, IBIT) start to dominate and the relationship reverses.
Tested alongside profit_gate.py's gate_floor mechanism (see that
module) since both change how a held position ages; a price floor at
or looser than this new 4% stop-loss was confirmed inert (byte-identical
output to the stop-loss alone), so only a 24h time floor is adopted, not
a price floor. **Adopted 2026-09-28** (owner approval). See
backtest_2026-09-28_gate_floor_and_tighter_stops.md.

Two mechanisms were built, backtested, and explicitly rejected - both
removed 2026-09-28 (owner request, "I may be over complicating
everything, keep it simple") since they never fired in production
(disabled by default) and only added dead code paths/params:
- A trailing stop on the post-take-profit remainder (2026-09-24 request).
  Every variant tested (backtest_2026-09-24_trailing_stop.md) hurt more
  than it helped - clipping a position before a strong trend fully plays
  out costs more than it protects.
- A profit-lock stop tightening the pre-take-profit floor once a
  position's peak gain cleared a trigger (2026-09-25 request). Same
  result at the requested 15%/10% plus two neighboring pairs
  (backtest_2026-09-25_profit_lock.md): every variant hurt, same root
  cause as the trailing-stop finding.
If either idea is revisited, both backtest docs and this module's git
history (before 2026-09-28) have the full implementation and tuning.
"""

STOP_LOSS_PCT = 0.04               # exit the full position if price drops
                                   # this far below the average cost basis.
                                   # Tightened from 10% 2026-09-28 (owner
                                   # request) - see backtest_2026-09-28_
                                   # gate_floor_and_tighter_stops.md.
TAKE_PROFIT_PCT = 0.08            # trigger level for partial profit-taking.
                                   # Tightened from 20% 2026-09-28 (owner
                                   # request, keeps the 1:2 risk/reward
                                   # ratio against the new 4% stop-loss) -
                                   # see backtest_2026-09-28_gate_floor_and_
                                   # tighter_stops.md.
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
      ("stop_loss", 1.0)          - exit the entire position (from entry
                                     cost basis - always checked first,
                                     regardless of take-profit state)
      ("take_profit", fraction)   - sell take_profit_sell_fraction of the
                                     position; only fires once per position
                                     (take_profit_already_taken guards repeats)
      (None, 0.0)                  - nothing fired; other logic (e.g. the
                                     SMA death cross) still applies
    """
    if avg_cost_basis <= 0:
        return (None, 0.0)

    pct_change = (current_price - avg_cost_basis) / avg_cost_basis

    if pct_change <= -stop_loss_pct:
        return ("stop_loss", 1.0)

    if take_profit_already_taken:
        return (None, 0.0)

    if pct_change >= take_profit_pct:
        return ("take_profit", take_profit_sell_fraction)

    return (None, 0.0)
