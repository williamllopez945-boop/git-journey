import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.income_cycle import (
    _portfolio_equity,
    _quotes_by_symbol,
    _closes_by_symbol,
    _volumes_by_symbol,
    _positions_by_symbol,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "trading_agent" / "income_cycle.py"

SUPPORT_DAYS = 60  # must match income_signals.SUPPORT_LOOKBACK_DAYS


def _write(tmp_dir, name, payload):
    path = Path(tmp_dir) / name
    path.write_text(json.dumps(payload))
    return str(path)


def _dip_and_support_closes(low=7.0, high=10.0, days=SUPPORT_DAYS):
    # Flat at `high` for the whole window except the final bar, which
    # drops to `low` - this is simultaneously the bottom of the trailing
    # 20-day window (classify_dip) AND the 60-day support level
    # (near_support), so classify_entry fires "dip_buy" on it.
    return [high] * (days - 1) + [low]


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


def test_closes_by_symbol_drops_interpolated_bars():
    historicals = {"data": {"results": [
        {"symbol": "YMAX", "bars": [
            {"close_price": "19.80", "interpolated": True},
            {"close_price": "7.60", "interpolated": False},
            {"close_price": "7.65"},  # no interpolated key at all -> real bar
        ]},
    ]}}
    assert _closes_by_symbol(historicals)["YMAX"] == [7.60, 7.65]


def test_volumes_by_symbol_drops_interpolated_bars():
    historicals = {"data": {"results": [
        {"symbol": "YMAX", "bars": [
            {"close_price": "19.80", "volume": "999999", "interpolated": True},
            {"close_price": "7.60", "volume": "1000", "interpolated": False},
            {"close_price": "7.65", "volume": "1500"},  # no interpolated key -> real bar
        ]},
    ]}}
    assert _volumes_by_symbol(historicals)["YMAX"] == [1000.0, 1500.0]


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


def test_entry_allowed_with_dip_and_support_no_ex_dividend_data_needed():
    # 2026-10-16 owner request: no --fundamentals-file, no ex-dividend
    # gate - a dip_buy + support signal enters on its own.
    with tempfile.TemporaryDirectory() as tmp:
        quotes = {"data": {"results": [
            {"quote": {"symbol": "YMAX", "bid_price": "7.68", "ask_price": "7.70",
                        "last_trade_price": "7.69"}},
        ]}}
        historicals = {"data": {"results": [{"symbol": "YMAX",
                                              "bars": [{"close_price": str(c)}
                                                       for c in _dip_and_support_closes()]}]}}
        portfolio = {"data": {"total_value": "500.0"}}
        positions = {"data": {"positions": []}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
            "--historicals-file", _write(tmp, "historicals.json", historicals),
            "--portfolio-file", _write(tmp, "portfolio.json", portfolio),
            "--positions-file", _write(tmp, "positions.json", positions),
        ])
        assert result.returncode == 0, result.stderr
        assert "YMAX: ENTER dip_buy" in result.stdout


def test_entry_blocked_without_support_confirmation():
    # Bottom of the trailing 20-day window, but NOT near the 60-day
    # support level (an earlier, deeper low sits outside the 20-day
    # window) - classify_entry must hold, not just classify_dip.
    closes = [20.0] * 10 + [5.0] + [10.0] * 48 + [7.1]  # overall low=5.0, today=7.1 (~42% away)
    with tempfile.TemporaryDirectory() as tmp:
        quotes = {"data": {"results": [
            {"quote": {"symbol": "YMAX", "bid_price": "7.08", "ask_price": "7.10",
                        "last_trade_price": "7.09"}},
        ]}}
        historicals = {"data": {"results": [{"symbol": "YMAX",
                                              "bars": [{"close_price": str(c)} for c in closes]}]}}
        portfolio = {"data": {"total_value": "500.0"}}
        positions = {"data": {"positions": []}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
            "--historicals-file", _write(tmp, "historicals.json", historicals),
            "--portfolio-file", _write(tmp, "portfolio.json", portfolio),
            "--positions-file", _write(tmp, "positions.json", positions),
        ])
        assert result.returncode == 0, result.stderr
        assert "hold (no dip+support signal)" in result.stdout
        assert "ENTER" not in result.stdout


def _gated_symbol_bars(today_volume, trailing_volume=1000.0):
    closes = _dip_and_support_closes()
    volumes = [trailing_volume] * (len(closes) - 1) + [today_volume]
    return [{"close_price": str(c), "volume": str(v)} for c, v in zip(closes, volumes)]


