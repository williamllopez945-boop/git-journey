"""Volume-surge confirmation gate for the income sleeve (see
PLAYBOOK.md's "Income sleeve" section).

Owner request (2026-10-13): confirm a dip-buy signal with a check for
"where institutional money will enter." Robinhood's API has no real
order-flow/dark-pool/block-trade data, so this uses the closest
available proxy: a heavier-than-normal trading volume on the dip day
itself. The reasoning: ordinary daily noise doesn't move much volume,
but a price dropping into the bottom of its range on volume well above
the recent average is more consistent with a real capitulation/
accumulation event (someone meaningfully sized stepping in or out) than
a quiet drift down. This is a proxy and a label, not a claim about real
institutional activity.

An earlier version of this module gated on distance from a trailing
volume-weighted average price (VWAP) instead - see
backtest_2026-10-13_institutional_flow_income_sleeve.md's "first
attempt" section for why that was replaced: being in the bottom 10% of
a 20-day range is close to definitionally below that same window's
volume-weighted average, so it never actually blocked anything (0 of
~790 dip_buy bars across 8 real symbols). The relative-volume version
below does discriminate (blocks roughly 80-90% of raw dip_buy bars
across the same 8 symbols) and is the one actually backtested for a
go/no-go decision.

Mirrors income_signals.py's style - module constants, plain functions,
no classes.
"""

VOLUME_LOOKBACK_DAYS = 20   # same window as income_signals.DIP_LOOKBACK_DAYS,
                             # for a like-for-like comparison.
VOLUME_SURGE_MULTIPLE = 1.5 # today's volume must be at least 1.5x the
                             # trailing lookback-day average (today excluded).


def average_trailing_volume(volumes, lookback_days=VOLUME_LOOKBACK_DAYS):
    """volumes: oldest-to-newest daily volumes for one symbol, today's
    volume last.

    Returns the mean volume over the lookback_days bars immediately
    BEFORE today (today excluded, so today's own volume can be compared
    against a baseline it didn't contribute to).

    None if fewer than lookback_days+1 bars are available, or if the
    trailing average is zero (no trading history to compare against).
    """
    if len(volumes) <= lookback_days:
        return None

    trailing = volumes[-lookback_days - 1:-1]
    avg = sum(trailing) / lookback_days
    if avg <= 0:
        return None
    return avg


def volume_surge_confirmed(volumes, lookback_days=VOLUME_LOOKBACK_DAYS,
                            surge_multiple=VOLUME_SURGE_MULTIPLE):
    """True if today's volume is at least surge_multiple times the
    trailing lookback_days average volume (today excluded) - read as a
    proxy for unusually heavy participation on the dip, standing in for
    "institutional money entering" since no real order-flow data is
    available. False if volume is merely ordinary, or not yet warmed up
    (never blocks by raising - just returns False, same fail-open-to-
    "no confirmation yet" posture as classify_dip's None case).
    """
    avg = average_trailing_volume(volumes, lookback_days=lookback_days)
    if avg is None:
        return False

    today_volume = volumes[-1]
    return today_volume >= avg * surge_multiple
