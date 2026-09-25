# Stop-loss / take-profit ratio backtest: 10%/20% (2026-09-25)

## Request

Owner: "1 to 2 ask ratio. Risk -10% stop loss and move take profit to
20%" — keep `STOP_LOSS_PCT` at 10%, raise `TAKE_PROFIT_PCT` from 15% to
20%, for a 1:2 risk/reward ratio.

`backtest_2026-09-23.md`'s original stop-loss/take-profit sweep tested
(8%/50%) and (10%/50%) against the original (10%/15%) and rejected both
on worst-case grounds (-75.26% and -25.84% respectively vs the original's
0% self-baseline) — but never tested (10%/20%) specifically. This file
fills that gap before shipping the requested change, per this project's
standing practice of backtesting a risk-limit change before applying it
where there's time to do so (see `backtest_2026-09-25_aggregate_cap.md`
for the same day's other instance of this).

## What was tested

**Series**: all 12 names in the current live watchlist composition —
`IBIT`/`ETHA` (crypto proxies) plus the 10-name `STOCK_WATCHLIST`
(`CRWD`, `PANW`, `TWLO`, `ILMN`, `IR`, `PTC`, `CHKP`, `MAIR`, `AR`,
`HUBS`) — across 4 windows each (90-day hourly + the same 3.7-year
daily history split into 3 regimes already fetched for the aggregate-cap
backtest), for **48 series total**. Not the identical 11-series
robustness set from `backtest_2026-09-23.md` (that set used older
proxies/watchlist names no longer current) — this uses the actual
current watchlist instead, which is more relevant to what the change
will actually trade going forward, at the cost of not being a bit-for-
bit re-run of the original sweep.

**Config held fixed at tuned production values**: `short_window=10`,
`long_window=30`, `min_strength_pct=0`, `cooldown_bars=4`,
`take_profit_sell_fraction=0.70`. Only `take_profit_pct` varied: 15%
(current) vs 20% (requested). `stop_loss_pct` held at 10% in both (not
swept — the request was specifically to keep it unchanged).

Single-asset `backtest.py`, not `portfolio_backtest.py` — this change is
about the exit trigger level, not multi-asset sizing/concurrency, so the
simpler simulator (same one the original 2026-09-23 sweep used) is the
right tool.

## Result: helps more than it hurts, worst case well inside prior tolerance

Ranked by delta (20% take-profit's return minus 15%'s, per series):

- **22 of 48 series helped**, 9 hurt, 17 unchanged (no take-profit event
  occurred in that window either way — most of the "unchanged" rows are
  series with 0% delta because the price never reached even the 15%
  level in that window, not because the change did nothing).
- **Mean delta: +2.02%.**
- **Worst case: AR_regime2_2024, -8.06%** (-9.83% at 15% take-profit →
  -17.90% at 20%).
- **Best case: CRWD_regime2_2024, +17.31%** (54.79%→72.10%).

The worst case here (-8.06%) is dramatically smaller than what the
original sweep already rejected at other take-profit levels (-25.84% for
50%, -75.26% for the (8%/50%) combination) — this isn't grading on a
curve against unrelated values, it's the same worst-case-first ranking
this project uses everywhere, and 20% clears it by a wide margin.

## Why it helps more often than it hurts

A 20% take-profit trigger sells the first 70% later than a 15% one, so
it participates further into strong trends before locking in the
partial exit (`ILMN_regime2_2024`: +49.58%→+61.45%;
`CRWD_regime2_2024`: +54.79%→+72.10%; `TWLO_regime3_2025-26`:
+9.68%→+25.41%). It costs something in choppier, weaker regimes where a
15% trigger would have locked in a smaller gain before a reversal gave
it back (`AR_regime2_2024`: -9.83%→-17.90% — the position kept riding
past 15% into a move that then reversed further before finally
triggering the higher bar, or exiting via stop-loss/death-cross instead
without ever taking the intermediate profit). This is the same
underlying tradeoff `TAKE_PROFIT_SELL_FRACTION`'s own 2026-09-23 tuning
already identified (letting more ride captures more upside at some
downside cost) — this result is consistent with that finding, not a new
kind of risk.

## Decision

**`TAKE_PROFIT_PCT` raised from 0.15 to 0.20.** `STOP_LOSS_PCT`
unchanged at 0.10 (a genuine 1:2 ratio, as requested).
`TAKE_PROFIT_SELL_FRACTION` (70%) unchanged — not part of this request,
and the 2026-09-23 tuning already validated it independently.
`exit_criteria.py`'s module docstring and constants updated; test suite
updated for the new default (149/149 pass, including a new
`test_default_take_profit_pct_is_20_percent` lock-in test matching the
existing pattern for `TAKE_PROFIT_SELL_FRACTION`).
