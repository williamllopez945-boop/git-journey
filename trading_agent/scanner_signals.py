"""Detects real SMA(10,30) 1h crossover events for the watchlist using the
RobinHood scanner's closeAvg (server-side, computed over real historical
candles) instead of the locally-polled price_history, which needs ~31
cycles to warm up from a cold start.

Persists each asset's last-seen bullish/bearish state so a genuine
crossover EVENT (SMA10 relative to SMA30 flipping) can be detected between
consecutive cycles, not just a bullish/bearish STATE snapshot.
"""

import json
from pathlib import Path

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


def classify(asset, sma10, sma30, pct_change, path=STATE_PATH):
    """Classify one asset's current scanner reading and update its
    persisted last-seen state.

    Returns (classification, crossover_pct) where classification is one of:
      "fresh_buy_cross"  - SMA10 just crossed above SMA30 since last check
      "fresh_sell_cross" - SMA10 just crossed below SMA30 since last check
      "excellent_watch"  - not a fresh cross, but |crossover_pct| or
                            |pct_change| clears the "worth a look" threshold
      "hold"              - nothing notable, or this is the first observation
    """
    state = _load_state(path)
    crossover_pct = (sma10 - sma30) / sma30 * 100 if sma30 else 0.0
    bullish_now = sma10 > sma30

    prev = state.get(asset)
    state[asset] = {"bullish": bullish_now, "crossover_pct": crossover_pct}
    _save_state(state, path)

    if prev is None:
        classification = "hold"
    elif prev["bullish"] != bullish_now:
        classification = "fresh_buy_cross" if bullish_now else "fresh_sell_cross"
    elif abs(crossover_pct) >= EXCELLENT_CROSSOVER_PCT or (
        pct_change is not None and abs(pct_change) >= EXCELLENT_PCT_CHANGE
    ):
        classification = "excellent_watch"
    else:
        classification = "hold"

    return classification, crossover_pct
