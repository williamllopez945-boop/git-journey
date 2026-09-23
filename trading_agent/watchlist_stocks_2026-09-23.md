# Stock watchlist snapshot — 2026-09-23T UTC

Extends the trading agent from crypto-only to also trading equities, per
owner request ("Add stocks to the watchlist too" -> "Run a momentum
screener, like the crypto watchlist got"). Same methodology as
`watchlist_2026-09-22.md`'s crypto screener: Robinhood's server-side
`closeAvg` over real hourly candles, this repo's exact strategy parameters
(`STRATEGY.short_window=10`, `STRATEGY.long_window=30` from `config.py`,
interpreted as 1h bars), ranked by crossover strength
`(SMA10 - SMA30) / SMA30`.

## Universe: STOCK, not just "screened all pairs"

Unlike crypto (Robinhood offers a fixed, curated list of 49 pairs, all
liquid), `FILTER_TYPE_INSTRUMENT_TYPE = STOCK` alone matched ~300-400
tickers, and unfiltered the top of that list was dominated by illiquid
penny/micro-cap names (BENF, VTGN, ARTL — sub-$13, thin volume) whose SMA
crossovers are noise from thin trading, not real momentum: a couple of
trades can swing a 10-bar SMA on a name that barely trades. That's not
equivalent to the crypto universe's inherent liquidity floor, so three
quality filters were added before ranking, mirroring standard
momentum-screener practice:

- `Market cap > $2,000,000,000` (mid-cap or larger)
- `Last price > $10` (price floor against penny-stock manipulation/wide spreads)
- `Average volume (1d, 30) > 1,000,000` shares (real daily liquidity)

398 stocks passed these filters at scan time. Scan saved as
`Stock SMA(10,30) 1h Crossover — Strategy Screener`,
scan_id `6e009dcf-d184-45a7-915f-ccfc50b4e6be`, columns: SMA 10 (1h),
SMA 30 (1h), Relative volume, Crossover %.

## Top 10 by crossover strength

| Rank | Symbol | Name | Last | SMA10 (1h) | SMA30 (1h) | Crossover % | Rel. volume |
|---|---|---|---|---|---|---|---|
| 1 | TNGX | Tango Therapeutics | $24.40 | 25.142 | 23.965 | +4.91% | 1.12x |
| 2 | GLBE | Global-E Online | $41.605 | 41.658 | 40.018 | +4.10% | 0.31x |
| 3 | VVV | Valvoline | $28.50 | 28.557 | 27.470 | +3.96% | 0.65x |
| 4 | ARQT | Arcutis Biotherapeutics | $26.39 | 27.357 | 26.377 | +3.71% | 0.85x |
| 5 | TRLV | Trulieve Cannabis | $12.54 | 12.397 | 11.960 | +3.65% | 1.55x |
| 6 | ESI | Element Solutions | $35.68 | 35.211 | 34.032 | +3.46% | 1.29x |
| 7 | CE | Celanese | $49.0975 | 48.190 | 46.628 | +3.35% | 1.32x |
| 8 | BHF | Brighthouse Financial | $52.16 | 52.391 | 50.775 | +3.18% | 0.33x |
| 9 | MDLN | Medline Inc. Class A | $34.28 | 34.098 | 33.049 | +3.17% | 0.42x |
| 10 | OLLI | Ollie's Bargain Outlet | $82.98 | 82.852 | 80.337 | +3.13% | 1.04x |

No "required assets" step here (unlike crypto's BTC/ETH/SOL/DOGE
carve-out) — the owner asked for a pure momentum screener with no
hand-picked tickers, so the top 10 above is the whole list.

## Scope decisions carried into the live system

- **Shared risk budget** (owner's explicit choice): stocks and crypto draw
  from the same `RISK_LIMITS` — one `max_aggregate_position_pct` (50%), one
  `max_trades_per_day`, one `max_concurrent_positions` cap spanning both
  asset classes combined, not separate pools. See `config.py` and
  `PLAYBOOK.md`.
- **Market-hours gating**: unlike crypto (24/7), equities only fill
  reliably during regular hours (9:30-16:00 ET) with market/stop orders;
  outside regular hours only limit orders execute. v1 scope: the stock
  scanner cycle only evaluates and acts during regular market hours -
  extended-hours trading is a possible future enhancement, not implemented
  here.
- **No cost-basis fallback needed (yet)**: `get_equity_positions` returns
  `average_cost` directly per position, unlike crypto's observed
  `cost_bases` gap (see README's "Known gap: cost basis"). Not
  pre-emptively adding equivalent fallback machinery for a problem that
  hasn't been observed on the equity side.
