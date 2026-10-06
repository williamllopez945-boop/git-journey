"""Candidate screening for the income sleeve (YieldMax-style
weekly-distribution basket ETFs - see PLAYBOOK.md's "Income sleeve"
section). Mirrors voltrap_candidates.py's role: pure functions that cut
the repeated filtering work out of a live cycle, without wrapping the
live quote call itself (spreads move; always re-check against a fresh
get_equity_quotes call, never trust a stored snapshot).

Liquidity matters more than usual here: these are thinly-traded, newer
ETFs, and a wide or crossed bid-ask spread means real slippage on any
fill. filter_by_liquidity fails closed - any row with a missing,
non-positive, or crossed quote is dropped, not passed through with a
guess.
"""

DEFAULT_MAX_SPREAD_PCT = 0.02


def spread_pct(bid_price, ask_price):
    """(ask - bid) / mid. None if either price is missing/non-positive,
    or the quote is crossed (bid >= ask - a stale or broken quote, never
    a real tradeable spread)."""
    if bid_price is None or ask_price is None:
        return None
    if bid_price <= 0 or ask_price <= 0:
        return None
    if bid_price >= ask_price:
        return None

    mid = (bid_price + ask_price) / 2
    return (ask_price - bid_price) / mid


def filter_by_liquidity(quotes, max_spread_pct=DEFAULT_MAX_SPREAD_PCT):
    """quotes: [{"symbol": ..., "bid_price": ..., "ask_price": ...}, ...]
    (get_equity_quotes result shape, already unpacked to plain numbers).

    Returns the survivors (spread_pct <= max_spread_pct) with "spread_pct"
    attached to each row, sorted tightest-spread-first. Any row whose
    spread_pct comes back None (missing/non-positive/crossed quote) is
    dropped, never passed through.
    """
    survivors = []
    for row in quotes:
        pct = spread_pct(row.get("bid_price"), row.get("ask_price"))
        if pct is None or pct > max_spread_pct:
            continue
        survivors.append({**row, "spread_pct": pct})

    survivors.sort(key=lambda row: row["spread_pct"])
    return survivors
