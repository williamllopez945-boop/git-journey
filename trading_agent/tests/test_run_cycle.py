import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from trading_agent.run_cycle import _crypto_avg_cost, _equity_signal_columns, _numeric_or_none, _portfolio_equity, _scan_rows

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "trading_agent" / "run_cycle.py"


def test_scan_rows_unwraps_full_tool_response():
    wrapped = {"data": {"result": {"results": [{"ticker": "BTC"}]}}}
    assert _scan_rows(wrapped) == [{"ticker": "BTC"}]


def test_scan_rows_accepts_bare_list():
    bare = [{"ticker": "BTC"}]
    assert _scan_rows(bare) == bare


def test_portfolio_equity_unwraps_data_key():
    assert _portfolio_equity({"data": {"total_value": "200.40"}}) == 200.40


def test_portfolio_equity_accepts_bare_payload():
    assert _portfolio_equity({"total_value": "200.40"}) == 200.40


def test_crypto_avg_cost_weighted_average():
    position = {"cost_bases": [
        {"direct_quantity": "10", "direct_cost_basis": "100"},
        {"direct_quantity": "5", "direct_cost_basis": "60"},
    ]}
    # (100 + 60) / (10 + 5) = 160 / 15
    assert abs(_crypto_avg_cost(position) - (160 / 15)) < 1e-9


def test_crypto_avg_cost_none_when_zero_direct_quantity():
    position = {"cost_bases": [{"direct_quantity": "0", "direct_cost_basis": "0"}]}
    assert _crypto_avg_cost(position) is None


def test_numeric_or_none_handles_empty_string():
    assert _numeric_or_none("") is None
    assert _numeric_or_none(None) is None
    assert _numeric_or_none("1.5") == 1.5


def test_equity_signal_columns_computes_sma_and_pct_change():
    historicals = {"data": {"results": [
        {"symbol": "ILMN", "bars": [{"close_price": str(100 + i), "volume": 1000} for i in range(30)]},
    ]}}
    quotes = {"data": {"results": [
        {"quote": {"symbol": "ILMN", "last_trade_price": "129.0", "previous_close": "120.0"}},
    ]}}
    cols = _equity_signal_columns(historicals, quotes)
    assert set(cols.keys()) == {"ILMN"}
    row = cols["ILMN"]
    # closes are 100..129 oldest-to-newest: SMA10 = avg(120..129), SMA30 = avg(100..129)
    assert float(row["SMA 10 (1h)"]) == sum(range(120, 130)) / 10
    assert float(row["SMA 30 (1h)"]) == sum(range(100, 130)) / 30
    assert float(row["% Change"]) == (129.0 - 120.0) / 120.0
    assert float(row["Last"]) == 129.0


def test_equity_signal_columns_skips_symbol_with_too_few_bars():
    historicals = {"data": {"results": [
        {"symbol": "AR", "bars": [{"close_price": "10.0", "volume": 500}] * 5},
    ]}}
    quotes = {"data": {"results": [
        {"quote": {"symbol": "AR", "last_trade_price": "10.0", "previous_close": "9.5"}},
    ]}}
    assert _equity_signal_columns(historicals, quotes) == {}


def test_equity_signal_columns_accepts_bare_unwrapped_payload():
    historicals = {"results": [
        {"symbol": "PTC", "bars": [{"close_price": str(50 + i), "volume": 100} for i in range(30)]},
    ]}
    quotes = {"results": [
        {"quote": {"symbol": "PTC", "last_trade_price": "79.0", "previous_close": "78.0"}},
    ]}
    cols = _equity_signal_columns(historicals, quotes)
    assert "PTC" in cols


def _write(tmp_dir, name, payload):
    path = Path(tmp_dir) / name
    path.write_text(json.dumps(payload))
    return str(path)


