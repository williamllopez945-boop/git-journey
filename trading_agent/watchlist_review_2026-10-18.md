# Weekly watchlist review — 2026-10-18

## Crypto section: paused

All crypto trading has been fully cut since 2026-10-08 (owner request), and the
account holds zero crypto positions (AERO, the last open position, closed
2026-10-09). A watchlist swap on `WATCHLIST` would have no operational effect
while trading is cut, so the crypto side of this review is skipped this week
per the owner's 2026-10-12 standing instruction. Resume the crypto section in
full the first week crypto trading is re-authorized.

## Stocks: method

1. **Score current `STOCK_WATCHLIST` holdings** (`TWLO, ILMN, PTC, CRWD, PANW`)
   by trailing performance, not today's signal strength.
   `RiskManager.state["trade_log"]` has **zero** entries for any of these five
   symbols — none has ever traded live — so every name was scored by a
   90-day-hourly `backtest.py` run (`get_equity_historicals`, 2026-07-20 →
   2026-10-16, interpolated bars stripped) at production settings
   (`STRATEGY` 10/30 SMA, `exit_criteria.py`'s live 4%/8% stop/take-profit,
   `fee_pct=0.001`), split H1/H2 and scored by the **worse** half — this
   project's standing worst-case-first rule, not full-period mean.
2. **Rank worst-case-first.** None of the five currently holds an open
   position, so all five were eligible as removal candidates (no forced
   liquidation needed either way).
3. **Source addition candidates** from the production stock scan
   (`scan_id 6e009dcf-d184-45a7-915f-ccfc50b4e6be`): 398 matching names
   (`Asset type=STOCK`, market cap > $10B, price > $10, 30-day avg volume >
   1M), returned sorted by **Crossover % desc** this run (200 of 398 rows —
   the known `frontend_limit`/no-pagination gap from `run_scan` still caps
   the page at 200, but since the scan itself now returns in crossover-sorted
   order, the top candidates by crossover are present in what we get; prior
   review docs noted this scan sorting by `Last desc` instead, which would
   miss low-priced high-crossover names — that specific failure mode was not
   observed this run, worth re-checking next week rather than assuming it's
   permanently fixed).
   `watchlist_review.rank_by_crossover_strength`, excluding the current
   watchlist, surfaced the top 3 non-watchlist names by `|crossover_pct|`:
   **TRU** (+4.39%), **CX** (+3.80%), **WMG** (+3.57%).
4. **Backtested every candidate** the same way as step 1 (90-day hourly,
   production settings, H1/H2 worst-case split), then ran a **combined**
   `portfolio_backtest.py` comparison (current 5-name portfolio vs. the one
   proposed swap below) at production `RISK_LIMITS`
   (`max_position_pct=20%, max_concurrent_positions=5,
   max_aggregate_position_pct=60%, max_trades_per_day=4, fee_pct=0.001`).

## Current holdings, ranked worst-half-first

| Symbol | H1 % | H2 % | Worst-half % | Full-period % | Max DD % | Trades |
|---|---|---|---|---|---|---|
| **TWLO** | +27.65 | **−2.95** | **−2.95** | +18.33 | 16.48 | 17 |
| **PANW** | +6.51 | **−0.10** | **−0.10** | +14.23 | 10.92 | 14 |
| CRWD | +6.03 | +14.36 | +6.03 | +31.01 | 8.70 | 13 |
| ILMN | +13.34 | +6.38 | +6.38 | +15.27 | 12.10 | 14 |
| PTC | +11.69 | +34.61 | +11.69 | +50.34 | 9.32 | 12 |

TWLO and PANW are this week's bottom two — both negative on their worse half
despite positive full-period returns, meaning the gain was front- or
back-loaded rather than consistent across the window. Both are flat
(no open position), so no liquidation constraint applies either way.

## Addition candidates, backtested (same method, same window)

| Symbol | Crossover % (scan) | H1 % | H2 % | Worst-half % | Full-period % |
|---|---|---|---|---|---|
| **TRU** | +4.39 | +11.39 | +9.08 | **+9.08** | +19.30 |
| CX | +3.80 | −4.76 | +7.00 | −4.76 | −3.73 |
| WMG | +3.57 | −1.50 | +2.82 | −1.50 | +1.56 |

Only **TRU** clearly beats either removal candidate worst-case-first
(+9.08% vs. TWLO's −2.95% and PANW's −0.10%). CX is worse than both removal
candidates on every measure — reject. WMG is worse than PANW and only
marginally better than TWLO — not a clear win, reject.

## Portfolio-level comparison (current vs. the one proposed swap)

Swapping the single worst holding, **TWLO → TRU**, keeping ILMN/PTC/CRWD/PANW
unchanged, at production `RISK_LIMITS`:

| Portfolio | H1 % | H2 % | Worst-half % | Full-period % | Max DD % | Trades |
|---|---|---|---|---|---|---|
| Current (TWLO, ILMN, PTC, CRWD, PANW) | +6.90 | +10.14 | +6.90 | +17.08 | 4.84 | 61 |
| Proposed (TRU, ILMN, PTC, CRWD, PANW) | +7.82 | +11.64 | +7.82 | +19.60 | 5.27 | 60 |

The proposed portfolio clears the worst-case-first bar: better on both
halves, better full-period, roughly the same number of trades. Max drawdown
is marginally higher (5.27% vs. 4.84%) — a real trade-off, not free, but
small relative to the return improvement.

## Decision

**Recommend: swap TWLO → TRU in `STOCK_WATCHLIST`.** No change recommended
for PANW this week — no candidate clearly beat it once TRU was already
assigned to TWLO's slot (using TRU twice isn't meaningful, and CX/WMG don't
clear the bar against PANW either).

This review does not edit `config.py`. The swap above is a recommendation
only, pending explicit owner approval as a separate action — same as every
prior watchlist change this project has made.

## Caveats

- 90 days of hourly bars is a short window relative to how rarely this
  SMA(10,30) strategy actually trades (12-17 entries per name) — treat this
  as directional evidence, not a long-run guarantee.
- None of these six symbols has ever traded live in this account, so every
  score here is backtest-only, same as every prior stock-side review.
- The stock scan's 200-row page cap (vs. 398 total matches) was not observed
  to cost us anything this run since the scan was itself crossover-sorted,
  but that sort order isn't guaranteed stable week to week — re-verify this
  each time rather than assuming it.
