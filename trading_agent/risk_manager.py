"""Enforces the conservative risk limits for autonomous trading:
per-trade position sizing, a daily-loss circuit breaker, and a daily trade
cap. State is persisted to disk so limits hold across process restarts and
across the scheduled cycles that drive the agent."""

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).parent / "state.json"


def _today():
    return datetime.now(timezone.utc).date().isoformat()


class RiskManager:
    def __init__(self, limits, state_path=STATE_PATH):
        self.limits = limits
        self.state_path = state_path
        self.state = self._load_or_init_state()

    def _load_or_init_state(self):
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text())
            if state.get("date") == _today():
                return state
        return {
            "date": _today(),
            "starting_equity": None,
            "trades_today": 0,
            "halted": False,
            "trade_log": [],
        }

    def _save(self):
        self.state_path.write_text(json.dumps(self.state, indent=2))

    def start_of_day(self, equity):
        """Record the day's starting portfolio equity, once per UTC day."""
        if self.state["starting_equity"] is None:
            self.state["starting_equity"] = equity
            self._save()

    def check_circuit_breaker(self, current_equity):
        """Halt trading for the rest of the day once drawdown from the
        day's starting equity reaches the configured limit."""
        start = self.state["starting_equity"]
        if start is None or start <= 0:
            return self.state["halted"]
        drawdown_pct = (start - current_equity) / start
        if drawdown_pct >= self.limits["daily_loss_limit_pct"]:
            self.state["halted"] = True
            self._save()
        return self.state["halted"]

    def can_trade(self):
        if self.state["halted"]:
            return False
        return self.state["trades_today"] < self.limits["max_trades_per_day"]

    def position_size(self, portfolio_value, price, current_position_value=0.0):
        """Quantity of the asset that can still be bought without exceeding
        max_position_pct of the portfolio for that asset."""
        if price <= 0:
            return 0.0
        max_value = portfolio_value * self.limits["max_position_pct"]
        remaining_value = max(max_value - current_position_value, 0.0)
        return remaining_value / price

    def record_trade(self, asset, side, quantity, price):
        self.state["trades_today"] += 1
        self.state["trade_log"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "asset": asset,
            "side": side,
            "quantity": quantity,
            "price": price,
        })
        self._save()
