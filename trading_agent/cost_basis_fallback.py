"""Fallback average cost basis computed from RiskManager's local
trade_log, for when get_crypto_positions' own cost_bases field reports a
zero direct_cost_basis/direct_quantity despite a real, held quantity -
an observed gap where Robinhood's cost-basis ledger doesn't reflect a
normally-filled direct purchase (the PEPE position bought 2026-09-22
still showed this a full day later: a single, clean, agentic-initiated
market buy, fully filled, yet cost_bases stayed at 0/0). This is a gap
in the account's own cost-basis data, not something get_crypto_positions'
own "transfers/rewards/forks" caveat covers - there's no transfer,
reward, or fork here.

Only a fallback: PLAYBOOK.md always tries get_crypto_positions' own cost
basis first (see get_crypto_positions's own guidance on when its average
only covers a subset of units) and only falls back to this when that
reports a zero direct_quantity for an asset currently held.
"""


def average_cost_basis_from_trade_log(asset, trade_log):
    """Replay trade_log's buy/sell entries for one asset, oldest first,
    maintaining a running average-cost ledger - the same method
    get_crypto_positions' own direct_cost_basis/direct_quantity fields
    compute: a buy adds to the weighted average; a sell reduces the open
    quantity proportionally without changing the average (the standard
    average-cost accounting method).

    trade_log: RiskManager.state["trade_log"] (or any list of dicts with
    "asset"/"side"/"quantity"/"price" keys) - already oldest-first, as
    RiskManager appends it.

    Returns the average cost basis (cost per unit) for whatever quantity
    this local record shows as currently open for `asset`, or None if it
    shows no open quantity (never bought, or fully exited per these
    records) - callers should keep using get_crypto_positions' figure (or
    treat cost basis as unavailable) in that case, not assume zero.
    """
    total_qty = 0.0
    total_cost = 0.0

    for t in trade_log:
        if t.get("asset") != asset:
            continue
        qty = t["quantity"]
        price = t["price"]

        if t["side"] == "buy":
            total_cost += qty * price
            total_qty += qty
        elif t["side"] == "sell" and total_qty > 0:
            sell_qty = min(qty, total_qty)
            total_cost -= (sell_qty / total_qty) * total_cost
            total_qty -= sell_qty

    if total_qty <= 0:
        return None
    return total_cost / total_qty
