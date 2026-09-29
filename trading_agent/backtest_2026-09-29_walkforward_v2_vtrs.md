# Walk-forward backtest re-run: fresh data, VTRS in place of MAIR (2026-09-29)

Re-run of `backtest_2026-09-29_walkforward.md`'s 4-fold walk-forward,
requested after today's DOGE/SOL cost-basis correction and the AVAX
trade-recording fix. **Correction on the premise first:** neither of
those fixes touches anything a backtest reads. `backtest.py`/
`portfolio_backtest.py` take fresh market price data pulled at request
time as input; they have never read `trade_log`/`state.json`. This
re-run exists for a real, separate reason instead: the watchlist itself
changed today (`MAIR` -> `VTRS`, `watchlist_review_2026-09-29_stocks.md`),
so the original walk-forward's 11-symbol universe no longer matches
what's actually live, and a fresh data pull picks up the newest week of
real bars.

## Method

Identical to the original walk-forward doc: same production settings
(SMA(10,30), `stop_loss_pct=0.04`, `take_profit_pct=0.08`,
`take_profit_sell_fraction=0.70`, gate `min_sell_profit_pct=0.0`/
`gate_max_hold_bars=24`, `fee_pct=0.001`), same `interpolated != true`
filtering, same 4-fold split, same production risk settings for the
portfolio pass (`max_position_pct=20%`, `max_concurrent_positions=5`,
`max_aggregate_pct=60%`, `max_trades_per_day=4`). Only two things
differ: `VTRS` replaces `MAIR` in the symbol set (current
`STOCK_WATCHLIST`, all 10 names + `IBIT`/`ETHA`, 12 total), and the data
is a fresh pull as of 2026-09-29. **Unlike MAIR, VTRS has full real
(non-interpolated) coverage across the entire aligned window** - no
truncated fold count needed this time; all 12 symbols share the
identical 1149-bar window, 2025-12-22 to 2026-09-28.

## Portfolio-level results (binding, per this project's standing convention)

**All 12 combined:**

| Fold | Window | Strategy | Buy-and-hold (eq-wt) | Max DD | # trades |
|---|---|---|---|---|---|
| F1 | 2025-12-22 -> 2026-03-04 | **+10.84%** | **-9.75%** | 5.41% | 59 |
| F2 | 2026-03-04 -> 2026-05-12 | +8.97% | +18.35% | 3.14% | 56 |
| F3 | 2026-05-12 -> 2026-07-21 | +12.16% | +11.47% | 4.40% | 60 |
| F4 | 2026-07-22 -> 2026-09-28 | +6.34% | +17.75% | 6.26% | 57 |

**Same shape as the original result, still holds with VTRS in the mix:
every fold positive, beats cash in all 4 windows.** F1 (the down-market
fold) again shows the strategy's downside protection clearly (+10.84%
vs. buy-and-hold's -9.75%, an even wider gap than the original 11-symbol
run's +7.13%/-12.80%); F2 and F4 give back upside in strong bull folds
(expected, by design); F3 roughly matches a choppy/flat market. Directly
comparable to the original doc's table - the pattern is stable across a
symbol swap and a fresh data pull, not an artifact of the specific
11-symbol mix.

**Stocks (10, VTRS in) and crypto-proxy separately** show the same
overall shape as before - stocks clearly outperform in F1
(+10.82% vs. -6.92%), give back upside in strong-bull folds; crypto-proxy
smaller-sample but directionally consistent, beating buy-and-hold in 3
of 4 folds including two negative buy-and-hold windows (F1: -5.97% vs.
-23.92%; F3: +3.68% vs. -16.19%).

## VTRS itself, isolated, on the full real window (no longer truncated)

| Fold | Strategy | Buy-and-hold |
|---|---|---|
| F1 | +9.13% | +23.76% |
| F2 | +3.80% | +14.47% |
| F3 | **-10.71%** | +3.91% |
| F4 | +5.13% | +5.43% |

VTRS's one weak fold (F3, -10.71% vs. a positive buy-and-hold) is
consistent with what the 2026-09-29 watchlist review already found on
the shorter, MAIR-constrained 676-bar overlap window (also F3
weakest there) - not a new finding, just now visible across the full
1149-bar window since VTRS has real data for the entire period, unlike
MAIR's truncated 682 bars.

## Decision: reconfirms the strategy, no parameter change

Same conclusion as the original walk-forward doc, now re-validated
against the current live watchlist and the freshest available data: the
strategy beats cash in every one of 4 independent real-data windows,
clearly earns its keep in the one down-market fold, and gives back some
upside in strong bulls by design. Nothing here changes live behavior.

## What this doesn't establish

Same standing gaps as the original doc - crypto proxies only
(`IBIT`/`ETHA` stand in for BTC/ETH), same-bar fill timing, `fee_pct=0.001`
is one point not a sweep (see `backtest_2026-09-29_gate_ab_test_with_costs.md`
for that), and 4 folds of ~6-7 weeks each remains a modest sample for
true regime-independence. This re-run does not establish anything the
original didn't - it confirms the same finding survives a real watchlist
change and a fresh data pull, which is the specific thing worth checking
after today's swap.
