"""Tracks per-position state across cycles:

- take_profit_taken: whether the take-profit partial exit already fired
  for the current position, so exit_criteria.check_exit doesn't
  re-trigger it every cycle the price stays above the take-profit level.
- cooldown_until: an ISO timestamp before which re-entry into the asset is
  blocked, set whenever a position fully closes (stop-loss or death
  cross). Targets repeated whipsaw losses from re-entering a choppy
  market immediately after being stopped out.
- gate_blocked_since: an ISO timestamp set the first cycle
  profit_gate.blocks_sell_cross holds a fresh_sell_cross/death-cross for
  this asset instead of executing it (2026-09-28, see profit_gate.py and
  backtest_2026-09-28_gate_floor_and_tighter_stops.md). Live cycles run
  on real wall-clock time, not the backtest's bar index, so this is the
  live equivalent of backtest.py's blocked_since_index - the caller
  converts elapsed wall-clock time to hours and passes that as
  bars_since_blocked to profit_gate.gate_floor_should_force_exit (1
  cycle ~= 1 hour, same convention as DEFAULT_COOLDOWN_HOURS below).
  Only the FIRST block sets it (mirrors blocked_since_index's "if None"
  guard) - a signal blocked for several consecutive cycles keeps the
  original timestamp, not the most recent one. Cleared on recovery to
  profitability or any exit, same as the backtest.

DEFAULT_COOLDOWN_HOURS: an initial sweep against only IBIT/ETHA suggested
12h, but re-tuning against a broader 11-series set (IBIT/ETHA plus GBTC's
2018-2026 history across 6 market regimes plus 3 Solana ETFs -
backtest_2026-09-23.md's "broader backtest" and final re-tuning sections)
found 4h paired with entry_filter.DEFAULT_MIN_STRENGTH_PCT=0 to be part
of the most robust combination: helped 6/11 series (vs 5/11 for the
12h/0.25% pairing) with a much safer worst case (-10.30% vs -24.78%).

Persisted so both survive across cycles and process restarts.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_PATH = Path(__file__).parent / "position_state.json"

DEFAULT_COOLDOWN_HOURS = 4  # 1 cycle ~= 1 hour, matches backtest.py's cooldown_bars units


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

    def mark_gate_blocked(self, asset, now=None):
        """Record the first cycle profit_gate.blocks_sell_cross holds a
        sell for this asset. A no-op if already marked (mirrors
        backtest.py's blocked_since_index "if None" guard) - later calls
        for the same still-blocked position never reset the clock."""
        if self.data.get(asset, {}).get("gate_blocked_since") is not None:
            return
        now = now or datetime.now(timezone.utc)
        self.data.setdefault(asset, {})["gate_blocked_since"] = now.isoformat()
        self._save()

    def clear_gate_blocked(self, asset):
        """Call on recovery to profitability or any exit, so a future
        block for this asset starts its own fresh clock."""
        if self.data.get(asset, {}).get("gate_blocked_since") is not None:
            self.data[asset]["gate_blocked_since"] = None
            self._save()

    def hours_since_gate_blocked(self, asset, now=None):
        """Hours elapsed since mark_gate_blocked first fired for this
        asset, for profit_gate.gate_floor_should_force_exit's
        bars_since_blocked (1 cycle ~= 1 hour). None if not currently
        blocked."""
        since_str = self.data.get(asset, {}).get("gate_blocked_since")
        if since_str is None:
            return None
        now = now or datetime.now(timezone.utc)
        elapsed = now - datetime.fromisoformat(since_str)
        return elapsed.total_seconds() / 3600.0
