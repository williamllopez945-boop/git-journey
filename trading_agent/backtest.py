"""Backtests the strategy (strategy.py's SMA crossover + exit_criteria.py's
stop-loss/take-profit) against real historical price series, using the
same production code paths as the live agent - not a re-implementation.

Crypto has no historicals source (see README's "Crypto price history"
section), so this runs against equity/ETF historicals instead - real
market data, not synthetic. Bitcoin/Ethereum ETFs (IBIT, ETHA, etc.) are
reasonable proxies since they track the underlying crypto price closely,
but they trade only during equity market hours, not 24/7 like crypto, and
carry their own tracking error - not a perfect substitute.

Position sizing here uses 100% of available cash per trade (not the
live agent's 5%-of-portfolio cap), to isolate and evaluate the entry/exit
signal quality itself, independent of the risk-management layer. See
README for how to translate these results to the live 5%-cap sizing.
"""

from .strategy import sma_crossover_signal
from .exit_criteria import check_exit
from .entry_filter import confirmed_signal


def backtest(closes, short_window, long_window, starting_cash=100.0, min_strength_pct=None, cooldown_bars=None):
    """Run the strategy over a closing-price series (oldest first).

    min_strength_pct: when set, entries require entry_filter.confirmed_signal
    (crossover strength must clear this threshold) instead of the raw
    strategy.sma_crossover_signal - filters weak/marginal crosses likely to
    whipsaw. None (default) uses the unfiltered signal.

    cooldown_bars: when set, blocks re-entry into a fresh buy signal for
    this many bars after a position fully closes (stop-loss or death
    cross) - targets repeated whipsaw losses from re-entering a choppy
    market immediately after being stopped out. None (default) disables
    the cooldown.

    Returns (trades, equity_curve):
      trades - list of dicts: {index, action, reason, qty, price, cash_after}
      equity_curve - list of portfolio value (cash + mark-to-market position)
                      at each bar, same length as closes
    """
    cash = starting_cash
    position_qty = 0.0
    avg_cost_basis = 0.0
    took_profit = False
    trades = []
    equity_curve = []
    last_exit_index = None

    for i, price in enumerate(closes):
        window = closes[: i + 1]

        if position_qty > 0:
            reason, fraction = check_exit(price, avg_cost_basis, took_profit)
            if reason == "stop_loss":
                proceeds = position_qty * price
                cash += proceeds
                trades.append({"index": i, "action": "sell", "reason": "stop_loss",
                                "qty": position_qty, "price": price, "cash_after": cash})
                position_qty = 0.0
                avg_cost_basis = 0.0
                took_profit = False
                last_exit_index = i
            elif reason == "take_profit":
                sell_qty = position_qty * fraction
                proceeds = sell_qty * price
                cash += proceeds
                position_qty -= sell_qty
                took_profit = True
                trades.append({"index": i, "action": "sell", "reason": "take_profit",
                                "qty": sell_qty, "price": price, "cash_after": cash})

        if min_strength_pct is None:
            signal = sma_crossover_signal(window, short_window, long_window)
        else:
            signal = confirmed_signal(window, short_window, long_window, min_strength_pct)

        if position_qty > 0 and signal == "sell":
            proceeds = position_qty * price
            cash += proceeds
            trades.append({"index": i, "action": "sell", "reason": "death_cross",
                            "qty": position_qty, "price": price, "cash_after": cash})
            position_qty = 0.0
            avg_cost_basis = 0.0
            took_profit = False
            last_exit_index = i
        elif position_qty == 0 and cash > 0 and signal == "buy":
            in_cooldown = (
                cooldown_bars is not None
                and last_exit_index is not None
                and i - last_exit_index < cooldown_bars
            )
            if not in_cooldown:
                qty = cash / price
                position_qty = qty
                avg_cost_basis = price
                trades.append({"index": i, "action": "buy", "reason": "fresh_buy_cross",
                                "qty": qty, "price": price, "cash_after": 0.0})
                cash = 0.0

        equity_curve.append(cash + position_qty * price)

    return trades, equity_curve


def summarize(trades, equity_curve, closes, starting_cash):
    """Compute headline metrics for a backtest run."""
    final_equity = equity_curve[-1] if equity_curve else starting_cash
    total_return_pct = (final_equity - starting_cash) / starting_cash * 100

    buy_hold_qty = starting_cash / closes[0]
    buy_hold_final = buy_hold_qty * closes[-1]
    buy_hold_return_pct = (buy_hold_final - starting_cash) / starting_cash * 100

    peak = starting_cash
    max_drawdown_pct = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        drawdown = (peak - e) / peak * 100
        max_drawdown_pct = max(max_drawdown_pct, drawdown)

    round_trips = []
    entry = None
    for t in trades:
        if t["action"] == "buy":
            entry = t
        elif t["action"] == "sell" and entry is not None:
            pnl_pct = (t["price"] - entry["price"]) / entry["price"] * 100
            round_trips.append({"reason": t["reason"], "pnl_pct": pnl_pct})
            if t["reason"] != "take_profit":
                entry = None

    wins = [r for r in round_trips if r["pnl_pct"] > 0]
    win_rate_pct = (len(wins) / len(round_trips) * 100) if round_trips else None

    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "buy_hold_return_pct": buy_hold_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "num_trades": len(trades),
        "num_round_trips": len(round_trips),
        "win_rate_pct": win_rate_pct,
        "round_trips": round_trips,
    }
