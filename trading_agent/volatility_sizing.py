"""Volatility-aware position sizing: scales down the max-position-pct cap
for higher-volatility assets relative to a benchmark, so a highly
volatile asset (e.g. a meme coin) doesn't get the same dollar allocation
as a comparatively stable one (e.g. BTC) under the flat
RISK_LIMITS["max_position_pct"] cap.

Deliberately never scales UP above the base cap for assets less volatile
than the benchmark - increasing total capital deployed to "make up for"
low volatility would raise aggregate portfolio risk, not just rebalance
it. This only ever reduces exposure to assets riskier than the benchmark.

Scope note: this scales the SIZE of an individual position given its own
volatility. It does not model correlation across simultaneously-held
positions (e.g. several meme coins moving together) - that would need a
true multi-asset portfolio backtester, a materially larger undertaking
than the single-asset backtest.py this was validated against. See
backtest_2026-09-23.md for how the volatility measurement itself was
checked against real market data.
"""


def realized_volatility(prices):
    """Sample stdev of period-over-period % returns across a price series.
    Same units as crossover_pct etc (percentage, not fraction) - e.g. 2.5
    means a typical bar-to-bar move of about 2.5%. Returns None when there
    isn't enough data (fewer than 3 prices) to compute a meaningful stdev.
    """
    if len(prices) < 3:
        return None

    returns = [
        (prices[i] - prices[i - 1]) / prices[i - 1] * 100
        for i in range(1, len(prices))
        if prices[i - 1] != 0
    ]
    if len(returns) < 2:
        return None

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return variance ** 0.5


def scaled_max_position_pct(asset_volatility, benchmark_volatility, base_max_position_pct):
    """Max-position-pct cap for an asset, scaled down (never up) by how
    much more volatile it is than the benchmark. An asset exactly as
    volatile as the benchmark, or less volatile, gets the full
    base_max_position_pct; an asset twice as volatile gets half, etc.
    """
    if (
        asset_volatility is None
        or benchmark_volatility is None
        or asset_volatility <= 0
        or benchmark_volatility <= 0
    ):
        return base_max_position_pct

    scale = min(1.0, benchmark_volatility / asset_volatility)
    return base_max_position_pct * scale
