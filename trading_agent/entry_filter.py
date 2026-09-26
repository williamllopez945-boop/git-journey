"""Entry confirmation filter: only treats an SMA crossover as tradeable
once the new bullish/bearish state has held for one bar past the cross
(not reversed immediately) and the SMA gap has grown to a minimum
strength by then. This targets the whipsaw losses found in
backtest_2026-09-23.md - most losing round trips came from crosses that
reversed within a bar or two.

A strength check exactly AT the crossing bar does not work - confirmed
empirically (see backtest_2026-09-23.md's follow-up sweep): the two SMAs
are approximately equal by definition at the instant of crossing, so any
meaningful strength threshold rejects nearly every real cross, not just
noisy ones. Checking one bar later, after the gap has had a chance to
develop, is what actually distinguishes a persisting move from a
whipsaw - this trades one bar of entry lag for that filtering.

DEFAULT_MIN_STRENGTH_PCT: an initial sweep against only IBIT/ETHA (one
6-month trending window) suggested 0.25%, but a broader sweep against 11
independent series - IBIT/ETHA plus GBTC's 2018-2026 history split into 6
market regimes, plus 3 Solana ETFs (backtest_2026-09-23.md's "broader
backtest" and final re-tuning sections) - showed that value helped only
5/11 series and hurt 6/11, including some large losses (worst -24.78%
delta vs raw). Re-tuned against the full 11-series set: 0% (persistence
check only, no strength requirement) was part of the best robust
combination found (paired with position_state.DEFAULT_COOLDOWN_HOURS),
helping 6/11 series with a much safer worst case (-10.30%). A strength
requirement was not part of the best robust setting on this wider
sample - persistence alone captured the generalizable edge.
"""

from .strategy import sma_crossover_signal

DEFAULT_MIN_STRENGTH_PCT = 0


def _sma(prices, window):
    if len(prices) < window:
        return None
    return sum(prices[-window:]) / window


def crossover_strength_pct(sma_short, sma_long):
    """|short - long| / long * 100. Precondition: sma_long != 0."""
    return abs(sma_short - sma_long) / sma_long * 100


def passes_threshold(sma_short, sma_long, min_strength_pct):
    if sma_long == 0:
        return False
    return crossover_strength_pct(sma_short, sma_long) >= min_strength_pct


def confirmed_signal(prices, short_window, long_window, min_strength_pct=DEFAULT_MIN_STRENGTH_PCT):
    """Wraps strategy.sma_crossover_signal with a 1-bar confirmation delay
    plus an optional strength check, evaluated one bar after the cross.

    Returns "buy" or "sell" only when: a crossover fired on the PREVIOUS
    bar, the resulting state still holds on the current bar (hasn't
    reversed), and the current gap clears min_strength_pct (0 disables the
    strength check, keeping only the persistence check). Otherwise "hold".
    """
    if len(prices) < 2:
        return "hold"

    prev_signal = sma_crossover_signal(prices[:-1], short_window, long_window)
    if prev_signal == "hold":
        return "hold"

    sma_short = _sma(prices, short_window)
    sma_long = _sma(prices, long_window)
    if sma_short is None or sma_long is None or sma_long == 0:
        return "hold"

    still_bullish = sma_short > sma_long
    if prev_signal == "buy" and not still_bullish:
        return "hold"
    if prev_signal == "sell" and still_bullish:
        return "hold"

    if min_strength_pct > 0 and not passes_threshold(sma_short, sma_long, min_strength_pct):
        return "hold"

    return prev_signal