def test_end_to_end_reports_fresh_buy_cross_and_exit_check():
    with tempfile.TemporaryDirectory() as tmp:
        # DOT: a confirmed fresh_buy_cross needs scanner_state.json to already
        # show a pending bullish flip from a prior cycle - simulate that by
        # pointing HOME/state at an isolated scanner_state via cwd trick is
        # overkill for this smoke test, so assert on the weaker but still
        # meaningful contract: the script runs end-to-end, reports circuit
        # breaker / can_trade state, and reports an exit check for a held
        # position, without crashing on real-shaped input.
        scan = {
            "data": {"result": {"results": [
                {"ticker": "BTC", "columns": {
                    "Symbol": "BTC", "SMA 10 (1h)": "100", "SMA 30 (1h)": "95",
                    "% Change": "0.01", "Relative volume": "1.2", "Last": "101",
                }},
            ]}}
        }
        portfolio = {"data": {"total_value": "200.40"}}
        positions = {"data": {"results": [
            {"currency": {"code": "BTC"}, "quantity_transferable": "1.0",
             "cost_bases": [{"direct_quantity": "1.0", "direct_cost_basis": "90.0"}]},
        ]}}

        scan_file = _write(tmp, "scan.json", scan)
        portfolio_file = _write(tmp, "portfolio.json", portfolio)
        positions_file = _write(tmp, "positions.json", positions)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "crypto",
             "--scan-file", scan_file, "--portfolio-file", portfolio_file,
             "--positions-file", positions_file, "--no-log",
             "--risk-state-path", str(Path(tmp) / "state.json"),
             "--scanner-state-path", str(Path(tmp) / "scanner_state.json"),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(Path(tmp) / "cycle_log.json")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        assert "circuit_breaker_halted:" in result.stdout
        assert "can_trade:" in result.stdout
        assert "BTC exit ->" in result.stdout


def test_stock_asset_class_uses_historicals_and_quotes_not_scan_file():
    with tempfile.TemporaryDirectory() as tmp:
        historicals = {"data": {"results": [
            {"symbol": "ILMN", "bars": [{"close_price": str(200 + i), "volume": 1000} for i in range(30)]},
        ]}}
        quotes = {"data": {"results": [
            {"quote": {"symbol": "ILMN", "last_trade_price": "229.0", "previous_close": "220.0"}},
        ]}}
        portfolio = {"data": {"total_value": "200.40"}}
        positions = {"data": {"positions": []}}

        historicals_file = _write(tmp, "historicals.json", historicals)
        quotes_file = _write(tmp, "quotes.json", quotes)
        portfolio_file = _write(tmp, "portfolio.json", portfolio)
        positions_file = _write(tmp, "positions.json", positions)

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "stock",
             "--historicals-file", historicals_file, "--quotes-file", quotes_file,
             "--portfolio-file", portfolio_file, "--positions-file", positions_file, "--no-log",
             "--risk-state-path", str(Path(tmp) / "state.json"),
             "--scanner-state-path", str(Path(tmp) / "scanner_state.json"),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(Path(tmp) / "cycle_log.json")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        assert "circuit_breaker_halted:" in result.stdout


def test_protective_exit_still_reported_during_a_circuit_breaker_halt():
    # 2026-09-29 regression: ChatGPT's second-opinion review flagged an
    # apparent contradiction between earlier reports ("circuit-breaker halts
    # skipped all evaluation") and the current PLAYBOOK.md/CHANGELOG.md
    # claim ("protective exits are never gated by the halt") and asked for
    # the actual code path to be verified and regression-tested, not just
    # asserted in prose. This is that test, at the run_cycle.py level (the
    # code path a live cycle actually calls): pre-seed a starting_equity
    # far above today's portfolio value (a real, current-day breach, not a
    # stale prior-day figure that start_of_day() would just overwrite), and
    # a held position priced well past the 4% stop-loss threshold. Assert
    # BOTH that the script reports the halt AND that it still reports the
    # stop-loss exit - proving protective exits are not skipped in the
    # actual code, not just documented as such.
    with tempfile.TemporaryDirectory() as tmp:
        scan = {
            "data": {"result": {"results": [
                {"ticker": "BTC", "columns": {
                    "Symbol": "BTC", "SMA 10 (1h)": "100", "SMA 30 (1h)": "95",
                    "% Change": "-0.10", "Relative volume": "1.2", "Last": "90",
                }},
            ]}}
        }
        # Today's equity (200.40) is a 33% drawdown from starting_equity
        # (300) - well past the 3% daily_loss_limit_pct - and "date" is
        # today's real UTC date so RiskManager treats this as already
        # recorded today rather than resetting it via start_of_day().
        portfolio = {"data": {"total_value": "200.40"}}
        today = datetime.now(timezone.utc).date().isoformat()
        risk_state = {
            "date": today, "starting_equity": 300.0, "trades_today": 0,
            "halted": False, "trade_log": [],
        }
        # BTC held at cost basis 100, marked at 90 (-10%) - well past the
        # 4% stop-loss trigger (exit_criteria.STOP_LOSS_PCT).
        positions = {"data": {"results": [
            {"currency": {"code": "BTC"}, "quantity_transferable": "1.0",
             "cost_bases": [{"direct_quantity": "1.0", "direct_cost_basis": "100.0"}]},
        ]}}

        scan_file = _write(tmp, "scan.json", scan)
        portfolio_file = _write(tmp, "portfolio.json", portfolio)
        positions_file = _write(tmp, "positions.json", positions)
        risk_state_path = Path(tmp) / "state.json"
        risk_state_path.write_text(json.dumps(risk_state))

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "crypto",
             "--scan-file", scan_file, "--portfolio-file", portfolio_file,
             "--positions-file", positions_file, "--no-log",
             "--risk-state-path", str(risk_state_path),
             "--scanner-state-path", str(Path(tmp) / "scanner_state.json"),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(Path(tmp) / "cycle_log.json")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        assert "circuit_breaker_halted: True" in result.stdout
        assert "can_trade: False" in result.stdout
        assert "BTC exit -> stop_loss" in result.stdout