def test_gated_symbol_blocked_without_volume_surge():
    # ULTY is in INCOME_INSTITUTIONAL_FLOW_GATED_SYMBOLS - a plain dip_buy
    # with ordinary volume must NOT enter (see
    # backtest_2026-10-13_institutional_flow_income_sleeve.md).
    with tempfile.TemporaryDirectory() as tmp:
        quotes = {"data": {"results": [
            {"quote": {"symbol": "ULTY", "bid_price": "7.68", "ask_price": "7.70",
                        "last_trade_price": "7.69"}},
        ]}}
        historicals = {"data": {"results": [
            {"symbol": "ULTY", "bars": _gated_symbol_bars(today_volume=1000.0)},
        ]}}
        portfolio = {"data": {"total_value": "500.0"}}
        positions = {"data": {"positions": []}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
            "--historicals-file", _write(tmp, "historicals.json", historicals),
            "--portfolio-file", _write(tmp, "portfolio.json", portfolio),
            "--positions-file", _write(tmp, "positions.json", positions),
        ])
        assert result.returncode == 0, result.stderr
        assert "blocked_no_volume_surge" in result.stdout
        assert "ENTER" not in result.stdout


def test_gated_symbol_allowed_with_volume_surge():
    # Same fixture, but today's volume is a clear surge (10x trailing
    # average) - should clear the gate and ENTER.
    with tempfile.TemporaryDirectory() as tmp:
        quotes = {"data": {"results": [
            {"quote": {"symbol": "ULTY", "bid_price": "7.68", "ask_price": "7.70",
                        "last_trade_price": "7.69"}},
        ]}}
        historicals = {"data": {"results": [
            {"symbol": "ULTY", "bars": _gated_symbol_bars(today_volume=10000.0)},
        ]}}
        portfolio = {"data": {"total_value": "500.0"}}
        positions = {"data": {"positions": []}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
            "--historicals-file", _write(tmp, "historicals.json", historicals),
            "--portfolio-file", _write(tmp, "portfolio.json", portfolio),
            "--positions-file", _write(tmp, "positions.json", positions),
        ])
        assert result.returncode == 0, result.stderr
        assert "ULTY: ENTER dip_buy" in result.stdout


def test_wide_spread_candidate_still_enters():
    # 2026-10-16 owner request: the liquidity/spread filter no longer
    # blocks entries - a ~25% spread (well over the old 2% filter) must
    # not stop a dip_buy + support signal from entering.
    with tempfile.TemporaryDirectory() as tmp:
        quotes = {"data": {"results": [
            {"quote": {"symbol": "YMAX", "bid_price": "7.00", "ask_price": "9.00",
                        "last_trade_price": "7.1"}},
        ]}}
        historicals = {"data": {"results": [{"symbol": "YMAX",
                                              "bars": [{"close_price": str(c)}
                                                       for c in _dip_and_support_closes()]}]}}
        portfolio = {"data": {"total_value": "500.0"}}
        positions = {"data": {"positions": []}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
            "--historicals-file", _write(tmp, "historicals.json", historicals),
            "--portfolio-file", _write(tmp, "portfolio.json", portfolio),
            "--positions-file", _write(tmp, "positions.json", positions),
        ])
        assert result.returncode == 0, result.stderr
        assert "blocked_illiquid" not in result.stdout
        assert "YMAX: ENTER dip_buy" in result.stdout


def test_held_position_past_stop_loss_reports_exit():
    with tempfile.TemporaryDirectory() as tmp:
        quotes = {"data": {"results": [
            {"quote": {"symbol": "YMAX", "bid_price": "6.49", "ask_price": "6.51",
                        "last_trade_price": "6.50"}},
        ]}}
        historicals = {"data": {"results": [{"symbol": "YMAX",
                                              "bars": [{"close_price": str(c)}
                                                       for c in _dip_and_support_closes()]}]}}
        portfolio = {"data": {"total_value": "500.0"}}
        # cost basis 10.0, price 6.50 -> -35%, well past the 15% stop-loss
        positions = {"data": {"positions": [
            {"symbol": "YMAX", "quantity": "10", "average_buy_price": "10.0"},
        ]}}

        result = _run(tmp, [
            "--quotes-file", _write(tmp, "quotes.json", quotes),
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
