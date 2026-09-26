"""Multi-asset portfolio backtest: runs the same production entry/exit rules
(entry_filter.confirmed_signal, exit_criteria.check_exit) across several
price series concurrently, sharing one cash pool, to evaluate
RISK_LIMITS["max_concurrent_positions"] - something backtest.py's
single-asset simulator cannot test, since it only ever holds one position
at a time and so has no notion of "how many assets are open at once."

Requires all series to be the same length and bar-aligned (same calendar
dates/timestamps at each index) - sizing and the concurrency cap only make
sense when every asset's price at index i is simultaneous with every other
asset's price at index i.
"""

from .strategy import sma_crossover_signal
from .exit_criteria import check_exit, STOP_LOSS_PCT, TAKE_PROFIT_PCT, TAKE_PROFIT_SELL_FRACTION
from .entry_filter import _sma, confirmed_signal, crossover_strength_pct


def portfolio_backtest(series, short_window, long_window, starting_cash=1000.0,
                        max_position_pct=0.05, max_concurrent_positions=None,
                        min_strength_pct=0, cooldown_bars=None,
                        stop_loss_pct=STOP_LOSS_PCT, take_profit_pct=TAKE_PROFIT_PCT,
                        take_profit_sell_fraction=TAKE_PROFIT_SELL_FRACTION,
                        max_aggregate_pct=None, timestamps=None, max_trades_per_day=None,
                        awesome_trade_min_crossover_pct=None, awesome_trade_aggregate_pct=None):
    """Run the strategy over several aligned closing-price series at once.

    series: dict {asset_name: [closes...]}, all the same length, bar i of
    every series representing the same point in time.

    max_position_pct: fraction of total portfolio value (cash + all
    open positions, mark-to-market) a fresh entry may allocate to one
    asset - mirrors RiskManager.position_size's live cap.

    max_concurrent_positions: None allows every asset to hold a position
    at once (uncapped, up to len(series)); an int blocks a fresh buy
    signal from opening a new position while that many assets already
    have one open, the same way the cooldown blocks entries in
    backtest.py - existing open positions are still fully managed
    (exits, take-profit) regardless of the cap.

    max_aggregate_pct: caps total mark-to-market value of ALL open
    positions combined at this fraction of portfolio value - mirrors
    RiskManager.position_size's aggregate clamp. Distinct from
    max_position_pct x max_concurrent_positions, which don't reliably
    compose into a portfolio-wide ceiling (e.g. 15% x 5 = 75%). None
    (default) disables the clamp, unchanged from before this parameter
    existed.

    timestamps: optional list of ISO datetime/date strings, same length as
    each series, bar i's timestamp for every asset (they're bar-aligned,
    so one shared list suffices). Required only when max_trades_per_day is
    set - day boundaries are taken from timestamps[i][:10] (the date
    portion), matching RiskManager's UTC-day trades_today reset. None
    (default) is fine whenever max_trades_per_day is also None.

    max_trades_per_day: mirrors RiskManager.can_trade()/record_trade() -
    a shared counter across every asset, reset each time the date in
    timestamps changes, incremented by every trade (buy or sell alike),
    same as the live can_trade()/record_trade() pairing. Protective exits
    (stop-loss/take-profit) are never blocked by this cap, matching
    PLAYBOOK.md's "Per-position exit rules" (they still increment the
    counter, they're just never gated by it) - only a death-cross sell or
    a fresh buy can be skipped for being at the cap. None (default)
    disables the cap entirely, unchanged from before this parameter
    existed.

    awesome_trade_min_crossover_pct / awesome_trade_aggregate_pct: added
    2026-09-25 to backtest PLAYBOOK.md's "awesome trade" sizing override
    (see CHANGELOG.md and RISK_LIMITS). When both are set, a fresh buy
    whose SMA gap (entry_filter.crossover_strength_pct at the signal bar)
    clears awesome_trade_min_crossover_pct sizes against
    awesome_trade_aggregate_pct instead of max_aggregate_pct for that one
    allocation only - mirrors RiskManager.position_size's max_aggregate_pct
    override argument. Either left None (default) disables the override,
    unchanged from before this parameter existed.

    min_strength_pct/cooldown_bars/stop_loss_pct/take_profit_pct/
    take_profit_sell_fraction: same meaning as backtest.py's single-asset
    version, applied per-asset.

    Returns (trades, equity_curve, per_asset_final_state):
      trades - list of dicts: {index, asset, action, reason, qty, price, cash_after}
      equity_curve - total portfolio value (cash + mark-to-market of all
                      positions) at each bar
      per_asset_final_state - {asset: {"qty": ..., "avg_cost": ...}} at the
                      end of the run, for inspection
    """
    n = len(next(iter(series.values())))
    for asset, closes in series.items():
        if len(closes) != n:
            raise ValueError(f"series must be aligned: {asset} has {len(closes)} bars, expected {n}")
    if max_trades_per_day is not None and (timestamps is None or len(timestamps) != n):
        raise ValueError("max_trades_per_day requires timestamps aligned with series")

    cash = starting_cash
    state = {asset: {"qty": 0.0, "avg_cost": 0.0, "took_profit": False, "last_exit_index": None}
              for asset in series}
    trades = []
    equity_curve = []
    current_day = None
    trades_today = 0

    for i in range(n):
        if max_trades_per_day is not None:
            day = timestamps[i][:10]
            if day != current_day:
                current_day = day
                trades_today = 0
        # Protective exits (stop-loss/take-profit) run for every open
        # position first, before any death-cross or fresh-entry logic -
        # same ordering backtest.py uses for a single asset.
        for asset, closes in series.items():
            st = state[asset]
            if st["qty"] <= 0:
                continue
            price = closes[i]
            reason, fraction = check_exit(price, st["avg_cost"], st["took_profit"],
                                           stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct,
                                           take_profit_sell_fraction=take_profit_sell_fraction)
            if reason == "stop_loss":
                proceeds = st["qty"] * price
                cash += proceeds
                trades.append({"index": i, "asset": asset, "action": "sell", "reason": "stop_loss",
                                "qty": st["qty"], "price": price, "cash_after": cash})
                st["qty"] = 0.0
                st["avg_cost"] = 0.0
                st["took_profit"] = False
                st["last_exit_index"] = i
                if max_trades_per_day is not None:
                    trades_today += 1
            elif reason == "take_profit":
                sell_qty = st["qty"] * fraction
                proceeds = sell_qty * price
                cash += proceeds
                st["qty"] -= sell_qty
                st["took_profit"] = True
                trades.append({"index": i, "asset": asset, "action": "sell", "reason": "take_profit",
                                "qty": sell_qty, "price": price, "cash_after": cash})
                if max_trades_per_day is not None:
                    trades_today += 1

        open_count = sum(1 for st in state.values() if st["qty"] > 0)

        for asset, closes in series.items():
            window = closes[: i + 1]
            price = closes[i]
            st = state[asset]

            if min_strength_pct is None:
                signal = sma_crossover_signal(window, short_window, long_window)
            else:
                signal = confirmed_signal(window, short_window, long_window, min_strength_pct)

            day_cap_blocked = (
                max_trades_per_day is not None and trades_today >= max_trades_per_day
            )
            if st["qty"] > 0 and signal == "sell":
                if day_cap_blocked:
                    continue
                proceeds = st["qty"] * price
                cash += proceeds
                trades.append({"index": i, "asset": asset, "action": "sell", "reason": "death_cross",
                                "qty": st["qty"], "price": price, "cash_after": cash})
                st["qty"] = 0.0
                st["avg_cost"] = 0.0
                st["took_profit"] = False
                st["last_exit_index"] = i
                open_count -= 1
                if max_trades_per_day is not None:
                    trades_today += 1
            elif st["qty"] == 0 and cash > 0 and signal == "buy":
                if day_cap_blocked:
                    continue
                in_cooldown = (
                    cooldown_bars is not None
                    and st["last_exit_index"] is not None
                    and i - st["last_exit_index"] < cooldown_bars
                )
                cap_blocked = (
                    max_concurrent_positions is not None
                    and open_count >= max_concurrent_positions
                )
                if not in_cooldown and not cap_blocked:
                    total_open_value = sum(state[a2]["qty"] * series[a2][i] for a2 in series)
                    portfolio_value = cash + total_open_value
                    alloc = min(portfolio_value * max_position_pct, cash)
                    effective_aggregate_pct = max_aggregate_pct
                    if (awesome_trade_min_crossover_pct is not None
                            and awesome_trade_aggregate_pct is not None):
                        sma_short = _sma(window, short_window)
                        sma_long = _sma(window, long_window)
                        if (sma_short is not None and sma_long not in (None, 0)
                                and crossover_strength_pct(sma_short, sma_long) >= awesome_trade_min_crossover_pct):
                            effective_aggregate_pct = awesome_trade_aggregate_pct
                    if effective_aggregate_pct is not None:
                        remaining_aggregate = max(portfolio_value * effective_aggregate_pct - total_open_value, 0.0)
                        alloc = min(alloc, remaining_aggregate)
                    if alloc > 0:
                        qty = alloc / price
                        st["qty"] = qty
                        st["avg_cost"] = price
                        cash -= alloc
                        trades.append({"index": i, "asset": asset, "action": "buy", "reason": "fresh_buy_cross",
                                        "qty": qty, "price": price, "cash_after": cash})
                        open_count += 1
                        if max_trades_per_day is not None:
                            trades_today += 1

        total_value = cash + sum(state[a]["qty"] * series[a][i] for a in series)
        equity_curve.append(total_value)

    final_state = {asset: {"qty": st["qty"], "avg_cost": st["avg_cost"]} for asset, st in state.items()}
    return trades, equity_curve, final_state


def summarize_portfolio(trades, equity_curve, starting_cash):
    """Headline metrics for a portfolio_backtest run, plus the
    concurrency-specific metric max_concurrent_positions_held - the peak
    number of assets with an open position at the same bar, which is what
    RISK_LIMITS["max_concurrent_positions"] would have capped."""
    final_equity = equity_curve[-1] if equity_curve else starting_cash
    total_return_pct = (final_equity - starting_cash) / starting_cash * 100

    peak = starting_cash
    max_drawdown_pct = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        drawdown = (peak - e) / peak * 100
        max_drawdown_pct = max(max_drawdown_pct, drawdown)

    held = set()
    peak_concurrent = 0
    trades_by_index = {}
    for t in trades:
        trades_by_index.setdefault(t["index"], []).append(t)
    for i in range(len(equity_curve)):
        for t in trades_by_index.get(i, []):
            if t["action"] == "buy":
                held.add(t["asset"])
            elif t["action"] == "sell" and t["reason"] != "take_profit":
                held.discard(t["asset"])
        peak_concurrent = max(peak_concurrent, len(held))

    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "num_trades": len(trades),
        "max_concurrent_positions_held": peak_concurrent,
    }
