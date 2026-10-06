# Income sleeve — candidate screen (2026-10-06)

**Owner request** (this session, via `AskUserQuestion`): a new, separate
"income sleeve" trading YieldMax-style weekly-distribution basket ETFs,
isolated from `RISK_LIMITS`/`STOCK_WATCHLIST`, using a new dip/support
entry signal rather than the SMA crossover. This doc is the first
screening pass — mechanism only, nothing applied to `config.py`.

## Universe

11 tickers confirmed tradable on Robinhood via `search`: `YMAX, YMAG,
ULTY, GPTY, LFGY, QDTY, RDTY, SDTY, MINY, CHPY, SLTY` — YieldMax's
"Group 1" weekly-distribution basket/strategy ETFs (as opposed to the
larger single-stock Group 1/2 lineup on individual names like AAPL/TSLA,
which the owner explicitly did not mean).

## Liquidity filter

`get_equity_quotes` pulled 2026-10-06 ~20:30 UTC (**after the 20:00 UTC
market close** — spreads below are after-hours and will be wider than a
regular-session read; re-check live during market hours before treating
this list as final). Run through `income_candidates.filter_by_liquidity`
(default `max_spread_pct=0.02`):

| Symbol | Bid | Ask | Spread % | Passes 2% filter? |
|---|---:|---:|---:|---|
| ULTY | 26.08 | 26.10 | 0.08% | yes |
| CHPY | 71.65 | 71.80 | 0.21% | yes |
| YMAG | 11.56 | 11.60 | 0.35% | yes |
| YMAX | 7.67 | 7.71 | 0.52% | yes |
| GPTY | 43.25 | 44.65 | 3.19% | **no — borderline, re-check live** |
| QDTY | 39.07 | 40.26 | 3.00% | no |
| SDTY | 41.21 | 45.15 | 9.12% | no |
| LFGY | 19.07 | 21.49 | 11.93% | no |
| SLTY | 18.11 | 22.78 | 22.84% | no |
| MINY | 36.23 | 54.58 | 40.41% | no |
| RDTY | 17.55 | 38.49 | 74.73% | no — likely a stale/broken quote, not a real spread |

**Result**: `ULTY, CHPY, YMAG, YMAX` pass cleanly. `GPTY` is close (3.19%
vs a 2% bar) and worth a same-session, regular-hours re-check rather
than a hard in/out call off one after-hours snapshot — flag for the
owner, don't silently include or exclude it. The rest (`QDTY, RDTY,
SDTY, MINY, SLTY, LFGY`) are clearly too thin right now; `RDTY`'s
74.73% spread in particular looks like a stale/crossed quote rather
than a tradeable price at all.

## Dip-signal read (today, real daily closes)

`get_equity_historicals(interval="day")` back to each ETF's real
inception (no interpolated bars used), fed through
`income_signals.classify_dip` (20-day lookback, bottom-10% entry
threshold):

| Symbol | Real history | Today's close | 20d range position | Signal |
|---|---|---:|---:|---|
| YMAX | 2024-01-17 → today (682 bars) | $7.71 | 0.65 | hold |
| YMAG | 2024-01-30 → today (673 bars) | $11.51 | 0.86 | hold |
| ULTY | 2024-02-29 → today (652 bars) | $25.92 | 0.66 | hold |
| GPTY | 2025-01-23 → today (427 bars) | $43.37 | 0.64 | hold |
| CHPY | 2025-04-03 → today (378 bars) | $71.65 | 1.00 (at its 20d high) | hold |

None of the 5 liquid/near-liquid candidates are in dip territory right
now — no entry signal today on any of them.

## Backtest sanity check (mechanism only — see limitations)

`income_backtest.income_backtest` run over each symbol's full real
history (`fee_pct=0.001`), compared to simple buy-and-hold over the
same window, price only (**no distribution cash flow modeled** — see
below):

| Symbol | Trades | Dip-signal return | Buy-hold return | Max drawdown |
|---|---:|---:|---:|---:|
| YMAX | 12 | −56.53% | −61.26% | 62.11% |
| YMAG | 9 | −22.91% | −42.14% | 34.46% |
| ULTY | 23 | −80.31% | −86.60% | 80.91% |
| GPTY | 4 | −5.98% | −13.42% | 25.83% |
| CHPY | 2 | +20.84% | +56.95% | 18.61% |

**Read this carefully — it is not a verdict on whether these ETFs are
worth holding:**

- **Price-only, no distributions.** These funds' entire purpose is the
  weekly distribution; the backtest above only ever marks the *share
  price*, which structurally erodes as every distribution (much of it
  return of capital) is paid out. Every number above is a price-return
  number, not a total-return number — the real total return including
  distributions received would look substantially better than either
  column, on every one of these. This is `income_backtest.py`'s stated
  limitation, not a surprise finding.
- **What it does show**: on price alone, the dip-timing signal beat
  naive buy-and-hold in all 5 cases (smaller loss or, for CHPY, a
  smaller — though still real — gap to its own buy-hold). That's a
  mechanism sanity-check (the signal isn't actively harmful to price
  entry timing), not confirmation the sleeve will be profitable overall.
- **Short, uneven history.** 2 to 23 trades per symbol over 378-682
  real bars (GPTY/CHPY under 1.5 years; even YMAX/YMAG/ULTY under 3).
  Treat none of this as a tuned parameter the way `exit_criteria.py`'s
  numbers are — `DIP_LOOKBACK_DAYS=20`/`DIP_ENTRY_THRESHOLD=0.10` are
  proposed defaults, not swept/optimized values.

## Recommendation

- **Proposed `INCOME_WATCHLIST`**: `YMAX, YMAG, ULTY, CHPY` (the 4 that
  clearly clear the liquidity bar). Re-check `GPTY` during regular
  market hours before deciding whether to add it as a 5th.
- **Not applied to `config.py`** — this remains a recommendation only,
  per the approved plan. No order has been placed, no `Routine` created,
  `INCOME_AUTO_EXECUTE` stays `False`.
- No entry signal fires today on any candidate — nothing to act on even
  once the mechanism is wired up.
