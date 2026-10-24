# Evidence index

Dated studies behind each strategy decision. The files stay in this folder,
because `config.py`, `CHANGELOG.md`, `PLAYBOOK.md` and `README.md` reference them by bare
filename. Read the relevant study before proposing to re-enable a rejected idea.

## Backtests and strategy studies

- [`backtest_2026-09-23.md`](backtest_2026-09-23.md) - Strategy backtest — 2026-09-23
- [`backtest_2026-09-24_trade_cap.md`](backtest_2026-09-24_trade_cap.md) - Backtest — max_trades_per_day: 3 vs 10 (2026-09-24)
- [`backtest_2026-09-24_trailing_stop.md`](backtest_2026-09-24_trailing_stop.md) - Trailing stop — considered, not adopted (2026-09-24)
- [`backtest_2026-09-25_aggregate_cap.md`](backtest_2026-09-25_aggregate_cap.md) - Aggregate-cap backtest: 50% vs 75% vs 75%+awesome-trade override (2026-09-25)
- [`backtest_2026-09-25_profit_lock.md`](backtest_2026-09-25_profit_lock.md) - Profit-lock stop — considered, not adopted (2026-09-25)
- [`backtest_2026-09-25_stop_take.md`](backtest_2026-09-25_stop_take.md) - Stop-loss / take-profit ratio backtest: 10%/20% (2026-09-25)
- [`backtest_2026-09-26_concurrent_cap.md`](backtest_2026-09-26_concurrent_cap.md) - Concurrent-positions cap re-check: 5 → 10? — 2026-09-26
- [`backtest_2026-09-26_liquidity_displacement.md`](backtest_2026-09-26_liquidity_displacement.md) - Liquidity sweep/displacement entry gate — considered, not adopted (2026-09-26)
- [`backtest_2026-09-26_sma_window_recheck.md`](backtest_2026-09-26_sma_window_recheck.md) - SMA(10,30) window re-check — no change, reconfirmed on the current watchlist
- [`backtest_2026-09-26_trade_cap_recheck.md`](backtest_2026-09-26_trade_cap_recheck.md) - Daily trade cap re-check: 3 → higher? — 2026-09-26
- [`backtest_2026-09-27_orb_evaluation.md`](backtest_2026-09-27_orb_evaluation.md) - 15-Minute Opening Range Breakout (ORB) for VOLTRAP — evaluation (2026-09-27, FINAL)
- [`backtest_2026-09-27_relative_strength.md`](backtest_2026-09-27_relative_strength.md) - Relative-strength entry gate — considered, not adopted (2026-09-27)
- [`backtest_2026-09-27_trade_cap_recheck.md`](backtest_2026-09-27_trade_cap_recheck.md) - max_trades_per_day re-check: 3 -> 4 (2026-09-27)
- [`backtest_2026-09-28_gate_floor_and_tighter_stops.md`](backtest_2026-09-28_gate_floor_and_tighter_stops.md) - Gate floor + tighter stop-loss/take-profit (2026-09-28)
- [`backtest_2026-09-28_sell_cross_profit_gate.md`](backtest_2026-09-28_sell_cross_profit_gate.md) - Profitability gate on death-cross/fresh_sell_cross exits (2026-09-28)
- [`backtest_2026-09-28_sell_off_gate_review.md`](backtest_2026-09-28_sell_off_gate_review.md) - Profitability gate under the 2026-09-28 crypto sell-off - real-data review
- [`backtest_2026-09-29_gate_ab_test_with_costs.md`](backtest_2026-09-29_gate_ab_test_with_costs.md) - Profitability gate: re-tested at current settings, net of transaction costs (2026-09-29)
- [`backtest_2026-09-29_gate_floor_removal.md`](backtest_2026-09-29_gate_floor_removal.md) - 24h gate floor removed (2026-09-29)
- [`backtest_2026-09-29_loss_budget_sizing.md`](backtest_2026-09-29_loss_budget_sizing.md) - Loss-budget position sizing evaluation (2026-09-29)
- [`backtest_2026-09-29_macd_rsi_strategy_rejected.md`](backtest_2026-09-29_macd_rsi_strategy_rejected.md) - MACD+RSI combo strategy — backtested, rejected (2026-09-29)
- [`backtest_2026-09-29_partial_stop_loss_rejected.md`](backtest_2026-09-29_partial_stop_loss_rejected.md) - Partial (70%) stop-loss, once per position — rejected (2026-09-29)
- [`backtest_2026-09-29_walkforward.md`](backtest_2026-09-29_walkforward.md) - Walk-forward backtest: current strategy vs. buy-and-hold and cash, across 4 independent chronological windows (2026-09-29)
- [`backtest_2026-09-29_walkforward_v2_vtrs.md`](backtest_2026-09-29_walkforward_v2_vtrs.md) - Walk-forward backtest re-run: fresh data, VTRS in place of MAIR (2026-09-29)
- [`backtest_2026-09-30_vwap_evaluation.md`](backtest_2026-09-30_vwap_evaluation.md) - VWAP evaluation — no change recommended, negative/neutral on worst case
- [`backtest_2026-10-02_awesome_trade_threshold_sweep.md`](backtest_2026-10-02_awesome_trade_threshold_sweep.md) - "Awesome trade" threshold sweep — keep 5%, do not lower
- [`backtest_2026-10-02_vpoc_evaluation.md`](backtest_2026-10-02_vpoc_evaluation.md) - VPOC (Volume Point of Control) evaluation — no change recommended
- [`backtest_2026-10-07_income_sleeve_full_history.md`](backtest_2026-10-07_income_sleeve_full_history.md) - Income sleeve: full real-history backtest (2026-10-07)
- [`backtest_2026-10-09_macd_rsi_income_sleeve_rejected.md`](backtest_2026-10-09_macd_rsi_income_sleeve_rejected.md) - Income sleeve: does adding MACD/RSI-oversold gating beat the 20-day range signal? (2026-10-09)
- [`backtest_2026-10-13_institutional_flow_income_sleeve.md`](backtest_2026-10-13_institutional_flow_income_sleeve.md) - Income sleeve: does an "institutional money entry" confirmation beat the 20-day dip alone? (2026-10-13)
- [`backtest_2026-10-14_stock_sma_window_sweep.md`](backtest_2026-10-14_stock_sma_window_sweep.md) - Stock watchlist SMA window sweep — keep 10/30, do not shorten
- [`backtest_2026-10-16_income_sleeve_support_zone_and_gate_removal.md`](backtest_2026-10-16_income_sleeve_support_zone_and_gate_removal.md) - Income sleeve: support-zone signal + entry-gate removal — 2026-10-16
- [`backtest_2026-10-20_sustained_excellent_watch_entry.md`](backtest_2026-10-20_sustained_excellent_watch_entry.md) - Sustained excellent_watch entry — rejected, no change to scanner_signals.py

