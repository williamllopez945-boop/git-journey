"""Tracks per-position state across cycles:

- take_profit_taken: whether the take-profit partial exit already fired
  for the current position, so exit_criteria.check_exit doesn't
  re-trigger it every cycle the price stays above the take-profit level.
- cooldown_until: an ISO timestamp before which re-entry into the asset is
  blocked, set whenever a position fully closes (stop-loss or death
  cross). Targets repeated whipsaw losses from re-entering a choppy
  market immediately after being stopped out - tuned empirically (12h) by
  sweeping backtest.py's cooldown_bars against real IBIT/ETHA data, see
  backtest_2026-09-23.md.

Persisted so both survive across cycles and process restarts.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_PATH = Path(__file__).parent / "position_state.json"

DEFAULT_COOLDOWN_HOURS = 12  # 1 cycle ~= 1 hour, matches backtest.py's cooldown_bars units


class PositionStateStore:
    def __init__(self, path=STATE_PATH):
        self.path = path
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {}

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=2))

    def took_profit(self, asset):
        return self.data.get(asset, {}).get("take_profit_taken", False)

    def mark_took_profit(self, asset):
        self.data.setdefault(asset, {})["take_profit_taken"] = True
        self._save()

    def reset(self, asset):
        """Call once a position is fully closed, so a future re-entry
        starts without a stale take-profit flag. Cooldown (set separately
        via record_exit) is untouched - it's tracked independently and
        must survive this reset in order to actually block re-entry."""
        if asset in self.data:
            self.data[asset]["take_profit_taken"] = False
            self._save()

    def record_exit(self, asset, cooldown_hours=DEFAULT_COOLDOWN_HOURS, now=None):
        """Call whenever a position fully closes (stop-loss or death
        cross) to start the re-entry cooldown."""
        now = now or datetime.now(timezone.utc)
        until = now + timedelta(hours=cooldown_hours)
        self.data.setdefault(asset, {})["cooldown_until"] = until.isoformat()
        self._save()

    def in_cooldown(self, asset, now=None):
        until_str = self.data.get(asset, {}).get("cooldown_until")
        if until_str is None:
            return False
        now = now or datetime.now(timezone.utc)
        return now < datetime.fromisoformat(until_str)
