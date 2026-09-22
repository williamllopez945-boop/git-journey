"""Static configuration for the autonomous crypto trading agent.

Edit these values to change the watchlist, strategy parameters, or risk
limits. DRY_RUN must be explicitly flipped to False to allow real orders.
"""

WATCHLIST = [
    "BTC", "ETH", "SOL", "DOGE",  # core assets
    "PEPE", "WIF", "BONK", "PENGU", "FLOKI", "XCN", "MEW", "POPCAT", "SHIB",  # top 10 screener (2026-09-22), DOGE deduped
    "PYTH", "XLM",  # added 2026-09-22 - PYTH is NOT covered by the SMA screener (see README)
]

STRATEGY = {
    # Simple moving average crossover: short SMA crossing above/below the
    # long SMA on the latest price bar generates a buy/sell signal.
    "short_window": 10,
    "long_window": 30,
}

RISK_LIMITS = {
    "max_position_pct": 0.05,       # max 5% of portfolio value held per asset
    "daily_loss_limit_pct": 0.03,   # halt all trading for the day past 3% drawdown
    "max_trades_per_day": 3,        # combined across all watchlist assets
}

# Safety default: no real orders are placed while True. Set to False only
# once the robinhood-trading MCP server is connected and authenticated with
# a live account you intend to trade on.
DRY_RUN = True
