"""Tracks whether a position has already had its take-profit partial exit
taken, so exit_criteria.check_exit doesn't re-trigger it every cycle the
price stays above the take-profit level. Persisted so it survives across
cycles; reset once the position is fully closed so a future fresh entry
in the same asset can take profit again."""

import json
from pathlib import Path

STATE_PATH = Path(__file__).parent / "position_state.json"


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
        """Call once the position is fully closed (quantity back to 0) so
        a future re-entry starts fresh."""
        if asset in self.data:
            del self.data[asset]
            self._save()
