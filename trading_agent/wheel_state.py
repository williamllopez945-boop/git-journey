"""Per-symbol state machine for the options wheel strategy (cash-secured
puts -> covered calls, see PLAYBOOK.md's "Options wheel strategy"
section for the full weekly/daily procedure this feeds into).

    idle -> csp_open -> [expires OTM] -> idle (keep premium)
                     -> [assigned]    -> holding_shares
    holding_shares -> covered_call_open -> [expires OTM] -> holding_shares
                                         -> [called away]  -> idle

Mirrors position_state.py's persisted-JSON-store pattern, but tracks a
richer per-symbol record (state, live option details, running P&L)
since a wheel position spans weeks and multiple contracts rather than
one crypto/stock position's simpler take-profit-flag/cooldown pair.

Deliberately independent of RiskManager/PositionStateStore: a CSP's
risk is reserved cash collateral, not a mark-to-market position, and has
no crypto/stock analogue - see PLAYBOOK.md's "Options wheel strategy"
section for why this stays a separate system.
"""

import json
from pathlib import Path

STATE_PATH = Path(__file__).parent / "wheel_state.json"

IDLE = "idle"
CSP_OPEN = "csp_open"
HOLDING_SHARES = "holding_shares"
COVERED_CALL_OPEN = "covered_call_open"


def next_state_after_csp_expiration(assigned):
    """A csp_open position's expiration resolves to holding_shares if
    assigned, idle (premium kept, nothing else changes) otherwise."""
    return HOLDING_SHARES if assigned else IDLE


def next_state_after_covered_call_expiration(called_away):
    """A covered_call_open position's expiration resolves to idle if the
    shares were called away, back to holding_shares (sell another call
    next cycle) otherwise."""
    return IDLE if called_away else HOLDING_SHARES


class WheelStateStore:
    def __init__(self, path=STATE_PATH):
        self.path = path
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {}

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=2))

    def state(self, symbol):
        return self.data.get(symbol, {}).get("state", IDLE)

    def record(self, symbol):
        return self.data.get(symbol, {})

    def open_csp(self, symbol, option_id, strike, expiration, premium_collected, quantity):
        self.data[symbol] = {
            "state": CSP_OPEN,
            "option_id": option_id,
            "strike": strike,
            "expiration": expiration,
            "premium_collected": premium_collected,
            "quantity": quantity,
        }
        self._save()

    def resolve_csp(self, symbol, assigned, cost_basis=None):
        """Call once a csp_open contract's expiration is known. assigned=True
        requires cost_basis (per-share cost floor for the eventual covered
        call: strike - premium collected per share)."""
        rec = self.data.setdefault(symbol, {})
        prior_premium = rec.get("premium_collected", 0.0)
        if assigned:
            rec["state"] = HOLDING_SHARES
            rec["cost_basis"] = cost_basis
            rec["premium_collected"] = prior_premium
        else:
            rec.clear()
            rec["state"] = IDLE
        self._save()

    def open_covered_call(self, symbol, option_id, strike, expiration, premium_collected, quantity):
        rec = self.data.setdefault(symbol, {})
        rec["state"] = COVERED_CALL_OPEN
        rec["option_id"] = option_id
        rec["strike"] = strike
        rec["expiration"] = expiration
        rec["quantity"] = quantity
        rec["premium_collected"] = rec.get("premium_collected", 0.0) + premium_collected
        self._save()

    def resolve_covered_call(self, symbol, called_away):
        rec = self.data.setdefault(symbol, {})
        if called_away:
            rec.clear()
            rec["state"] = IDLE
        else:
            rec["state"] = HOLDING_SHARES
            for key in ("option_id", "strike", "expiration"):
                rec.pop(key, None)
        self._save()
