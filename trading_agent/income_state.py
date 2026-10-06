"""State wiring for the income sleeve (YieldMax-style weekly-distribution
basket ETFs - see PLAYBOOK.md's "Income sleeve" section).

No new state-machine class needed: unlike VOLTRAP (which forked its own
VoltrapStateStore because a cash-secured-put's lifecycle has no
crypto/stock analogue), this sleeve trades ordinary mark-to-market ETF
shares - the same shape RiskManager/PositionStateStore already model.
Both classes already accept an overridable path (risk_manager.py's
RiskManager.__init__(self, limits, state_path=...), position_state.py's
PositionStateStore.__init__(self, path=...)), so this module just wires
each to its own file, deliberately distinct from the main bot's
state.json/position_state.json - a path collision here would corrupt
the live trading bot's real state.
"""

from pathlib import Path

from .risk_manager import RiskManager
from .position_state import PositionStateStore

RISK_STATE_PATH = Path(__file__).parent / "income_risk_state.json"
POSITION_STATE_PATH = Path(__file__).parent / "income_position_state.json"


def income_risk_manager(limits):
    """limits: an INCOME_RISK_LIMITS-shaped dict (config.py)."""
    return RiskManager(limits, state_path=RISK_STATE_PATH)


def income_position_state_store():
    return PositionStateStore(path=POSITION_STATE_PATH)
