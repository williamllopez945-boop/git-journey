"""Builds a rolling crypto price history locally by recording one bar per
trading cycle, since the connected MCP server exposes no crypto
historicals endpoint (only equity/index/option). Each recorded bar
corresponds to one cycle run (e.g. hourly, if the cycle is scheduled
hourly) - the SMA windows in config.py are expressed in units of cycles,
not wall-clock time."""

import json
from pathlib import Path

HISTORY_PATH = Path(__file__).parent / "price_history.json"

# Keep enough bars for the longest strategy window plus headroom, without
# growing the file unboundedly.
MAX_BARS = 500


class PriceHistoryStore:
    def __init__(self, path=HISTORY_PATH, max_bars=MAX_BARS):
        self.path = path
        self.max_bars = max_bars
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {}

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=2))

    def record(self, asset, price, timestamp):
        """Append one bar for `asset`. Skips the write if `timestamp`
        matches the most recently recorded bar, guarding against recording
        the same cycle twice."""
        bars = self.data.setdefault(asset, [])
        if bars and bars[-1]["timestamp"] == timestamp:
            return
        bars.append({"timestamp": timestamp, "price": price})
        if len(bars) > self.max_bars:
            del bars[: len(bars) - self.max_bars]
        self._save()

    def get_closes(self, asset):
        """Oldest-to-newest list of recorded prices for `asset`, ready to
        pass straight into strategy.sma_crossover_signal."""
        return [bar["price"] for bar in self.data.get(asset, [])]

    def bar_count(self, asset):
        return len(self.data.get(asset, []))
