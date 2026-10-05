# Profitability gate: re-tested at current settings, net of transaction costs (2026-09-29)

Owner-requested follow-up to the 2026-09-29 ChatGPT second-opinion review
(Slack `#voltrap-agents-work`), which flagged that the original gate
decision (`backtest_2026-09-28_sell_cross_profit_gate.md`) had two real
gaps: (1) it ran at the *old* 10%/20% stop-loss/take-profit, before the
tighter 4%/8% + 24-hour gate floor were adopted later the same day, and
(2) neither pass modeled transaction costs/slippage, flagged as an
unaddressed limitation in every backtest doc since. This re-runs the same
gate A/B comparison (no gate vs. the current live config: gate at 0%
breakeven + a 24-hour time floor) at the *current* production settings,
with a transaction-cost model added for the first time.

## What was built

`fee_pct` parameter added to `backtest.py` and `portfolio_backtest.py`
(default `0.0`, unchanged pre-existing behavior) - a round-trip friction
applied at every fill: a buy converts less cash into quantity than the
raw price implies, a sell returns less cash than the raw price implies,
and the effective cost basis used for stop-loss/take-profit thresholds
includes the entry-side fee (so a tight stop-loss can trigger fractionally
sooner under cost, matching real economics). This is a flat approximation
of bid/ask spread and slippage, not real fee data - Robinhood crypto/stock
orders observed live this session mostly show $0 explicit commission, so
the real cost is spread from marketable-limit fills, which this proxies
as a symmetric haircut on both sides of a trade. Full test suite green
(245/245, 7 new tests) before running any of the below.

## Method

Real hourly data, `get_equity_historicals`, 2026-06-29 to 2026-09-28 (384
bars, split-adjusted, regular hours) for the current `STOCK_WATCHLIST`
(`CRWD, PANW, TWLO, ILMN, IR, PTC, CRDO, MAIR, AR, PYPL`) plus `IBIT`/
`ETHA` (BTC/ETH proxies - crypto itself has no historicals source). Split
H1/H2 (192 bars each) for worst-case-first ranking, same convention as
every other backtest in this project. Production strategy settings
throughout: SMA(10,30), `min_strength_pct=0`, `cooldown_bars=4`, and the
**current live** stop-loss/take-profit (4%/8%, 70% partial) - the
tightened values adopted after the original gate backtest, not the old
10%/20% it actually used.

Two variants compared: **no gate** (`min_sell_profit_pct=None`) vs.
**current live** (`min_sell_profit_pct=0.0`, `gate_max_hold_bars=24`).
Three `fee_pct` levels: 0% (frictionless, matches the original backtest's
assumption), 0.05%, and 0.15% per fill (0.1%-0.3% round trip) - not real
fee data, a sensitivity check on a plausible spread/slippage range. Both
isolated (`backtest.py`, all 12 series) and portfolio-level
(`portfolio_backtest.py`, stocks and crypto-proxy separately, production
risk settings: `max_position_pct=20%`, `max_concurrent_positions=5`,
`max_aggregate_pct=60%`, `max_trades_per_day=4`) passes run at every fee
level, per this project's standing "isolated can reverse at the portfolio
level" rule.

## Pass 1: isolated single-asset, worst-of-H1/H2 pattern holds across fee levels

| Symbol | No-gate Full (0%/0.05%/0.15% fee) | Gated Full (0%/0.05%/0.15% fee) |
|---|---|---|
| CRWD | +5.65% / +9.02% / +8.15% | +2.78% / +6.06% / +5.21% |
| PANW | +13.18% (flat across fees) | +13.18% (flat - never trades differently) |
| TWLO | +1.81% / +1.20% / +0.16% | **+35.80% / +35.12% / +34.00%** |
| ILMN | +11.07% / +10.20% / +8.49% | +26.92% / +26.43% / **+14.74%** |
| IR | -2.53% / -3.02% / -3.99% | +5.09% / +4.73% / +4.70% |
| PTC | -4.93% / -5.69% / -6.58% | -2.63% / +1.96% / +0.94% |
| CRDO | +3.60% / +2.90% / +1.50% | +15.67% / +15.00% / +13.66% |
| **MAIR** | **-18.26% / -18.43% / -19.48%** | **-24.84% / -25.00% / -25.97%** |
| AR | +2.53% / +1.92% / +0.70% | +4.76% / +4.70% / +3.66% |
| PYPL | +14.70% / +13.84% / +12.14% | +20.61% / +20.43% / +18.87% |
| IBIT | +10.42% / +9.65% / +8.12% | +12.03% / +11.36% / +10.03% |
| ETHA | +17.00% / +16.19% / +14.57% | +27.35% / +26.71% / +20.99% |

**MAIR's isolated cost under the gate is real and reproduces at every fee
level** (-18% to -20% baseline vs. -25% to -26% gated) - the same
mechanistic finding as the original backtest: a persistently declining
asset rides out full stop-loss cycles instead of exiting earlier via an
ungated death-cross. Not new evidence; a re-confirmation. Every other
series either benefits from the gate or is unaffected (PANW never sees a
different signal path either way). ILMN shows the most fee-sensitivity of
any gated series (+26.9% at 0% fee down to +14.7% at 0.15% fee) - more
round trips under the gate compounds cost drag more there than elsewhere,
worth naming even though it doesn't flip the conclusion.