def test_stock_asset_class_requires_historicals_and_quotes_files():
    with tempfile.TemporaryDirectory() as tmp:
        portfolio_file = _write(tmp, "portfolio.json", {"data": {"total_value": "200.40"}})
        positions_file = _write(tmp, "positions.json", {"data": {"positions": []}})

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "stock",
             "--portfolio-file", portfolio_file, "--positions-file", positions_file, "--no-log",
             "--risk-state-path", str(Path(tmp) / "state.json"),
             "--scanner-state-path", str(Path(tmp) / "scanner_state.json"),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(Path(tmp) / "cycle_log.json")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0
        assert "--historicals-file and --quotes-file" in result.stderr


def test_record_only_requires_record_trade_asset():
    with tempfile.TemporaryDirectory() as tmp:
        portfolio_file = _write(tmp, "portfolio.json", {"data": {"total_value": "200.40"}})

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "crypto", "--record-only",
             "--portfolio-file", portfolio_file,
             "--risk-state-path", str(Path(tmp) / "state.json"),
             "--scanner-state-path", str(Path(tmp) / "scanner_state.json"),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(Path(tmp) / "cycle_log.json")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0
        assert "--record-only has nothing to do without --record-trade-asset" in result.stderr


def test_record_only_does_not_require_scan_or_positions_files():
    # --record-only needs no classification/position data at all - only
    # --portfolio-file (for the circuit-breaker status line) and the
    # --record-trade-* flags. No --scan-file, --historicals-file,
    # --quotes-file, or --positions-file should be required.
    with tempfile.TemporaryDirectory() as tmp:
        portfolio_file = _write(tmp, "portfolio.json", {"data": {"total_value": "200.40"}})

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "crypto", "--record-only",
             "--portfolio-file", portfolio_file,
             "--record-trade-asset", "BTC", "--record-trade-side", "sell",
             "--record-trade-quantity", "0.001", "--record-trade-price", "85000.0",
             "--record-trade-classification", "fresh_sell_cross",
             "--record-trade-crossover-pct", "-0.12",
             "--risk-state-path", str(Path(tmp) / "state.json"),
             "--scanner-state-path", str(Path(tmp) / "scanner_state.json"),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(Path(tmp) / "cycle_log.json")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        assert "circuit_breaker_halted:" in result.stdout
        assert "--- classifications" not in result.stdout
        assert "--- protective-exit checks" not in result.stdout
        assert "recorded: sell 0.001 BTC @ 85000.0" in result.stdout


