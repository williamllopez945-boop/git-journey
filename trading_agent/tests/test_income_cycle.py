import json
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.income_cycle import (
    _portfolio_equity,
    _quotes_by_symbol,
    _fundamentals_by_symbol,
    _closes_by_symbol,
    _positions_by_symbol,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "trading_agent" / "income_cycle.py"


def _write(tmp_dir, name, payload):
    path = Path(tmp_dir) / name
    path.write_text(json.dumps(payload))
    return str(path)


def _dip_closes(low=7.0, high=10.0, today_close=7.1, days=20):
    # Flat-ish high for most of the window, a dip at the end - puts
    # rolling_range_position near 0 (bottom of the trailing range).
    closes = [high] * (days - 1) + [today_close]
    closes[0] = low  # ensure low is inside the window
    return closes


def _state_paths(tmp):
    return [
        "--risk-state-path", str(Path(tmp) / "risk_state.json"),
        "--position-state-path", str(Path(tmp) / "position_state.json"),
        "--cycle-log-path", str(Path(tmp) / "cycle_log.json"),
    ]


def test_portfolio_equity_unwraps_data_key():
    assert _portfolio_equity({"data": {"total_value": "500.0"}}) == 500.0


def test_quotes_by_symbol():
    quotes = {"data": {"results": [
        {"quote": {"symbol": "YMAX", "bid_price": "7.60", "ask_price": "7.70",
                    "last_trade_price": "7.65"}},
    ]}}
    by_symbol = _quotes_by_symbol(quotes)
    assert by_symbol["YMAX"]["bid_price"] == "7.60"


def test_fundamentals_by_symbol():
    fundamentals = {"data": {"results": [{"symbol": "YMAX", "ex_dividend_date": "2026-10-07"}]}}
    assert _fundamentals_by_symbol(fundamentals)["YMAX"]["ex_dividend_date"] == "2026-10-07"


def test_closes_by_symbol_drops_interpolated_bars():
    historicals = {"data": {"results": [
        {"symbol": "YMAX", "bars": [
            {"close_price": "19.80", "interpolated": True},
            {"close_price": "7.60", "interpolated": False},
            {"close_price": "7.65"},  # no interpolated key at all -> real bar
        ]},
    ]}}
    assert _closes_by_symbol(historicals)["YMAX"] == [7.60, 7.65]


def test_positions_by_symbol_drops_zero_quantity():
    positions = {"data": {"positions": [
        {"symbol": "YMAX", "quantity": "10", "average_buy_price": "7.5"},
        {"symbol": "YMAG", "quantity": "0", "average_buy_price": "11.0"},
    ]}}
    by_symbol = _positions_by_symbol(positions)
    assert set(by_symbol.keys()) == {"YMAX"}


def _run(tmp, extra_args):
    return subprocess.run(
        [sys.executable, str(SCRIPT)] + extra_args + _state_paths(tmp) + ["--no-log"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


def test_entry_blocked_in_avoid_window():
    with tempfile.TemporaryDirectory() as tmp:
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        quotes = {"data": {"results": [
            {"quote": {"symbol": "YMAX", "bid_price": "7.68", "ask_price": "7.70",
                        "last_trade_price": "7.69"}},
        ]}}
        fundamentals = {"data": {"results": [{"symbol": "YMAX", "ex_dividend_date": tomorrow}]}}
        historicals = {"data": {"results": [{"symbol": "YMAX",
                                              "bars": [{"close_price": str(c)} for c in _dip_closes()]}]}}
        portfolio = {"data": {"total_value": "500.0"}}
        positions = {"data": {"positions": []}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
            "--fundamentals-file", _write(tmp, "fundamentals.json", fundamentals),
            "--historicals-file", _write(tmp, "historicals.json", historicals),
            "--portfolio-file", _write(tmp, "portfolio.json", portfolio),
            "--positions-file", _write(tmp, "positions.json", positions),
        ])
        assert result.returncode == 0, result.stderr
        assert "blocked_avoid_window" in result.stdout
        assert "ENTER" not in result.stdout


def test_entry_allowed_in_favorable_window():
    with tempfile.TemporaryDirectory() as tmp:
        today = date.today().isoformat()
        quotes = {"data": {"results": [
            {"quote": {"symbol": "YMAX", "bid_price": "7.68", "ask_price": "7.70",
                        "last_trade_price": "7.69"}},
        ]}}
        fundamentals = {"data": {"results": [{"symbol": "YMAX", "ex_dividend_date": today}]}}
        historicals = {"data": {"results": [{"symbol": "YMAX",
                                              "bars": [{"close_price": str(c)} for c in _dip_closes()]}]}}
        portfolio = {"data": {"total_value": "500.0"}}
        positions = {"data": {"positions": []}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
            "--fundamentals-file", _write(tmp, "fundamentals.json", fundamentals),
            "--historicals-file", _write(tmp, "historicals.json", historicals),
            "--portfolio-file", _write(tmp, "portfolio.json", portfolio),
            "--positions-file", _write(tmp, "positions.json", positions),
        ])
        assert result.returncode == 0, result.stderr
        assert "YMAX: ENTER dip_buy" in result.stdout


def test_illiquid_candidate_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        today = date.today().isoformat()
        quotes = {"data": {"results": [
            {"quote": {"symbol": "YMAX", "bid_price": "7.00", "ask_price": "9.00",
                        "last_trade_price": "8.0"}},  # ~25% spread, well over the 2% filter
        ]}}
        fundamentals = {"data": {"results": [{"symbol": "YMAX", "ex_dividend_date": today}]}}
        historicals = {"data": {"results": [{"symbol": "YMAX",
                                              "bars": [{"close_price": str(c)} for c in _dip_closes()]}]}}
        portfolio = {"data": {"total_value": "500.0"}}
        positions = {"data": {"positions": []}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
            "--fundamentals-file", _write(tmp, "fundamentals.json", fundamentals),
            "--historicals-file", _write(tmp, "historicals.json", historicals),
            "--portfolio-file", _write(tmp, "portfolio.json", portfolio),
            "--positions-file", _write(tmp, "positions.json", positions),
        ])
        assert result.returncode == 0, result.stderr
        assert "blocked_illiquid" in result.stdout
        assert "ENTER" not in result.stdout


