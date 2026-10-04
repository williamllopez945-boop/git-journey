"""Resolves the marketable-limit-order price PLAYBOOK.md's order-type
policy requires (2026-09-24) for every crypto/stock order this project
places for real.

Exists because no code in this repo places orders (`run_cycle.py` only
fetches data and classifies signals - see its own docstring); every
real order is an MCP tool call made directly by the calling session
each cycle. That is exactly why the policy has lapsed twice live
(2026-09-27: CRV/DOGE/AVAX/SOL/LINK; 2026-10-04: BCH/AVAX - see
CHANGELOG.md for both) despite being written down - "remember to pick
a limit price and use type=limit" competes against the simpler,
no-price-needed `type=market` call every single cycle. Making the
correct price a single tested function call, rather than a recalled
policy, is the fix: the natural next step after calling this becomes
"place a type=limit order at this price," not "place a market order."
"""

DEFAULT_BUFFER_PCT = 0.001  # 0.1%: a buy's limit sits this far above the
                            # current ask, a sell's this far below the
                            # current bid - small enough that the order
                            # stays genuinely marketable (near-certain
                            # fill in normal liquidity, same as a plain
                            # market order) while still capping the
                            # worst-case fill price, matching PLAYBOOK.md's
                            # wording ("at or slightly above the current
                            # ask for a buy / at or slightly below the
                            # current bid for a sell").


def marketable_limit_price(side, bid, ask, buffer_pct=DEFAULT_BUFFER_PCT):
    """side: 'buy' or 'sell'. bid/ask: the current quote (get_crypto_quotes'
    bid_price/ask_price, or get_equity_quotes'/get_equity_price_book's
    equivalent fields).

    Returns the price to pass as `limit_price` on a type=limit order.
    This function has no notion of type=market - this project's policy
    is to never place one for a real crypto/stock order (see
    PLAYBOOK.md's order-type policy and the two incidents above), so
    there is nothing here to compute for that case."""
    if side == "buy":
        return ask * (1 + buffer_pct)
    if side == "sell":
        return bid * (1 - buffer_pct)
    raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
