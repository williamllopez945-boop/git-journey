"""SMA crossover signal logic. Pure computation, no network calls."""


def _sma(prices, window):
    if len(prices) < window:
        return None
    return sum(prices[-window:]) / window


def sma_crossover_signal(prices, short_window, long_window):
    """Return "buy", "sell", or "hold" for the latest bar in ``prices``.

    ``prices`` is a list of closing prices ordered oldest-to-newest,
    including the current bar as the last element. A crossover is detected
    by comparing the short/long SMA relationship between the current bar
    and the previous one.
    """
    if len(prices) < long_window + 1:
        return "hold"

    short_now = _sma(prices, short_window)
    long_now = _sma(prices, long_window)
    short_prev = _sma(prices[:-1], short_window)
    long_prev = _sma(prices[:-1], long_window)

    if None in (short_now, long_now, short_prev, long_prev):
        return "hold"

    crossed_up = short_prev <= long_prev and short_now > long_now
    crossed_down = short_prev >= long_prev and short_now < long_now

    if crossed_up:
        return "buy"
    if crossed_down:
        return "sell"
    return "hold"
