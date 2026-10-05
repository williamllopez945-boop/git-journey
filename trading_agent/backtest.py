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
from .exit_criteria import check_exit, STOP_LOSS_PCT, TAKE_PROFIT_PCT, TAKE_PROFIT_SELL_FRACTION
from .entry_filter import confirmed_signal
from .rsi_filter import passes_rsi_filter, DEFAULT_RSI_PERIOD, DEFAULT_RSI_OVERBOUGHT_PCT
from .volume_filter import passes_volume_filter, DEFAULT_VOLUME_PERIOD, DEFAULT_VOLUME_MIN_RATIO
from .profit_gate import blocks_sell_cross, MIN_SELL_PROFIT_PCT, gate_floor_should_force_exit


def backtest(closes, short_window, long_window, starting_cash=100.0, min_strength_pct=None, cooldown_bars=None,
             stop_loss_pct=STOP_LOSS_PCT, take_profit_pct=TAKE_PROFIT_PCT,
             take_profit_sell_fraction=TAKE_PROFIT_SELL_FRACTION,
             rsi_period=None, rsi_overbought_pct=DEFAULT_RSI_OVERBOUGHT_PCT,
             volumes=None, volume_period=DEFAULT_VOLUME_PERIOD, volume_min_ratio=DEFAULT_VOLUME_MIN_RATIO,
             min_sell_profit_pct=MIN_SELL_PROFIT_PCT,
             gate_max_hold_bars=None, fee_pct=0.0):
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

    stop_loss_pct/take_profit_pct/take_profit_sell_fraction: override
    exit_criteria.py's module defaults - lets this sweep those values
    instead of only ever testing the hardcoded defaults.

    rsi_period/rsi_overbought_pct: when rsi_period is set, a fresh buy
    entry additionally requires rsi_filter.passes_rsi_filter (RSI below
    the overbought threshold) - blocks entries into an already-extended
    move. None (default) disables the RSI filter entirely.

    volumes/volume_period/volume_min_ratio: when volumes is given (a list
    of per-bar volumes, same length and order as closes), a fresh buy
    entry additionally requires volume_filter.passes_volume_filter
    (current bar's volume at least volume_min_ratio times its own recent
    average) - blocks entries on unconvincing, low-volume drift. None
    (default) disables the volume filter entirely.

    min_sell_profit_pct: when set, profit_gate.blocks_sell_cross holds a
    death-cross sell signal instead of executing it while the position's
    unrealized P&L is below this threshold (a fraction: 0.0 = requires
    breakeven or better) - stop-loss/take-profit are unaffected and still
    protect the held position every bar. Defaults to profit_gate.py's
    tuned live value (0.0, adopted 2026-09-28); pass None to disable the
    gate entirely (pre-2026-09-28 behavior: every death-cross sells
    immediately regardless of P&L). See profit_gate.py and
    backtest_2026-09-28_sell_cross_profit_gate.md.

    gate_max_hold_bars: profit_gate.gate_floor_should_force_exit's time
    floor - force a gate-blocked position out after this many bars,
    regardless of P&L, even though blocks_sell_cross would otherwise keep
    holding it. None (default) disables the floor - unchanged pre-floor
    behavior. See profit_gate.py.

    fee_pct: round-trip friction applied at every fill (fraction, e.g.
    0.001 = 0.1%) - a buy converts less cash into quantity than the raw
    price implies (qty = cash / (price * (1+fee_pct))), a sell returns
    less cash than the raw price implies (proceeds = qty * price *
    (1-fee_pct)). Every prior backtest in this project has flagged "no
    transaction costs/slippage modeled" as an unaddressed limitation
    (see backtest_2026-09-28_sell_cross_profit_gate.md's "What this
    doesn't establish") - this is that model, added 2026-09-29 for the
    ChatGPT-review-prompted gate re-test. It's a flat approximation of
    spread/slippage, not real fee data (Robinhood crypto/stock orders
    observed live this session mostly show $0 explicit fees - the real
    cost is bid/ask spread from marketable-limit fills, which this
    proxies as a symmetric haircut on both sides of a trade, applied
    identically to every fill reason - buy, stop_loss, take_profit,
    death_cross, gate_floor). 0.0 (default) is the pre-existing,
    frictionless behavior.

    Returns (trades, equity_curve):
      trades - list of dicts: {index, action, reason, qty, price, cash_after}
      equity_curve - list of portfolio value (cash + mark-to-market position)
                      at each bar, same length as closes
    """
    cash = starting_cash
    position_qty = 0.0
    avg_cost_basis = 0.0
    took_profit = False
    blocked_since_index = None
    trades = []
    equity_curve = []
    last_exit_index = None

    for i, price in enumerate(closes):
        window = closes[: i + 1]

        if position_qty > 0:
            reason, fraction = check_exit(price, avg_cost_basis, took_profit,
                                           stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
                                           take_profit_sell_fraction=take_profit_sell_fraction)
            if reason == "stop_loss":
                proceeds = position_qty * price * (1 - fee_pct)
                cash += proceeds
                trades.append({"index": i, "action": "sell", "reason": reason,
                                "qty": position_qty, "price": price, "cash_after": cash})
                position_qty = 0.0
                avg_cost_basis = 0.0
                took_profit = False
                blocked_since_index = None
                last_exit_index = i
            elif reason == "take_profit":
                sell_qty = position_qty * fraction
                proceeds = sell_qty * price * (1 - fee_pct)
                cash += proceeds
                position_qty -= sell_qty
                took_profit = True
                trades.append({"index": i, "action": "sell", "reason": "take_profit",
                                "qty": sell_qty, "price": price, "cash_after": cash})

        if position_qty > 0 and blocked_since_index is not None:
            pct_change = (price - avg_cost_basis) / avg_cost_basis if avg_cost_basis > 0 else 0.0
            if min_sell_profit_pct is not None and pct_change >= min_sell_profit_pct:
                blocked_since_index = None
            elif gate_floor_should_force_exit(price, avg_cost_basis, i - blocked_since_index,
                                               max_hold_bars=gate_max_hold_bars):
                proceeds = position_qty * price * (1 - fee_pct)
                cash += proceeds
                trades.append({"index": i, "action": "sell", "reason": "gate_floor",
                                "qty": position_qty, "price": price, "cash_after": cash})
                position_qty = 0.0
                avg_cost_basis = 0.0
                took_profit = False
                blocked_since_index = None
                last_exit_index = i

        if min_strength_pct is None:
            signal = sma_crossover_signal(window, short_window, long_window)
        else:
            signal = confirmed_signal(window, short_window, long_window, min_strength_pct)

        if position_qty > 0 and signal == "sell":
            if blocks_sell_cross(price, avg_cost_basis, min_sell_profit_pct):
                if blocked_since_index is None:
                    blocked_since_index = i
            else:
                proceeds = position_qty * price * (1 - fee_pct)
                cash += proceeds
                trades.append({"index": i, "action": "sell", "reason": "death_cross",
                                "qty": position_qty, "price": price, "cash_after": cash})
                position_qty = 0.0
                avg_cost_basis = 0.0
                took_profit = False
                blocked_since_index = None
                last_exit_index = i
        elif position_qty == 0 and cash > 0 and signal == "buy":
            in_cooldown = (
                cooldown_bars is not None
                and last_exit_index is not None
                and i - last_exit_index < cooldown_bars
            )
            rsi_blocked = (
                rsi_period is not None
                and not passes_rsi_filter(window, rsi_period, rsi_overbought_pct)
            )
            volume_blocked = (
                volumes is not None
                and not passes_volume_filter(volumes[: i + 1], volume_period, volume_min_ratio)
            )
            if not in_cooldown and not rsi_blocked and not volume_blocked:
                qty = cash / (price * (1 + fee_pct))
                position_qty = qty
                avg_cost_basis = price * (1 + fee_pct)
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

    # profit_factor: gross gain / gross loss, both in pnl_pct terms (this
    # project's convention throughout - see exit_criteria.py etc.) rather
    # than dollar P&L. >1 means winning round trips outweigh losing ones
    # in aggregate; None when there's nothing to divide by (no losses, or
    # no round trips at all) rather than a misleading inf/0.
    losses = [r for r in round_trips if r["pnl_pct"] < 0]
    gross_gain = sum(r["pnl_pct"] for r in wins)
    gross_loss = -sum(r["pnl_pct"] for r in losses)
    profit_factor = (gross_gain / gross_loss) if gross_loss > 0 else None

    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "buy_hold_return_pct": buy_hold_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "num_trades": len(trades),
        "num_round_trips": len(round_trips),
        "win_rate_pct": win_rate_pct,
        "profit_factor": profit_factor,
        "round_trips": round_trips,
    }