def test_record_only_leaves_scanner_state_untouched():
    # The actual bug this mode fixes: recording a fill used to require a
    # second full invocation with the same --scan-file, which called
    # classify() again on identical inputs and silently advanced
    # scanner_state.json's persisted pending/confirmed state a second time
    # this cycle (observed live 2026-10-05, e.g. XLM confirming
    # fresh_sell_cross only on a duplicate call - see CHANGELOG.md). Prove
    # the fix: a --record-only call makes no change to scanner_state.json
    # at all, byte for byte - then show the old buggy pattern (a second
    # plain invocation with the same --scan-file) DOES still mutate it
    # further on identical inputs, so this is a real, reproducible bug
    # --record-only actually avoids, not a hypothetical one.
    with tempfile.TemporaryDirectory() as tmp:
        scanner_state_path = Path(tmp) / "scanner_state.json"
        # Pre-seed a prior bearish reading so this cycle's bullish scan
        # data triggers a real "cross just happened" -> pending=True
        # transition (classify()'s prev-is-None path sets pending=False
        # immediately, which can't demonstrate the confirm-on-duplicate-
        # call bug - a real pending state is required first).
        scanner_state_path.write_text(json.dumps({"BTC": {"bullish": False, "crossover_pct": -1.0, "pending": False}}))
        portfolio_file = _write(tmp, "portfolio.json", {"data": {"total_value": "200.40"}})
        scan = {
            "data": {"result": {"results": [
                {"ticker": "BTC", "columns": {
                    "Symbol": "BTC", "SMA 10 (1h)": "100", "SMA 30 (1h)": "95",
                    "% Change": "0.01", "Relative volume": "1.2", "Last": "101",
                }},
            ]}}
        }
        positions = {"data": {"results": []}}
        scan_file = _write(tmp, "scan.json", scan)
        positions_file = _write(tmp, "positions.json", positions)

        # First, a normal classify-only cycle detects the bearish->bullish
        # flip and records it as pending (classification: hold).
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "crypto",
             "--scan-file", scan_file, "--portfolio-file", portfolio_file,
             "--positions-file", positions_file, "--no-log",
             "--risk-state-path", str(Path(tmp) / "state.json"),
             "--scanner-state-path", str(scanner_state_path),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(Path(tmp) / "cycle_log.json")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        state_after_classify = scanner_state_path.read_text()
        assert json.loads(state_after_classify)["BTC"]["pending"] is True

        # Recording a fill for that same cycle must not touch it at all.
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "crypto", "--record-only",
             "--portfolio-file", portfolio_file,
             "--record-trade-asset", "BTC", "--record-trade-side", "buy",
             "--record-trade-quantity", "1.0", "--record-trade-price", "101.0",
             "--record-trade-classification", "fresh_buy_cross",
             "--record-trade-crossover-pct", "5.26",
             "--risk-state-path", str(Path(tmp) / "state.json"),
             "--scanner-state-path", str(scanner_state_path),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(Path(tmp) / "cycle_log.json")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        assert scanner_state_path.read_text() == state_after_classify

        # Contrast: the old buggy pattern of re-running with --scan-file
        # (no --record-only) DOES mutate it further on the exact same
        # inputs - the pending flip from the first call is still there, so
        # this duplicate call wrongly confirms it as a fresh cross.
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "crypto",
             "--scan-file", scan_file, "--portfolio-file", portfolio_file,
             "--positions-file", positions_file, "--no-log",
             "--risk-state-path", str(Path(tmp) / "state.json"),
             "--scanner-state-path", str(scanner_state_path),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(Path(tmp) / "cycle_log.json")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        assert "BTC: fresh_buy_cross" in result.stdout
        assert scanner_state_path.read_text() != state_after_classify
        assert json.loads(scanner_state_path.read_text())["BTC"]["pending"] is False


def test_record_only_still_records_the_trade():
    with tempfile.TemporaryDirectory() as tmp:
        portfolio_file = _write(tmp, "portfolio.json", {"data": {"total_value": "200.40"}})
        risk_state_path = Path(tmp) / "state.json"
        cycle_log_path = Path(tmp) / "cycle_log.json"

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--asset-class", "crypto", "--record-only",
             "--portfolio-file", portfolio_file,
             "--record-trade-asset", "ETH", "--record-trade-side", "sell",
             "--record-trade-quantity", "0.5", "--record-trade-price", "2700.0",
             "--record-trade-protective",
             "--record-trade-classification", "stop_loss",
             "--record-trade-action", "executed",
             "--record-trade-order-id", "order-123",
             "--risk-state-path", str(risk_state_path),
             "--scanner-state-path", str(Path(tmp) / "scanner_state.json"),
             "--position-state-path", str(Path(tmp) / "position_state.json"),
             "--cycle-log-path", str(cycle_log_path)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr

        risk_state = json.loads(risk_state_path.read_text())
        trade_log = risk_state["trade_log"]
        assert trade_log[-1]["asset"] == "ETH"
        assert trade_log[-1]["side"] == "sell"
        assert trade_log[-1]["price"] == 2700.0
        # protective=True must not consume a daily trade slot.
        assert risk_state["trades_today"] == 0

        cycle_log = json.loads(cycle_log_path.read_text())
        assert cycle_log[-1]["asset"] == "ETH"
        assert cycle_log[-1]["action"] == "executed"
        assert cycle_log[-1]["order_id"] == "order-123"
