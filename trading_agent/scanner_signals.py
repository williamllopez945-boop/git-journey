"""Detects real SMA(10,30) 1h crossover events for the watchlist using the
RobinHood scanner's closeAvg (server-side, computed over real historical
candles) instead of the locally-polled price_history, which needs ~31
cycles to warm up from a cold start.

Persists each asset's last-seen bullish/bearish state so a genuine
crossover EVENT (SMA10 relative to SMA30 flipping) can be detected between
consecutive cycles, not just a bullish/bearish STATE snapshot.

A crossover is confirmed one cycle after it's first detected (the
"pending" state below), then only classified as fresh_buy_cross /
fresh_sell_cross if the state still holds AND the gap clears
min_strength_pct - the same 1-bar-persistence-plus-strength design as
entry_filter.py, adapted to this module's cycle-by-cycle persisted-state
architecture (which doesn't have direct access to a price history array
to re-derive it from). See entry_filter.py's docstring for why a strength
check exactly at the crossing instant doesn't work, and
backtest_2026-09-23.md for the empirical tuning behind the default
threshold.

A confirmed fresh_buy_cross is additionally gated by relative_volume, the
scan's "Relative volume" column (volume(1h,1)/volumeAvg(14,1h) - the most
recent hour's volume over its own 14-hour average, real crypto data from
the scanner, not an equity proxy). Blocks only an unconvincing, low-volume
breakout; never applies to fresh_sell_cross or any other classification.
See volume_filter.py and backtest_2026-09-23.md's "Volume entry
confirmation filter" section for the backtested threshold (against
equity/ETF proxy volume, since crypto still has no historicals source).
"""

import json
from pathlib import Path

from .entry_filter import DEFAULT_MIN_STRENGTH_PCT
from .volume_filter import DEFAULT_VOLUME_MIN_RATIO

STATE_PATH = Path(__file__).parent / "scanner_state.json"

# Thresholds for flagging a non-crossover signal as worth a human look.
EXCELLENT_CROSSOVER_PCT = 5.0   # |SMA10-SMA30| / SMA30 * 100
EXCELLENT_PCT_CHANGE = 0.05     # fractional move from prior close (5%)


def _load_state(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_state(state, path):
    path.write_text(json.dumps(state, indent=2))


def classify(asset, sma10, sma30, pct_change, path=STATE_PATH, min_strength_pct=DEFAULT_MIN_STRENGTH_PCT,
             relative_volume=None, min_volume_ratio=DEFAULT_VOLUME_MIN_RATIO):
    """Classify one asset's current scanner reading and update its
    persisted last-seen state.

    relative_volume: the scan's "Relative volume" column value for this
    asset this cycle (None if not fetched, e.g. an older scan config -
    disables the volume gate entirely, same as omitting min_strength_pct
    would for the strength check). When given, a confirmed buy cross is
    downgraded to "hold" if relative_volume < min_volume_ratio - an
    unconvincing, low-volume breakout. Never applies to a sell cross or
    any other classification.

    Returns (classification, crossover_pct) where classification is one of:
      "fresh_buy_cross"  - SMA10 crossed above SMA30 last cycle, still
                            holds this cycle, the gap clears
                            min_strength_pct, and volume clears
                            min_volume_ratio (when relative_volume is given)
      "fresh_sell_cross" - the same, crossed below (never volume-gated)
      "excellent_watch"  - not a confirmed cross, but |crossover_pct| or
                            |pct_change| clears the "worth a look" threshold
      "hold"              - nothing notable, the first observation for this
                            asset, a crossover just detected this cycle
                            (pending confirmation next cycle), a crossover
                            that persisted but didn't clear min_strength_pct,
                            or a confirmed buy cross blocked by low volume
    """
    state = _load_state(path)
    crossover_pct = (sma10 - sma30) / sma30 * 100 if sma30 else 0.0
    bullish_now = sma10 > sma30

    prev = state.get(asset)

    if prev is None:
        classification = "hold"
        new_state = {"bullish": bullish_now, "crossover_pct": crossover_pct, "pending": False}
    elif prev["bullish"] != bullish_now:
        # Cross just happened this cycle - hold for one more cycle to confirm
        # it isn't an immediate whipsaw, per entry_filter.py's design.
        classification = "hold"
        new_state = {"bullish": bullish_now, "crossover_pct": crossover_pct, "pending": True}
    elif prev.get("pending"):
        # State held for a second consecutive cycle since the flip - confirm
        # if the gap has grown enough to clear the strength threshold.
        if abs(crossover_pct) >= min_strength_pct:
            classification = "fresh_buy_cross" if bullish_now else "fresh_sell_cross"
            if (
                classification == "fresh_buy_cross"
                and relative_volume is not None
                and relative_volume < min_volume_ratio
            ):
                classification = "hold"
        else:
            classification = "hold"
        new_state = {"bullish": bullish_now, "crossover_pct": crossover_pct, "pending": False}
    else:
        if abs(crossover_pct) >= EXCELLENT_CROSSOVER_PCT or (
            pct_change is not None and abs(pct_change) >= EXCELLENT_PCT_CHANGE
        ):
            classification = "excellent_watch"
        else:
            classification = "hold"
        new_state = {"bullish": bullish_now, "crossover_pct": crossover_pct, "pending": False}

    state[asset] = new_state
    _save_state(state, path)

    return classification, crossover_pct
