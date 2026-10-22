# Income sleeve candidate expansion — 2026-10-07

**Trigger**: owner request, "Add more yieldmax or another stocks with weekly dividend payout."
Current `INCOME_WATCHLIST` (live since 2026-10-06): `YMAX, YMAG, ULTY, CHPY`. `GPTY` was
screened the same day but excluded on an after-hours spread snapshot (3.19%, over the 2%
liquidity filter) — flagged then for a live re-check during regular hours.

## What was screened

**Re-checked, previously excluded for spread** (`income_candidates_2026-10-06.md`):
`GPTY, LFGY, QDTY, RDTY, SDTY, MINY, SLTY` — all still YieldMax basket/0DTE products.

**New discovery, different issuer**: Robinhood search for "WeeklyPay" surfaced a Roundhill
family not previously considered — one basket fund (`TOPW`, "Top WeeklyPay ETF") and ten
**single-stock, 1.2x-leveraged** weekly payers: `MSTW, AMDW, HOOW, PLTW, ARMW, COIW, GDXW,
TOPW, GLDW, GOOW, NVDW, TSLW`.

Quotes pulled 2026-10-07 ~20:11 UTC (right at/just after the 20:00 UTC close — about as good
a liquidity snapshot as this time of day gets; re-verify intraday before any go-live add,
same caveat as every prior screen here).

## Liquidity (`filter_by_liquidity`, 2% spread threshold, unchanged)

| Symbol | Spread | Passes? |
|---|---|---|
| GPTY | 1.78% | **Yes** (was 3.19% after-hours on 10-06 — clears cleanly now) |
| QDTY | 2.48% | No (just over) |
| LFGY | 10.62% | No |
| RDTY | 19.81% | No |
| SDTY | 9.95% | No |
| MINY | 23.43% | No |
| SLTY | 8.11% | No |
| TOPW | 20.71% | No |
| MSTW | 8.71% | No |
| ARMW | 2.01% | No (just over) |
| GDXW | 9.66% | No |
| GLDW | 2.16% | No (just over) |
| TSLW | 0.11% | **Yes** |
| HOOW | 0.19% | **Yes** |
| COIW | 0.48% | **Yes** |
| PLTW | 0.51% | **Yes** |
| NVDW | 0.52% | **Yes** |
| AMDW | 0.59% | **Yes** |
| GOOW | 0.82% | **Yes** |

All liquid survivors confirmed `distribution_frequency: "Weekly"` via `get_equity_fundamentals`,
ex-dividend 2026-10-05 (Roundhill names, payable 10-06) / 2026-10-07 (GPTY, payable 10-08) —
real weekly cadence, not a labeling fluke.

## Price-only backtest sanity check (`income_backtest.py`, same mechanism/caveats as
`backtest_2026-10-07_income_sleeve_full_history.md` — **no distribution cash flow modeled**,
so this understates real total return; treat as a NAV-erosion sanity check, not a tuned result)

Real daily history, 2025-01-02 → 2026-10-06 (441 bars, ~1.75 years):

| Symbol | Total return | Max drawdown | Trades |
|---|---|---|---|
| GPTY | -5.33% | 25.60% | 4 |
| AMDW | **+89.17%** | 26.67% | 5 |
| GOOW | +16.36% | 17.98% | 2 |
| NVDW | -21.06% | 38.43% | 6 |
| PLTW | -32.52% | 52.84% | 14 |
| HOOW | -31.91% | 56.33% | 15 |
| TSLW | -50.57% | 59.79% | 16 |
| COIW | -65.67% | 74.53% | 24 |

## Observations

**GPTY** is the clean addition: same risk profile as the current holdings (diversified
15-30-stock AI/tech basket, no leverage), now liquid during regular hours, confirmed weekly,
and its price-only backtest result (-5.33%, 25.6% max drawdown) is in the same range as the
existing sleeve's other members, not an outlier. This is the one already flagged as pending
a live re-check — recommend adding it now.

**The Roundhill `WeeklyPay` single-stock funds are a materially different risk shape**, not
just a liquidity question: each one is "1.2x leveraged exposure to the weekly price return of
[one stock]" (own fund description) — single-name concentration *and* leverage, stacked on top
of the same option-income NAV-decay mechanic. The backtest shows it: 5 of 7 tested lost
21-66% of price value over 1.75 years with max drawdowns of 38-75%, and the two apparent
"winners" (AMDW +89%, GOOW +16%) are explained entirely by AMD's and Alphabet's own strong
runs over that window, not a repeatable edge — the same single stock having a bad run instead
(see TSLW/COIW/HOOW/PLTW) erases it. This is exactly the concentration risk this sleeve has
avoided from the start (the original candidate list only ever considered YieldMax's
diversified *basket* funds, never its single-stock monthly payers like MSTY/NVDY/TSLY for the
same reason). Recommend **not** adding any of these to `INCOME_WATCHLIST` without the owner
explicitly accepting that different risk profile — it doesn't fit `INCOME_RISK_LIMITS`'
deliberately conservative, basket-only mandate as currently scoped.

**Still excluded on liquidity** (re-confirmed, no change from 2026-10-06): `LFGY, QDTY, RDTY,
SDTY, MINY, SLTY, TOPW` — all wide-or-crossed even at a good time of day. `QDTY` (2.48%) and
`ARMW`/`GLDW` (2.0-2.2%) are close enough to the 2% line to be worth a fresh look on a future
pass, not close enough to add on this one.

## Decision

**Owner-approved 2026-10-07.** `GPTY` added as recommended. For the Roundhill single-stock
`WeeklyPay` funds, the owner chose to add `AMDW`, `GOOW`, and `NVDW` despite the flagged
leverage/concentration risk — the three candidates with the mildest backtest outcomes of the
seven liquid ones screened (the other four: `TSLW`, `COIW`, `HOOW`, `PLTW` were explicitly
left out, each having lost 32-66% of price value over the same 1.75-year window). `INCOME_WATCHLIST`
is now `["YMAX", "YMAG", "ULTY", "CHPY", "GPTY", "AMDW", "GOOW", "NVDW"]`
(`trading_agent/config.py`). `INCOME_RISK_LIMITS` and `INCOME_AUTO_EXECUTE` were left
unchanged — not part of this request, and `max_concurrent_positions=2` stays a real cap
against 8 names (unlike the stock-watchlist trim, where 5 names against a cap of 5 stopped
being a constraint).
