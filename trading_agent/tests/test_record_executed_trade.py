import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "trading_agent" / "record_executed_trade.py"


def _run(args, risk_state_path, cycle_log_path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args,
         "--risk-state-path", str(risk_state_path),
         "--cycle-log-path", str(cycle_log_path)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


def _seed_risk_state(path, trades_today=0):
    today = datetime.now(timezone.utc).date().isoformat()
    path.write_text(json.dumps({
        "date": today, "starting_equity": 1000.0, "trades_today": trades_today,
        "halted": False, "trade_log": [],
    }))


def test_ordinary_fresh_entry_records_trade_and_consumes_a_trade_slot():
    with tempfile.TemporaryDirectory() as tmp:
        risk_state_path = Path(tmp) / "state.json"
        cycle_log_path = Path(tmp) / "cycle_log.json"
        _seed_risk_state(risk_state_path)

        result = _run(
            ["--asset", "AVAX", "--side", "buy", "--quantity", "7.9511", "--price", "11.560665",
             "--classification", "fresh_buy_cross", "--crossover-pct", "1.7211",
             "--notional", "91.92", "--order-id", "6abb8587-7a90-4230-8127-ad18b8e59b4a"],
            risk_state_path, cycle_log_path,
        )
        assert result.returncode == 0, result.stderr
        assert "trades_today: 0 -> 1" in result.stdout

        state = json.loads(risk_state_path.read_text())
        assert state["trades_today"] == 1
        assert len(state["trade_log"]) == 1
        entry = state["trade_log"][0]
        assert entry["asset"] == "AVAX"
        assert entry["side"] == "buy"
        assert entry["quantity"] == 7.9511
        assert entry["price"] == 11.560665

        cycle_log = json.loads(cycle_log_path.read_text())
        assert len(cycle_log) == 1
        assert cycle_log[0]["asset"] == "AVAX"
        assert cycle_log[0]["classification"] == "fresh_buy_cross"
        assert cycle_log[0]["action"] == "executed"
        assert cycle_log[0]["order_id"] == "6abb8587-7a90-4230-8127-ad18b8e59b4a"


def test_protective_exit_does_not_consume_a_trade_slot():
    with tempfile.TemporaryDirectory() as tmp:
        risk_state_path = Path(tmp) / "state.json"
        cycle_log_path = Path(tmp) / "cycle_log.json"
        _seed_risk_state(risk_state_path, trades_today=2)

        result = _run(
            ["--asset", "BTC", "--side", "sell", "--quantity", "1.0", "--price", "90.0",
             "--protective", "--action", "protective_exit", "--reason", "stop_loss",
             "--avg-cost-basis", "100.0", "--pnl-pct", "-10.0"],
            risk_state_path, cycle_log_path,
        )
        assert result.returncode == 0, result.stderr
        assert "trades_today: 2 -> 2" in result.stdout

        state = json.loads(risk_state_path.read_text())
        assert state["trades_today"] == 2

        cycle_log = json.loads(cycle_log_path.read_text())
        assert cycle_log[0]["classification"] is None
        assert cycle_log[0]["crossover_pct"] is None
        assert cycle_log[0]["action"] == "protective_exit"
        assert cycle_log[0]["reason"] == "stop_loss"
        assert cycle_log[0]["avg_cost_basis"] == 100.0
        assert cycle_log[0]["pnl_pct"] == -10.0


def test_appends_to_existing_trade_log_without_clobbering_prior_entries():
    with tempfile.TemporaryDirectory() as tmp:
        risk_state_path = Path(tmp) / "state.json"
        cycle_log_path = Path(tmp) / "cycle_log.json"
        today = datetime.now(timezone.utc).date().isoformat()
        risk_state_path.write_text(json.dumps({
            "date": today, "starting_equity": 1000.0, "trades_today": 1, "halted": False,
            "trade_log": [{"timestamp": "2026-09-28T12:00:00+00:00", "asset": "LINK",
                            "side": "buy", "quantity": 6.0035, "price": 15.4805}],
        }))
        cycle_log_path.write_text(json.dumps([
            {"timestamp": "2026-09-28T12:00:00+00:00", "asset": "LINK",
             "classification": "fresh_buy_cross", "crossover_pct": 3.0, "action": "executed"},
        ]))

        result = _run(
            ["--asset", "AVAX", "--side", "buy", "--quantity", "7.9511", "--price", "11.560665",
             "--classification", "fresh_buy_cross", "--crossover-pct", "1.7211"],
            risk_state_path, cycle_log_path,
        )
        assert result.returncode == 0, result.stderr

        state = json.loads(risk_state_path.read_text())
        assert state["trades_today"] == 2
        assert [t["asset"] for t in state["trade_log"]] == ["LINK", "AVAX"]

        cycle_log = json.loads(cycle_log_path.read_text())
        assert [e["asset"] for e in cycle_log] == ["LINK", "AVAX"]
