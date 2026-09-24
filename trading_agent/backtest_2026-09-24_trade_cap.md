# Backtest — max_trades_per_day: 3 vs 10 (2026-09-24)

Direct follow-up to raising `RISK_LIMITS["max_trades_per_day"]` from 3 to
10 earlier today (see `config.py`'s module docstring, "not re-backtested
against this change specifically"). This backtest fills that gap.

## Setup

- **Stocks only.** `STOCK_WATCHLIST`'s 10 symbols (CRWD, PANW, TWLO, ILMN,
  IR, PTC, CHKP, MAIR, AR, HUBS), real hourly bars via
  `get_equity_historicals` (split-adjusted, regular hours), 2026-06-26
  through 2026-09-23 (~90 days, 372 bars/symbol, all bar-aligned).
- **Crypto not covered** — same limitation as every prior backtest this
  session: no crypto historicals tool, and the current `WATCHLIST`
  (LIT, BCH, XCN, HBAR, DOT, CRV, ZORA, LINK, AVAX, ASTER, plus
  BTC/ETH/SOL/PYTH/XLM) doesn't have the kind of liquid equity-ETF
  proxies IBIT/ETHA gave BTC/ETH in `backtest_2026-09-23.md`. This result
  speaks to the stock side of the shared daily cap only.
- Exact production rules: `entry_filter.confirmed_signal` (1-bar
  persistence, `min_strength_pct=0`), `exit_criteria.check_exit` (10%
  stop-loss, 15% take-profit sells 70%), `position_state`'s 4h cooldown,
  `max_position_pct=20%`, `max_concurrent_positions=5`,
  `max_aggregate_position_pct=50%` — all current live config, unchanged.
- **New in `portfolio_backtest.py` for this run**: a `max_trades_per_day`
  parameter didn't exist before today — the simulator had no notion of
  day boundaries or a trade-count cap at all. Added it (shared counter
  across all assets, resets on the real calendar date from each bar's
  timestamp, every trade increments it, protective exits are never
  blocked by it — mirrors `RiskManager.can_trade()`/`record_trade()`
  exactly, including the "exits bypass the cap" rule from PLAYBOOK.md).
- `starting_cash=$1000` (backtest convention throughout this session);
  real $ impact at the live ~$200 portfolio is proportionally smaller.

## Results

| | cap = 3 (old) | cap = 10 (new) | Buy & hold |
|---|---|---|---|
| Return | **+2.60%** | **-2.81%** | +20.35% |
| Max drawdown | 5.89% | 6.86% | 9.23% |
| Trades | 66 | 83 | — |
| Win rate | 42.4% (14W/19L) | 34.1% (14W/27L) | — |

## The finding, stated plainly

**Raising the cap made this backtest worse, not better.** Cap=10 produced
identical results to no cap at all — the trade count never exceeded 7 in
any single day across the whole window, so 10 never actually bound
anything here; 3 did, on 5 separate days.

The 17 extra trades the wider cap let through (66 → 83) added **zero
extra wins** (14 in both cases) and **8 extra losses** (19 → 27). On the
days it mattered, the old cap of 3 wasn't cutting off good signals — it
was incidentally filtering out a cluster of lower-quality, likely
correlated signals firing on the same volatile day, the same failure
mode `backtest_2026-09-23.md`'s concurrent-positions sweep found for
correlated clusters, just expressed through the daily-count gate instead
of the concurrency gate.

**Both variants underperformed buy-and-hold substantially** (+2.60%/
-2.81% vs +20.35%) — consistent with every prior backtest this session;
noted for the same reason as always, not new to this result.

## What this does and doesn't mean

- This is one ~90-day window on 10 stocks; it's a real, honest signal,
  not proof the higher cap is *always* worse. Worth a re-check whenever a
  meaningfully different or longer window is backtested for other
  reasons.
- It doesn't argue for reverting the cap by itself — the owner's request
  wasn't scoped to backtested performance, and 10 is still bounded by
  every per-trade guard (`max_position_pct`, `max_aggregate_position_pct`,
  `max_concurrent_positions`, `auto_execute_max_usd`) exactly as before.
  This is information for that decision, not an automatic reversal.
- Crypto-side impact is genuinely unknown from this data — flagged above,
  not glossed over.
