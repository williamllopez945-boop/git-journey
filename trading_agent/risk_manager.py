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
        """A new UTC day resets the day-scoped fields (trades_today,
        starting_equity, halted) but MUST carry trade_log forward - it's
        the durable trade history cost_basis_fallback.py and
        daily_review.py both depend on, not a daily-scoped counter.
        Discovered live (2026-09-23): a position bought one day and
        exited the next found its own cost basis unrecoverable because
        this method used to return a wholesale-fresh state (including an
        empty trade_log) on any date mismatch."""
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text())
            if state.get("date") == _today():
                return state
            return {
                "date": _today(),
                "starting_equity": None,
                "trades_today": 0,
                "halted": False,
                "trade_log": state.get("trade_log", []),
            }
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

    def position_size(self, portfolio_value, price, current_position_value=0.0, max_position_pct=None,
                       total_open_position_value=0.0, max_aggregate_pct=None):
        """Quantity of the asset that can still be bought without exceeding
        max_position_pct of the portfolio for that asset, AND without
        pushing total capital deployed across every simultaneously held
        position over max_aggregate_pct of the portfolio.

        max_position_pct: overrides RISK_LIMITS["max_position_pct"] when
        given - pass volatility_sizing.scaled_max_position_pct(...) here to
        size a volatile asset down below the flat cap. None (default) uses
        the configured flat cap, unchanged from before this parameter
        existed.

        total_open_position_value: current mark-to-market value of ALL
        open positions across the whole watchlist (including this asset's
        own existing holding, if any) - the aggregate exposure check needs
        the whole picture, not just this one asset. Defaults to 0.0
        (no other positions), unchanged from before this parameter
        existed.

        max_aggregate_pct: overrides RISK_LIMITS["max_aggregate_position_pct"]
        when given. The per-asset cap and the concurrent-positions cap
        don't reliably compose into a portfolio-wide ceiling (e.g. 15%
        per asset x 5 concurrent = 75%, well over a 50% target) - this is
        an independent, final clamp on top of the per-asset sizing, using
        current mark-to-market value (not cost basis), so it also protects
        against already-open positions appreciating past the intended
        ceiling. None (default, and no config value set) disables the
        clamp entirely, unchanged from before this parameter existed."""
        if price <= 0:
            return 0.0
        pct = max_position_pct if max_position_pct is not None else self.limits["max_position_pct"]
        max_value = portfolio_value * pct
        remaining_value = max(max_value - current_position_value, 0.0)

        agg_pct = max_aggregate_pct if max_aggregate_pct is not None else self.limits.get("max_aggregate_position_pct")
        if agg_pct is not None:
            remaining_aggregate = max(portfolio_value * agg_pct - total_open_position_value, 0.0)
            remaining_value = min(remaining_value, remaining_aggregate)

        return remaining_value / price

    def can_open_new_position(self, open_position_count):
        """Whether a fresh entry may open a NEW position - an asset the
        watchlist doesn't already hold - given how many assets currently
        have one open. Never blocks adding to (there's no scale-in in this
        strategy) or exiting an existing position, only a fresh entry into
        a previously-flat asset, same scope as the whipsaw cooldown gate.

        Gated by RISK_LIMITS["max_concurrent_positions"] (see
        portfolio_backtest.py / backtest_2026-09-23.md's concurrent-
        positions sweep): correlated watchlist assets (the meme-coin
        cluster especially) tend to fire near-duplicate signals, so
        holding many at once concentrates correlated risk and multiplies
        whipsaw losses rather than diversifying. None/absent (default)
        means uncapped, unchanged from before this gate existed."""
        max_concurrent = self.limits.get("max_concurrent_positions")
        if max_concurrent is None:
            return True
        return open_position_count < max_concurrent

    def can_auto_execute(self, order_value_usd):
        """Whether an order of this notional value may execute without
        per-trade approval, per RISK_LIMITS["auto_execute_max_usd"]."""
        return order_value_usd <= self.limits.get("auto_execute_max_usd", 0.0)

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
