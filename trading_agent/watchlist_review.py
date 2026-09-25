"""Helper functions for the weekly watchlist review (see PLAYBOOK.md's
"Weekly watchlist review" section for the full procedure these feed
into). Mirrors run_cycle.py's role for the hourly cycle: cuts the
repeated token cost of work every past watchlist doc
(watchlist_2026-09-22.md, watchlist_2026-09-23_meme_removal.md,
watchlist_stocks_2026-09-23_large_cap.md) did by hand, without wrapping
the actual backtest calls - those stay bespoke Python per review, like
every prior backtest doc, since the windows/regimes genuinely differ
each time.

Two independent pieces:
- rank_by_crossover_strength: the same "how strong is today's signal"
  ranking every past watchlist construction used, for sourcing candidates
  from a broader scan universe.
- trailing_trade_pnl: a *different* question - "did this asset actually
  make or lose money for the account" - for scoring whether a *current*
  watchlist member should stay. None means the asset never traded, the
  caller's signal to fall back to a backtest instead (most of the
  watchlist, most weeks, for a narrow SMA-crossover strategy that trades
  rarely).
"""


def rank_by_crossover_strength(scan_rows, exclude=()):
    """scan_rows: the list of {"ticker": ..., "columns": {...}} dicts
    run_scan / run_cycle.py's _scan_rows() already produce. Returns rows
    sorted by |SMA10-SMA30|/SMA30 descending (same crossover_pct
    convention as scanner_signals.classify()), skipping any ticker in
    exclude (already-watchlisted names, or a topic exclusion list like
    watchlist_2026-09-23_meme_removal.md's meme/political coins) and any
    row missing SMA10/SMA30 (still warming up) or with SMA30 == 0.

    Each returned row gets one extra key, "crossover_pct", alongside its
    original columns.
    """
    ranked = []
    for row in scan_rows:
        ticker = row.get("ticker") or row.get("columns", {}).get("Symbol")
        if not ticker or ticker in exclude:
            continue
        cols = row.get("columns", {})
        try:
            sma10 = float(cols["SMA 10 (1h)"])
            sma30 = float(cols["SMA 30 (1h)"])
        except (KeyError, TypeError, ValueError):
            continue
        if sma30 == 0:
            continue
        crossover_pct = (sma10 - sma30) / sma30 * 100
        ranked.append({**row, "crossover_pct": crossover_pct})
    ranked.sort(key=lambda r: abs(r["crossover_pct"]), reverse=True)
    return ranked


def trailing_trade_pnl(asset, trade_log, current_price=None):
    """Replay trade_log for one asset (oldest first, weighted-average-
    cost accounting - same method as
    cost_basis_fallback.average_cost_basis_from_trade_log) and return
    realized + unrealized P&L in dollars.

    Returns None if this asset never appears in trade_log - the caller's
    signal to score it with a backtest instead.

    current_price prices any still-open quantity for the unrealized
    component; omit it to get realized P&L only (open quantity, if any,
    contributes nothing).
    """
    total_qty = 0.0
    total_cost = 0.0
    realized_pnl = 0.0
    traded = False

    for t in trade_log:
        if t.get("asset") != asset:
            continue
        traded = True
        qty = t["quantity"]
        price = t["price"]

        if t["side"] == "buy":
            total_cost += qty * price
            total_qty += qty
        elif t["side"] == "sell" and total_qty > 0:
            sell_qty = min(qty, total_qty)
            avg_cost = total_cost / total_qty
            realized_pnl += sell_qty * (price - avg_cost)
            total_cost -= sell_qty * avg_cost
            total_qty -= sell_qty

    if not traded:
        return None

    unrealized_pnl = 0.0
    if total_qty > 0 and current_price is not None:
        avg_cost = total_cost / total_qty
        unrealized_pnl = total_qty * (current_price - avg_cost)

    return realized_pnl + unrealized_pnl