## Watchlist reviews and screens

- [`watchlist_2026-09-22.md`](watchlist_2026-09-22.md) - Crypto watchlist snapshot — 2026-09-22T10:xx UTC
- [`watchlist_2026-09-23_meme_removal.md`](watchlist_2026-09-23_meme_removal.md) - Crypto watchlist: meme-coin removal — 2026-09-23T UTC
- [`watchlist_review_2026-09-26_crypto.md`](watchlist_review_2026-09-26_crypto.md) - Crypto watchlist review — 2026-09-26
- [`watchlist_review_2026-09-26_stocks.md`](watchlist_review_2026-09-26_stocks.md) - Stock watchlist review — 2026-09-26
- [`watchlist_review_2026-09-26_voltrap.md`](watchlist_review_2026-09-26_voltrap.md) - VOLTRAP watchlist — 2026-09-26 (first standing list)
- [`watchlist_review_2026-09-27.md`](watchlist_review_2026-09-27.md) - Weekly watchlist review — 2026-09-27
- [`watchlist_review_2026-09-29_stocks.md`](watchlist_review_2026-09-29_stocks.md) - Watchlist review: MAIR removal, re-tested with sourced candidates (2026-09-29)
- [`watchlist_review_2026-10-04.md`](watchlist_review_2026-10-04.md) - Weekly watchlist review — 2026-10-04
- [`watchlist_review_2026-10-06_stocks_top5.md`](watchlist_review_2026-10-06_stocks_top5.md) - Stock watchlist review — trim to top 5 (2026-10-06)
- [`watchlist_review_2026-10-11.md`](watchlist_review_2026-10-11.md) - Weekly watchlist review — 2026-10-11
- [`watchlist_review_2026-10-18.md`](watchlist_review_2026-10-18.md) - Weekly watchlist review — 2026-10-18
- [`watchlist_stocks_2026-09-23.md`](watchlist_stocks_2026-09-23.md) - Stock watchlist snapshot — 2026-09-23T UTC
- [`watchlist_stocks_2026-09-23_large_cap.md`](watchlist_stocks_2026-09-23_large_cap.md) - Stock watchlist: large-cap upgrade — 2026-09-23T UTC

## Income candidate screens

- [`income_candidates_2026-10-06.md`](income_candidates_2026-10-06.md) - Income sleeve — candidate screen (2026-10-06)
- [`income_candidates_2026-10-07_expansion.md`](income_candidates_2026-10-07_expansion.md) - Income sleeve candidate expansion — 2026-10-07

## VOLTRAP dry-runs

- [`voltrap_dryrun_2026-09-30.md`](voltrap_dryrun_2026-09-30.md) - VOLTRAP dry-run — 2026-09-30
- [`voltrap_dryrun_2026-10-05.md`](voltrap_dryrun_2026-10-05.md) - VOLTRAP dry-run — 2026-10-05
- [`voltrap_dryrun_2026-10-12.md`](voltrap_dryrun_2026-10-12.md) - VOLTRAP dry-run — 2026-10-12
- [`voltrap_dryrun_2026-10-19.md`](voltrap_dryrun_2026-10-19.md) - VOLTRAP dry-run — 2026-10-19

## Reconciliations and sizing

- [`pnl_reconciliation_2026-09-29.md`](pnl_reconciliation_2026-09-29.md) - All-time P&L reconciliation, 2026-09-29
- [`reconciliation_2026-10-05.md`](reconciliation_2026-10-05.md) - Trade ledger reconciliation — 2026-10-05
- [`volatility_sizing_2026-09-23.md`](volatility_sizing_2026-09-23.md) - Volatility-aware position sizing — 2026-09-23
