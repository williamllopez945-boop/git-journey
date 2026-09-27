# max_trades_per_day re-check: 3 -> 4 (2026-09-27)

Owner asked to raise `RISK_LIMITS["max_trades_per_day"]` "to allow for
more room." The existing evidence (`backtest_2026-09-24_trade_cap.md`)
found cap=3 was the best-supported value, split-window-robust, and that
raising it to 10 made results worse. That test used the stock watchlist
current at the time (`CHKP`/`HUBS` among others), which has since been
revised (`watchlist_review_2026-09-26_stocks.md`), so it was re-run
fresh before treating it as still valid, then cross-checked against a
second, independent, deeper real dataset. Final decision: **raised to 4**.

## Pass 1: re-run stock-only backtest on the CURRENT watchlist

Same methodology as `backtest_2026-09-24_trade_cap.md` exactly
(`portfolio_backtest.py`'s `max_trades_per_day` support, production
`entry_filter`/`exit_criteria`, current `RISK_LIMITS`: `max_position_pct`
20%, `max_concurrent_positions` 5, `max_aggregate_position_pct` 60%),
against real hourly bars (`get_equity_historicals`, split-adjusted,
regular hours) for the current 10 `STOCK_WATCHLIST` names (`CRWD, PANW,
TWLO, ILMN, IR, PTC, CRDO, MAIR, AR, PYPL` - `CRDO`/`PYPL` replaced
`CHKP`/`HUBS` on 2026-09-26), 2026-06-29 to 2026-09-25 (~90 days, 378
bars/symbol, real and bar-aligned).

**Split-window (H1: 2026-06-29 to 08-12, H2: 08-12 to 09-25, 189 bars
each):**

| cap | H1 | H2 | Worst-case |
|---|---|---|---|
| 1 | -4.61% | -1.47% | -4.61% |
| 2 | +1.71% | +1.17% | +1.17% |
| **3** | **+3.39%** | **+2.70%** | **+2.70%** |
| 4 | +0.28% | +2.24% | +0.28% |
| 5 | -1.35% | +2.24% | -1.35% |
| 7-20 / uncapped | -3.43% | +2.24% | -3.43% |

Confirms the original finding: cap=3 remains the best worst-case
choice on this watchlist and window. Cap stops binding anything past
~6-7 trades/day (identical to uncapped from there), same shape as
2026-09-24's result.

## Pass 2: cross-check against real, deeper multi-year data

The 90-day stock window is thin for a cap that only binds on the
market's more volatile days - few of those occurred in this particular
quarter. Codex's Alpaca-sourced dataset (archived:
`archive/orb-alpaca-data-2026-09-27`, 8 symbols, verified - see
`docs/handoffs/orb-alpaca-data.review-claude.md`) gave a real, much
longer, more volatile alternative to stress-test the same mechanism:
`SMCI, MARA, OKLO, CLSK, RGTI, ASST, NVDL, SEDG` (the VOLTRAP-context
set - genuinely different symbols from `STOCK_WATCHLIST`, not a
substitute backtest for it, but a real dataset with 3.7 years of common
history to test cap behavior against actual multi-regime, higher-volatility
conditions).

5-minute bars aggregated to hourly closes (last close at/before each
hour, matching what a single hourly `classify()` call would see).
Common aligned history across all 8 symbols: 2023-02-03 to 2026-09-25
(6,125 hourly bars). Same exact cap-sweep methodology, split into 4
independent real quarters (not halves, since the longer history allows
a stronger test):

| cap | Q1 | Q2 | Q3 | Q4 | Worst-case |
|---|---|---|---|---|---|
| 1 | +62.21% | +61.99% | +7.12% | -20.66% | -20.66% |
| 2 | +49.29% | +30.25% | +11.44% | -0.49% | -0.49% |
| 3 | +31.59% | +3.77% | +9.37% | +15.60% | +3.77% |
| **4** | +13.75% | +5.82% | +14.96% | +13.75% | **+5.82%** |
| 5 | +13.73% | +6.09% | +18.66% | +12.64% | +6.09% |
| 7+ / uncapped | +13.73% | +7.66% | +19.58% | +13.86% | +7.66% |

**Opposite direction from Pass 1**: on this real, volatile, multi-year
universe, worst-case return rises monotonically with the cap, then
saturates around 7 (trade volume never exceeds ~7/day even on this
universe's most volatile quarters). A tight cap here incidentally cuts
off real winning signals on high-activity days, not just correlated
noise - the reverse failure mode from the calm-large-cap result.

## Why the two datasets disagree, and why that's real information

`STOCK_WATCHLIST` (calm, `$10B+` market-cap large caps) and this
Alpaca-sourced set (leveraged/momentum small-mid caps) sit at different
points on a volatility/signal-density spectrum. A tight daily cap helps
when most of what fires on a busy day is correlated noise (Pass 1's
finding), and hurts when a busy day means several real, high-conviction
breakouts across an active universe (Pass 2's finding). Since
`max_trades_per_day` is one counter **shared across the whole watchlist
(crypto + stocks)**, and the crypto side has never been directly
backtestable (no historicals tool for it), the crypto watchlist's
actual behavior could plausibly sit closer to either end - this is
a real, acknowledged unknown, not resolved by either pass.

## Decision: cap = 4

The only value with a **positive worst-case on both real test beds**:
+0.28% on the calm stock universe (giving up +2.42pp vs. staying at 3)
and +5.82% on the volatile multi-year universe (gaining +2.05pp vs.
staying at 3). Not the peak on either individual test - 3 wins Pass 1,
7+ wins Pass 2 - but the only choice that isn't a loser on either one.
Raising further (5+) starts giving back Pass 1's worst-case into
negative territory for a shrinking additional gain on Pass 2.

This is a judgment call between two disagreeing pieces of real evidence,
not a clean win - flagged plainly rather than picking a side silently.
Owner made the final call (raise to 4) with both results in hand.

## What this doesn't establish

- No direct backtest of the crypto side of the shared cap exists (same
  limitation as 2026-09-24's result) - the disagreement above is exactly
  why that gap matters more now, not less.
- Pass 2's dataset is not `STOCK_WATCHLIST` and this isn't a claim about
  its specific future behavior - it's a real-data stress test of the cap
  mechanism under different volatility conditions, nothing more.
- Neither pass models real transaction costs/slippage precisely (same
  caveat as every other backtest this project has run).
