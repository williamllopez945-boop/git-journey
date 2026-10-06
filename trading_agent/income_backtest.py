"""Backtests the income sleeve's dip-entry/stop-trim rule (income_signals.py
+ income_exit.py) against real historical daily closes - same production
code paths, not a re-implementation, same convention as backtest.py.

A new, dedicated loop rather than a parameterization of backtest.py:
that module calls strategy.sma_crossover_signal/entry_filter/profit_gate
directly throughout a heavily-tested loop (test_backtest.py,
test_portfolio_backtest.py); this sleeve's signal is much simpler - one
threshold entry, one stop, one trim, no RSI/volume/cooldown/gate
layering - so a dedicated ~60-line loop is less total risk than
injecting a signal function into that load-bearing code. Reuses
backtest.summarize unchanged for headline metrics: that function is
already pure over (trades, equity_curve, closes, starting_cash), with
no crossover-specific logic.

Models price action only - no distribution/dividend cash flow is
simulated. That understates real total return for a strategy whose
entire appeal is the distribution; state this plainly in any report,
don't bury it.

Every income-sleeve candidate has well under 2 years of real daily
history (YMAX/YMAG oldest, ~2024 inception; most others 2025-only) - a
backtest here covers at best a few hundred bars for the oldest names, a
few dozen for the newest. Treat any result as a mechanism sanity-check,
not a tuned parameter the way exit_criteria.py's numbers are.

Position sizing here uses 100% of available cash per entry (not the
live sleeve's INCOME_RISK_LIMITS caps), to isolate and evaluate the
entry/exit signal quality itself - same convention backtest.py uses.
"""

from .income_signals import classify_dip, DIP_LOOKBACK_DAYS, DIP_ENTRY_THRESHOLD
from .income_exit import (
    check_income_exit,
    INCOME_STOP_LOSS_PCT,
    INCOME_TRIM_TRIGGER_PCT,
    INCOME_TRIM_SELL_FRACTION,
)


def income_backtest(closes, starting_cash=100.0, lookback_days=DIP_LOOKBACK_DAYS,
                     entry_threshold=DIP_ENTRY_THRESHOLD, stop_loss_pct=INCOME_STOP_LOSS_PCT,
                     trim_trigger_pct=INCOME_TRIM_TRIGGER_PCT, trim_sell_fraction=INCOME_TRIM_SELL_FRACTION,
                     fee_pct=0.0):
    """closes: oldest-to-newest daily close prices for one symbol.

    fee_pct: round-trip friction applied at every fill, same model as
    backtest.py's fee_pct (symmetric haircut on both sides of a trade).
    0.0 (default) is frictionless.

    Returns (trades, equity_curve), same shape as backtest.backtest:
      trades - list of dicts: {index, action, reason, qty, price, cash_after}
      equity_curve - list of portfolio value (cash + mark-to-market
                      position) at each bar, same length as closes
    """
    cash = starting_cash
    position_qty = 0.0
    avg_cost_basis = 0.0
    trim_taken = False
    trades = []
    equity_curve = []

    for i, price in enumerate(closes):
        if position_qty > 0:
            reason, fraction = check_income_exit(
                price, avg_cost_basis, trim_taken,
                stop_loss_pct=stop_loss_pct, trim_trigger_pct=trim_trigger_pct,
                trim_sell_fraction=trim_sell_fraction,
            )
            if reason == "stop_loss":
                proceeds = position_qty * price * (1 - fee_pct)
                cash += proceeds
                trades.append({"index": i, "action": "sell", "reason": reason,
                                "qty": position_qty, "price": price, "cash_after": cash})
                position_qty = 0.0
                avg_cost_basis = 0.0
                trim_taken = False
            elif reason == "trim":
                sell_qty = position_qty * fraction
                proceeds = sell_qty * price * (1 - fee_pct)
                cash += proceeds
                position_qty -= sell_qty
                trim_taken = True
                trades.append({"index": i, "action": "sell", "reason": "trim",
                                "qty": sell_qty, "price": price, "cash_after": cash})

        if position_qty == 0 and cash > 0:
            window = closes[: i + 1]
            signal = classify_dip(window, lookback_days=lookback_days, entry_threshold=entry_threshold)
            if signal == "dip_buy":
                qty = cash / (price * (1 + fee_pct))
                position_qty = qty
                avg_cost_basis = price * (1 + fee_pct)
                trades.append({"index": i, "action": "buy", "reason": "dip_buy",
                                "qty": qty, "price": price, "cash_after": 0.0})
                cash = 0.0

        equity_curve.append(cash + position_qty * price)

    return trades, equity_curve
