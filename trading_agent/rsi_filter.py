"""RSI entry confirmation filter: blocks a fresh buy entry when RSI (a
momentum oscillator, 0-100) shows the move is already overbought - likely
extended and due to mean-revert, rather than the start of a fresh trend.

Scope, same as the whipsaw cooldown and concurrent-positions cap: only
ever blocks a NEW entry (a "buy" signal into a previously-flat asset). It
never blocks a sell/death-cross or a protective exit - those reduce risk
and are never held back by an entry-side filter.

Uses a simple (non-Wilder-smoothed) RSI over the last `period` changes,
matching this codebase's existing simple-average SMA (strategy.py's
`_sma` is a plain mean, not exponential either) rather than introducing a
different smoothing convention for one indicator.
"""

DEFAULT_RSI_PERIOD = 14
DEFAULT_RSI_OVERBOUGHT_PCT = 70


def rsi(prices, period=DEFAULT_RSI_PERIOD):
    """Latest RSI value (0-100) from the last `period` price changes, or
    None if there isn't enough history yet (needs period+1 prices)."""
    if len(prices) < period + 1:
        return None

    changes = [prices[i] - prices[i - 1] for i in range(len(prices) - period, len(prices))]
    gains = [c for c in changes if c > 0]
    losses = [-c for c in changes if c < 0]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def passes_rsi_filter(prices, period=DEFAULT_RSI_PERIOD, overbought_pct=DEFAULT_RSI_OVERBOUGHT_PCT):
    """Whether a fresh buy entry should proceed: True when RSI can't be
    computed yet (don't block warm-up - the other entry gates already
    handle insufficient history) or is below the overbought threshold."""
    value = rsi(prices, period)
    if value is None:
        return True
    return value < overbought_pct
