"""Entry signal for the income sleeve (YieldMax-style weekly-distribution
basket ETFs - see PLAYBOOK.md's "Income sleeve" section).

Deliberately NOT scanner_signals.classify's SMA(10,30) crossover: these
ETFs are a weekly-income base, not a trend-following trade - the owner's
explicit goal is buying as low as possible within a recent range, not
following a crossover. This is a rolling-range-position ("Donchian %B")
signal instead: where today's close sits between the trailing high and
low. Mirrors equity_signals.py's style - module constants, plain
functions, no classes, asset-class-agnostic (any symbol's closes work).
"""

DIP_LOOKBACK_DAYS = 20     # ~1 trading month; short enough that even a
                           # 2025-inception ETF warms up within weeks.
DIP_ENTRY_THRESHOLD = 0.10 # bottom 10% of the trailing range counts as a
                           # dip. Proposed, not backtested against
                           # comparable-depth history - see
                           # income_backtest.py's limitation note.

SUPPORT_LOOKBACK_DAYS = 60   # ~3 trading months - a longer horizon than
                             # DIP_LOOKBACK_DAYS on purpose: this checks
                             # proximity to an actual support level, not
                             # just where today sits in a short window.
SUPPORT_TOLERANCE_PCT = 0.03 # today's close must be within 3% of the
                             # trailing support level to count as "near
                             # support" (2026-10-16 owner request - "good
                             # low with good support zones," not just a
                             # rolling-range percentile).


def rolling_range_position(closes, lookback_days=DIP_LOOKBACK_DAYS):
    """closes: oldest-to-newest daily close prices for one symbol, today's
    close last.

    Returns (today_close - trailing_low) / (trailing_high - trailing_low)
    over the trailing lookback_days closes (today inclusive): 0.0 means
    today's close is the window's low, 1.0 means it's the window's high.

    None if fewer than lookback_days closes are available (not warmed up
    yet), or if the window is flat (high == low - no range to position
    within).
    """
    if len(closes) < lookback_days:
        return None

    window = closes[-lookback_days:]
    low = min(window)
    high = max(window)
    if high == low:
        return None

    return (window[-1] - low) / (high - low)


def classify_dip(closes, lookback_days=DIP_LOOKBACK_DAYS, entry_threshold=DIP_ENTRY_THRESHOLD):
    """"dip_buy" if today's close is within the bottom entry_threshold
    fraction of its trailing lookback_days range, else "hold" - including
    the warm-up/flat-window None case: never blocks, just doesn't signal.
    """
    position = rolling_range_position(closes, lookback_days=lookback_days)
    if position is None:
        return "hold"
    if position <= entry_threshold:
        return "dip_buy"
    return "hold"


def near_support(closes, lookback_days=SUPPORT_LOOKBACK_DAYS, tolerance_pct=SUPPORT_TOLERANCE_PCT):
    """closes: oldest-to-newest daily close prices for one symbol, today's
    close last.

    True if today's close is within tolerance_pct of the lowest close
    over the trailing lookback_days (today inclusive) - a real support
    level over a longer horizon, independent of classify_dip's shorter
    20-day percentile read. None if fewer than lookback_days closes are
    available yet (not warmed up) - the caller decides how to treat that,
    same convention as rolling_range_position's None.
    """
    if len(closes) < lookback_days:
        return None

    window = closes[-lookback_days:]
    support_level = min(window)
    if support_level <= 0:
        return None

    return (window[-1] - support_level) / support_level <= tolerance_pct


def classify_entry(closes, lookback_days=DIP_LOOKBACK_DAYS, entry_threshold=DIP_ENTRY_THRESHOLD,
                    support_lookback_days=SUPPORT_LOOKBACK_DAYS, support_tolerance_pct=SUPPORT_TOLERANCE_PCT):
    """"dip_buy" only when BOTH classify_dip's short-range percentile read
    AND near_support's longer-range support-level check agree - two
    independent confirmations of "a good low," not just one (2026-10-16
    owner request, replacing classify_dip alone as the live entry signal).

    Falls back to "hold" if near_support can't be computed yet (fewer
    than support_lookback_days bars) - a dip signal with no support
    confirmation available is treated the same as no confirmation at
    all, not a free pass.
    """
    if classify_dip(closes, lookback_days=lookback_days, entry_threshold=entry_threshold) != "dip_buy":
        return "hold"
    if near_support(closes, lookback_days=support_lookback_days, tolerance_pct=support_tolerance_pct):
        return "dip_buy"
    return "hold"
