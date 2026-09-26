"""Append-only log of every cycle's non-hold classifications and the
action taken on each - not just executed trades.

RiskManager's trade_log (state.json) only records what actually
executed, so it can't answer "what did the strategy see today and what
did we do about it" - the question a genuine after-action review needs.
A signal that got blocked by the cooldown, the concurrent-positions cap,
the aggregate cap, or the volume filter, or one still sitting as an
unapproved recommendation, never shows up there at all. cycle_log.py
fills that gap: one entry per notable event, persisted to cycle_log.json
(gitignored - runtime data, same as state.json/position_state.json).

daily_review.py reads this alongside RiskManager's trade_log to build
the end-of-day summary.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent / "cycle_log.json"

# Valid `action` values for record(). Kept as a set (not an enum) to match
# this codebase's existing style (plain strings throughout scanner_signals.py
# classifications, exit_criteria.check_exit's reason strings, etc.).
ACTIONS = {
    "executed",             # a new-entry order was auto-executed
    "recommended",          # a new-entry signal exceeded auto_execute_max_usd,
                             # presented for approval instead
    "blocked_cooldown",     # fresh_buy_cross skipped - PositionStateStore().in_cooldown
    "blocked_concurrent_cap",   # fresh_buy_cross skipped - max_concurrent_positions reached
    "blocked_aggregate_cap",    # fresh_buy_cross sized to 0 - max_aggregate_position_pct reached
    "blocked_volume",       # fresh_buy_cross downgraded to hold inside classify() itself
                             # (relative_volume below DEFAULT_VOLUME_MIN_RATIO) - logged
                             # separately from the others since classify() already
                             # returned "hold", not fresh_buy_cross, for this one
    "excellent_watch",      # not a confirmed cross - alert-only, never executed
    "protective_exit",      # stop-loss or take-profit fired on an open position
}


class CycleLogStore:
    def __init__(self, path=LOG_PATH):
        self.path = path

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return []

    def _save(self, entries):
        self.path.write_text(json.dumps(entries, indent=2))

    def record(self, asset, classification, crossover_pct, action, now=None, **extra):
        """Append one entry. `extra` carries whatever's relevant to this
        action (price, quantity, notional, reason, relative_volume, etc.)
        - kept freeform rather than a fixed schema since the useful
        details differ a lot by action type."""
        entries = self._load()
        entries.append({
            "timestamp": (now or datetime.now(timezone.utc)).isoformat(),
            "asset": asset,
            "classification": classification,
            "crossover_pct": crossover_pct,
            "action": action,
            **extra,
        })
        self._save(entries)

    def entries_for_date(self, date_iso):
        """All entries whose timestamp date (UTC) matches date_iso
        (YYYY-MM-DD) - the same UTC-day boundary RiskManager's
        trades_today counter uses."""
        return [e for e in self._load() if e["timestamp"][:10] == date_iso]