## Pass 2: portfolio-level (the binding metric) - gate wins clean, no reversal, at every fee level

**Stock portfolio (10 names, shared cash pool):**

| Fee | Variant | Full | H1 (worst) | H2 | Max DD (Full) | # trades |
|---|---|---|---|---|---|---|
| 0.00% | No gate | +2.87% | **-4.07%** | +2.78% | 7.44% | 101 |
| 0.00% | **Gated** | **+10.38%** | **+5.76%** | -0.45% | **5.55%** | 75 |
| 0.05% | No gate | +2.14% | -4.44% | +3.15% | 7.79% | 101 |
| 0.05% | **Gated** | **+10.31%** | **+5.64%** | -0.40% | **5.86%** | 74 |
| 0.15% | No gate | +0.73% | -5.17% | +2.61% | 8.49% | 101 |
| 0.15% | **Gated** | **+8.43%** | **+4.58%** | -0.75% | **5.77%** | 82 |

**Crypto-proxy mini-portfolio (IBIT+ETHA):**

| Fee | Variant | Full | H1 (worst) | H2 | Max DD (Full) | # trades |
|---|---|---|---|---|---|---|
| 0.00% | No gate | +5.58% | -1.41% | +1.06% | 3.44% | 31 |
| 0.00% | **Gated** | **+7.69%** | **+0.84%** | +0.63% | **1.68%** | 25 |
| 0.05% | No gate | +5.28% | -1.57% | +0.98% | 3.54% | 31 |
| 0.05% | **Gated** | **+7.45%** | **+0.75%** | +0.55% | **1.69%** | 25 |
| 0.15% | No gate | +4.69% | -1.88% | +0.82% | 3.77% | 31 |
| 0.15% | **Gated** | **+6.21%** | **-0.15%** | +0.39% | **2.20%** | 27 |

**This is a materially cleaner result than the original 2026-09-28
backtest.** At the tighter 4%/8% stop-loss, the gate now wins on
worst-case (H1) in stocks too, not just full-period mean - +5.76% vs.
-4.07% at 0% fee, a real reversal of a losing window into a winning one,
holding (+4.58% vs. -5.17%) even at the highest fee level tested. Max
drawdown is lower for the gated variant in every stock scenario. Crypto
shows the same pattern. The one soft spot: stocks H2 slightly favors
no-gate (-0.45% vs. +2.78% at 0% fee) - reported plainly, not hidden,
though it's a small gap relative to H1's much larger swing.

**Trade count matters for costs, and the gate has fewer trades.** Gated
runs 74-82 stock trades vs. no-gate's flat 101 across every fee level -
the gate reduces whipsaw re-entry cycles (fewer death-cross-then-cooldown-
then-re-entry loops), which is itself a cost-reduction mechanism separate
from the P&L-timing effect: fewer round trips means less cumulative fee
drag compounds against the gated variant as `fee_pct` rises, part of why
its lead over no-gate narrows only modestly (not sharply) at the highest
fee level tested.

## Decision: current live gate configuration re-confirmed, not changed

No parameter change from this doc - `profit_gate.MIN_SELL_PROFIT_PCT=0.0`
and `GATE_MAX_HOLD_HOURS=24` were already live (adopted 2026-09-28,
`CHANGELOG.md`). This re-test exists to answer ChatGPT's specific concern
("test the same entry stream with immediate bearish exits versus current
gate/timer, net of costs") with real evidence at the actual current
settings, not the superseded ones. **The result reinforces the original
decision rather than calling it into question**: the portfolio-level
worst-case win is larger and cleaner under 4%/8% than it was under
10%/20%, and it holds up under every transaction-cost assumption tested
(0% to 0.15% per fill, 0.1%-0.3% round trip).

MAIR's isolated weakness under the gate is real, reproduced, and already
a known, accepted tradeoff (see the original doc's "Why MAIR gets worse
under the gate" section) - it is also independently a chronic
underperformer already flagged for `STOCK_WATCHLIST` removal
consideration, not an argument specific to this gate.

## What this doesn't establish

- Same standing crypto-data gap as every other backtest here: IBIT/ETHA
  are proxies, not the actual traded pairs.
- `fee_pct` is a flat symmetric approximation, not real bid/ask spread
  data (which this project has no source for) - it's a sensitivity check
  on plausible values, not a precise cost model.
- Does not re-test `TAKE_PROFIT_SELL_FRACTION` (70%, held fixed) or the
  gate's own threshold/floor values (0%/24h) against neighboring values
  at this new fee model - only the binary gate-on/gate-off question ChatGPT
  specifically asked about.
- Stocks H2's mild edge toward no-gate is a real, if small, finding this
  doc doesn't explain mechanistically - worth revisiting if it recurs in
  a future re-test window.
