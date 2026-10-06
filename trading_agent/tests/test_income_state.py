import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent import income_state
from trading_agent.risk_manager import RiskManager
from trading_agent.position_state import PositionStateStore
from trading_agent import risk_manager as risk_manager_module
from trading_agent import position_state as position_state_module


def test_income_risk_manager_uses_its_own_state_path(tmp_path, monkeypatch):
    own_path = tmp_path / "income_risk_state.json"
    monkeypatch.setattr(income_state, "RISK_STATE_PATH", own_path)

    rm = income_state.income_risk_manager({"max_trades_per_day": 2})

    assert isinstance(rm, RiskManager)
    assert rm.state_path == own_path
    assert rm.state_path != risk_manager_module.STATE_PATH


def test_income_position_state_store_uses_its_own_path(tmp_path, monkeypatch):
    own_path = tmp_path / "income_position_state.json"
    monkeypatch.setattr(income_state, "POSITION_STATE_PATH", own_path)

    store = income_state.income_position_state_store()

    assert isinstance(store, PositionStateStore)
    assert store.path == own_path
    assert store.path != position_state_module.STATE_PATH


def test_default_paths_are_distinct_from_main_bot_state():
    # Guards against a path collision that would corrupt the live bot's
    # real state.json / position_state.json.
    assert income_state.RISK_STATE_PATH != risk_manager_module.STATE_PATH
    assert income_state.POSITION_STATE_PATH != position_state_module.STATE_PATH
    assert income_state.RISK_STATE_PATH.name == "income_risk_state.json"
    assert income_state.POSITION_STATE_PATH.name == "income_position_state.json"