def test_held_position_past_stop_loss_reports_exit():
    with tempfile.TemporaryDirectory() as tmp:
        today = date.today().isoformat()
        quotes = {"data": {"results": [
            {"quote": {"symbol": "YMAX", "bid_price": "6.49", "ask_price": "6.51",
                        "last_trade_price": "6.50"}},
        ]}}
        fundamentals = {"data": {"results": [{"symbol": "YMAX", "ex_dividend_date": today}]}}
        historicals = {"data": {"results": [{"symbol": "YMAX",
                                              "bars": [{"close_price": str(c)} for c in _dip_closes()]}]}}
        portfolio = {"data": {"total_value": "500.0"}}
        # cost basis 10.0, price 6.50 -> -35%, well past the 15% stop-loss
        positions = {"data": {"positions": [
            {"symbol": "YMAX", "quantity": "10", "average_buy_price": "10.0"},
        ]}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
            "--fundamentals-file", _write(tmp, "fundamentals.json", fundamentals),
            "--historicals-file", _write(tmp, "historicals.json", historicals),
            "--portfolio-file", _write(tmp, "portfolio.json", portfolio),
            "--positions-file", _write(tmp, "positions.json", positions),
        ])
        assert result.returncode == 0, result.stderr
        assert "YMAX exit -> stop_loss" in result.stdout


def test_record_only_writes_only_to_given_state_paths():
    real_risk_state = REPO_ROOT / "trading_agent" / "income_risk_state.json"
    real_cycle_log = REPO_ROOT / "trading_agent" / "income_cycle_log.json"
    risk_before = real_risk_state.read_text() if real_risk_state.exists() else None
    log_before = real_cycle_log.read_text() if real_cycle_log.exists() else None

    with tempfile.TemporaryDirectory() as tmp:
        risk_path = Path(tmp) / "risk_state.json"
        position_path = Path(tmp) / "position_state.json"
        cycle_log_path = Path(tmp) / "cycle_log.json"

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--record-only",
             "--record-trade-asset", "YMAX", "--record-trade-side", "buy",
             "--record-trade-quantity", "12.5", "--record-trade-price", "7.68",
             "--record-trade-notional", "96.00", "--record-trade-reason", "dip_buy",
             "--risk-state-path", str(risk_path),
             "--position-state-path", str(position_path),
             "--cycle-log-path", str(cycle_log_path)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        assert "recorded: buy 12.5 YMAX" in result.stdout
        assert risk_path.exists()
        assert cycle_log_path.exists()
        assert "YMAX" in cycle_log_path.read_text()

    # The real sleeve state files must not have been touched by this test.
    risk_after = real_risk_state.read_text() if real_risk_state.exists() else None
    log_after = real_cycle_log.read_text() if real_cycle_log.exists() else None
    assert risk_after == risk_before
    assert log_after == log_before
