# Crypto watchlist: meme-coin removal — 2026-09-23T UTC

Owner asked to "get out of meme coins and into stable coins that has a
future." Clarified via AskUserQuestion: literal stablecoins (USDC/USDT)
are pegged to $1 and don't move enough for an SMA-crossover strategy to
trade, so the owner chose the recommended interpretation - swap the
meme-coin cluster for blue-chip/established crypto that still has real
price movement to trade.

**No sell orders were needed.** The account held zero open crypto
positions at the time (confirmed via `get_crypto_positions` - $0 crypto
value, 100% cash), so this was a pure watchlist swap, not a liquidation.

## Method

Same top-10-by-SMA(10,30)-1h-crossover-strength methodology as
`watchlist_2026-09-22.md` (the original crypto screener) and
`watchlist_stocks_2026-09-23.md` (the stock screener) - not hand-picked.
The only change: an exclusion list applied to the 49-pair universe first,
to remove meme/joke/political coins and the one true stablecoin before
ranking:

`DOGE, SHIB, PEPE, WIF, BONK, FLOKI, MEW, POPCAT, PNUT, MOODENG, TRUMP,
PENGU, WLFI, USDC`

(DOGE - Dogecoin, the origin meme coin; SHIB/PEPE/WIF/BONK/FLOKI/MEW/
POPCAT/PNUT/MOODENG - animal/joke-themed tokens; TRUMP/WLFI - political
tokens; PENGU - NFT-collectible-themed; USDC - a genuine dollar-pegged
stablecoin, excluded because it has no meaningful price movement for a
momentum strategy to trade, not because it's a meme.)

## Top 10 by crossover strength (blue-chip-eligible universe)

| Rank | Symbol | Name | Crossover % |
|---|---|---|---|
| 1 | LIT | Lighter | +3.98% |
| 2 | BCH | Bitcoin Cash | +3.68% |
| 3 | XCN | Onyxcoin | +3.44% |
| 4 | HBAR | Hedera | -2.54% |
| 5 | DOT | Polkadot | -2.52% |
| 6 | CRV | Curve | -2.20% |
| 7 | ZORA | Zora | +1.94% |
| 8 | LINK | Chainlink | -1.90% |
| 9 | AVAX | Avalanche | -1.73% |
| 10 | ASTER | Aster | -1.72% |

## Required core assets (unchanged pattern, DOGE dropped)

BTC, ETH, SOL kept as the required "core" carve-out regardless of
crossover rank, same as the original watchlist's BTC/ETH/SOL/DOGE
carve-out - DOGE simply no longer qualifies as "core" given the explicit
meme-coin removal request.

## Net effect on WATCHLIST

```
Before: BTC, ETH, SOL, DOGE, PEPE, WIF, BONK, PENGU, FLOKI, XCN, MEW,
        POPCAT, SHIB, PYTH, XLM
After:  BTC, ETH, SOL, LIT, BCH, XCN, HBAR, DOT, CRV, ZORA, LINK, AVAX,
        ASTER, PYTH, XLM
```

Same size (15 assets). PYTH and XLM untouched - both already non-meme,
added 2026-09-22 for unrelated reasons (PYTH has no scanner coverage;
XLM's inclusion predates this pass). XCN was already on the old list too
(it independently re-ranked into the new top 10 on its own merits, not
carried over) - unlike the other 8 removed names, it isn't actually a
joke/meme token (Onyxcoin is a payments-focused L1), it just happened to
appear in the original unfiltered 2026-09-22 screener alongside the memes.

## Scope note: no config value beyond WATCHLIST touched

RISK_LIMITS, STRATEGY, and the stock watchlist are unaffected by this
pass - purely a crypto ticker-list swap.
