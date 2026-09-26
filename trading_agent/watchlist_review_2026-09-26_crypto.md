# Crypto watchlist review — 2026-09-26

Owner request: "work on our watchlists" (crypto/options/stocks, refresh
with real candidates now). This is the crypto pass — same purpose as
the standing "Weekly watchlist review" Routine (`trig_01HMP6iKVzgmPjwxuA1DdqvE`,
first scheduled firing 2026-09-27), run early/by hand at the owner's
request rather than waiting for Sunday. The Routine still fires as
scheduled; this doc doesn't replace it, just gets ahead of it once.

**Recommendation: one clear swap, no other changes.** Full reasoning
below.

## Method

Same core methodology as every past crypto watchlist doc this project
has produced (`watchlist_2026-09-22.md`, `watchlist_2026-09-23_meme_removal.md`):
rank by SMA(10,30) 1h crossover strength from the live scanner
(`run_scan`, scan_id `8f2ca450-1f7f-4e69-b015-daafe494c14e`, all 49
crypto pairs Robinhood offers, no pagination cap here — 49 < 200).
Crypto still has **no historicals source** (confirmed again this
session), so a real per-asset backtest isn't possible for assets that
never traded — same limitation as every prior crypto watchlist pass.
Two real data sources are added on top of that baseline snapshot,
which weren't fully exploited in past passes:

1. **Real trailing P&L** (`watchlist_review.trailing_trade_pnl`) for any
   asset that's actually been bought/sold this session
   (`RiskManager.state["trade_log"]`) — a real result, not a proxy.
2. **Multi-day signal history** (`cycle_log.json`, 2026-09-23 through
   today) — lets a removal decision be based on a *persistent* pattern
   across many cycles, not one day's snapshot, addressing this
   project's own "check neighbors before trusting one data point" rule.

## Current WATCHLIST members: trailing performance

**Real trade P&L (traded this session):**

| Asset | Status | Realized+unrealized P&L | Verdict |
|---|---|---|---|
| DOT | open (34.256) | +$3.96 | keep — real winner |
| LINK | open (3.058) | +$3.57 | keep — real winner |
| AVAX | open (1.7842) | +$0.62 | keep — real winner |
| HBAR | closed today (see live log, 15:47 UTC) | +$0.04 | keep — flat/small win, clean round trip |

No traded asset shows a loss. Nothing here is a removal candidate on
real P&L grounds, and DOT/LINK/AVAX hold open positions anyway (never
force-removed from a routine review per this project's standing rule —
skip and revisit once flat).

**Never traded (10 of 14) — no real P&L, scored by today's crossover
strength + multi-day signal history instead:**

| Asset | Today's crossover | Multi-day pattern (`cycle_log.json`, 09-23 → today) | Verdict |
|---|---|---|---|
| BTC | +0.03% | required "core" — never removed regardless of rank | keep |
| ETH | -0.12% | required "core" | keep |
| SOL | -0.11% | required "core" | keep |
| CRV | +0.45% | — | keep |
| ZORA | +0.26% | — | keep |
| LIT | -0.12% | Deep bearish streak 09-23→09-25 (-1.0% to -3.6%), now recovering toward flat/slightly positive (+0.08% blocked by aggregate cap on 09-26, -0.01% today) — a genuine bottoming pattern, not a loser | keep, watch |
| ASTER | -0.12% | Bearish 09-23 (-2.4% to -3.0%), narrowing toward -0.23% today — same recovering pattern as LIT, thinner data (only 4 observations) | keep, watch |
| BCH | -0.34% | Only 3 observations (09-25/09-26), mixed (one blocked buy-cross, two sell-crosses) — too thin to call a trend | keep |
| XLM | -0.40% | Genuinely choppy: -4.2% (09-23) → +3.05% (09-24) → -0.09% (today). Oscillating, not persistently bearish — the opposite of a clean removal case | keep |
| **XCN** | **0.00%** | **SMA10 == SMA30 exactly, every single cycle observed (09-25, 09-26), `Volume: 0` in every raw scan row.** This isn't "currently weak," it's a frozen/dead data feed — the crossover strategy structurally cannot ever generate a signal for this asset while its scanner data stays flat at zero volume. | **remove** |

**XCN is the one clear, well-evidenced removal.** Every other
below-median name (BCH, XLM, ASTER) turns out to be noisy/oscillating
rather than persistently weak once the multi-day history is checked —
exactly the kind of single-snapshot false positive this project's own
ranking discipline is meant to catch. No forced swap on ambiguous data;
"no change" is the right call for all of them this week.

## Addition candidate screen

`rank_by_crossover_strength` against all 49 pairs, excluding the current
14-name watchlist and the existing meme/political/stablecoin exclusion
list (`DOGE, SHIB, PEPE, WIF, BONK, FLOKI, MEW, POPCAT, PNUT, MOODENG,
TRUMP, PENGU, WLFI, USDC` — unchanged from `watchlist_2026-09-23_meme_removal.md`):

| Rank | Symbol | Name | Crossover % | Relative volume |
|---|---|---|---|---|
| 1 | AERO | Aerodrome Finance | +5.30% | 1.29 |
| 2 | AVNT | Avantis | +4.90% | 3.22 |
| 3 | ENA | Ethena | +4.49% | 0.55 |
| 4 | XPL | Plasma | +3.30% | 1.07 |
| 5 | MNT | Mantle | +3.00% | 1.31 |

AERO (Aerodrome Finance, a real Base-chain DEX) and AVNT (Avantis, a
real perps-trading protocol) are both legitimate DeFi projects, not
meme/joke/political tokens — same "no hidden meme coin slipping back
in" check `watchlist_2026-09-23_meme_removal.md` applied.

**Same limitation as the original 2026-09-22 construction**: these are
brand-new to this watchlist, so there's no multi-day `cycle_log.json`
history to check persistence against (only watchlist members get
logged every cycle) — this recommendation rests on today's screen
alone, same as every past crypto addition has. Worth a second look in a
week once real cycle data exists for it.

**Recommendation: swap `XCN` → `AERO`.** One clean removal (dead data
feed), one clean addition (top-ranked, real project, replaces it 1-for-1
so watchlist size stays at 14).

## Net effect on WATCHLIST (proposed, not yet applied)

```
Before: BTC, ETH, SOL, LIT, BCH, XCN, HBAR, DOT, CRV, ZORA, LINK, AVAX, ASTER, XLM
After:  BTC, ETH, SOL, LIT, BCH, AERO, HBAR, DOT, CRV, ZORA, LINK, AVAX, ASTER, XLM
```

Same size (14 assets). Only `XCN` → `AERO` changes.

## Scope note

`config.py` has **not** been edited — this is a recommendation only,
per this project's standing rule (a human is in the loop before
`WATCHLIST` changes, never a side effect of an automated review).
Waiting for explicit approval. `RISK_LIMITS`, `STRATEGY`, `STOCK_WATCHLIST`,
and `VOLTRAP_WATCHLIST` are out of scope for this doc (see the sibling
stock and VOLTRAP review docs from the same pass).
