# Weekly watchlist review — 2026-10-11

**Decision: no change recommended** for either watchlist. Crypto trading
remains fully cut (owner directive, 2026-10-08) and the account now holds
zero crypto positions at all (AERO, the last open position, has since
closed) — there is no crypto watchlist action that would have any
operational effect this week. On the stock side, all 5 `STOCK_WATCHLIST`
names backtest positively worst-case-first; none qualifies as a genuine
underperformer, so no removal candidate exists to justify sourcing a
replacement.

## Method

Same procedure as prior reviews (see `PLAYBOOK.md`'s "Weekly watchlist
review" section): score current holdings by trailing performance
(real trade P&L where it exists, else a 90-day-hourly `backtest.py` pass
against real historicals), rank worst-case-first, and only consider
sourcing/backtesting a replacement if a real removal candidate exists.

Current positions checked via `get_crypto_positions`/`get_equity_positions`
(2026-10-11 ~18:10 UTC): **zero crypto positions**, one equity position
(`ULTY`, 2 shares — the income sleeve, out of scope for this review).

## Crypto: WATCHLIST

`WATCHLIST = [BTC, ETH, SOL, DOGE, LIT, BCH, AERO, HBAR, DOT, CRV, ZORA,
LINK, AVAX, ASTER, XLM]`. All crypto scan/classify/trading activity has
been cut entirely since 2026-10-08 per explicit owner request, and as of
this review there is no open crypto position of any kind (AERO closed
since the last review). A watchlist swap has no operational meaning
while trading is cut — there is nothing to buy or sell differently. No
scoring, no candidate screen, and no backtest were run this week; this
is a deliberate scope decision, not an oversight. **Revisit this section
in full the first week crypto trading is re-authorized.**

## Stocks: STOCK_WATCHLIST

`STOCK_WATCHLIST = [TWLO, ILMN, PTC, CRWD, PANW]` (trimmed from 10 to 5
on 2026-10-06 — see `watchlist_review_2026-10-06_stocks_top5.md`). None
of the 5 has real trade history yet, so all are scored by `backtest.py`
at production settings (SMA(10,30), `fee_pct=0.001`), real hourly
historicals, 2026-07-13T14:00Z–2026-10-11 (384 bars), split at the
midpoint for H1/H2:

| Symbol | Full return | H1 | H2 | Worst (split) | Max DD | Trades |
|---|---|---|---|---|---|---|
| **TWLO** | +32.38% | +20.73% | **+3.71%** | **+3.71%** | 7.72% | 15 |
| ILMN | +24.80% | +18.51% | +6.71% | +6.71% | 7.78% | 12 |
| PTC | +50.62% | +10.58% | +34.86% | +10.58% | 9.32% | 11 |
| CRWD | +31.01% | +11.41% | +23.56% | +11.41% | 8.70% | 13 |
| PANW | +21.66% | +11.93% | +14.22% | +11.93% | 8.93% | 12 |

**No removal candidate exists.** Every name's worst-case split-window
return is positive — TWLO is the weakest at +3.71% worst-case, but that
is a real gain, not a loss, and this project's standing rule only
proposes sourcing a replacement for a *genuinely underperforming* name
(see every prior review's decision rule). A mechanical "always replace
the bottom one" swap is explicitly not the standard here. With no
removal candidate, no addition-candidate screen or backtest was run this
week — there is nothing to compare a sourced candidate against.

**Also worth repeating from the 2026-10-06 trim doc**: at exactly 5
names, `max_concurrent_positions=5` is no longer a binding constraint on
this list (5 names, 5 slots) — a fact that doesn't change this week's
decision, but is relevant context if the list is ever widened again.

## Decision

**No change recommended this week**, for both watchlists — crypto
because trading is fully cut and a swap would be inert, stocks because
no current name is underperforming enough to source a replacement for.
`WATCHLIST` and `STOCK_WATCHLIST` are unchanged. No `config.py` edit was
made. No order was placed, previewed, or cancelled at any point in this
review.
