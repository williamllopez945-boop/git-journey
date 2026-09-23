# Stock watchlist: large-cap upgrade — 2026-09-23T UTC

Owner: "Let's look at replacing the small cap stocks with larger ones.
With more confidence, I will add more capital." Same screener
methodology as every other watchlist change this session - not
hand-picked - with the market-cap floor raised from $2B to $10B (price
> $10 and 30d avg volume > 1M unchanged).

## Method

Re-ran the production stock scan (`Stock SMA(10,30) 1h Crossover —
Strategy Screener`, scan_id `6e009dcf-d184-45a7-915f-ccfc50b4e6be`) with
`FILTER_TYPE_MARKET_CAP > $10,000,000,000` in place of the prior $2B
floor. 399 stocks passed. Ranked by `(SMA10-SMA30)/SMA30` crossover
strength, top 10 taken.

## Top 10 by crossover strength (large-cap universe)

| Rank | Symbol | Name | Market cap | Crossover % |
|---|---|---|---|---|
| 1 | AR | Antero Resources | $11.0B | +2.61% |
| 2 | CRWD | CrowdStrike Holdings | $268.8B | +2.58% |
| 3 | ILMN | Illumina | $38.6B | +2.58% |
| 4 | HUBS | HubSpot | $11.3B | +2.57% |
| 5 | CHKP | Check Point Software | $14.4B | +2.56% |
| 6 | IR | Ingersoll Rand | $29.6B | +2.48% |
| 7 | PTC | PTC Inc | $15.2B | +2.47% |
| 8 | TWLO | Twilio | $44.6B | +2.26% |
| 9 | PANW | Palo Alto Networks | $321.7B | +2.24% |
| 10 | MAIR | Madison Air Solutions | $12.7B | +2.24% |

All ten are real, established operating companies (verified via
`get_equity_fundamentals` before adopting), most multi-decade-old,
several mega-cap (PANW $322B, CRWD $269B) - a genuine step up in size
and liquidity from the prior $2B-floor list (GLBE/VVV/TRLV/ESI/CE/BHF/
MDLN/OLLI, mostly $3-9B).

## Backtest validation before switching

Ran the production `portfolio_backtest.py` engine (same code as every
other backtest this session) against real hourly historicals for all 10
candidates, 378 aligned bars, ~90 days through 2026-09-23.

**Per-asset isolated:**

| Asset | Return | Max DD | Trades |
|---|---|---|---|
| ILMN | +9.82% | 13.16% | 16 |
| CRWD | +8.71% | 12.62% | 9 |
| AR | +5.49% | 5.90% | 11 |
| TWLO | +3.95% | 15.77% | 12 |
| PANW | +2.99% | 16.64% | 10 |
| PTC | +0.83% | 13.17% | 16 |
| IR | -2.53% | 10.49% | 10 |
| HUBS | -11.01% | 22.87% | 11 |
| CHKP | -17.66% | 17.96% | 17 |
| MAIR | -17.96% | 23.92% | 13 |

6 of 10 positive standalone (vs 2 of 8 on the prior mid-cap list).

**Combined portfolio** (crypto proxies IBIT/ETHA + these 10 large-caps,
one shared cash pool, production `RISK_LIMITS`): **+9.43% return, 4.94%
max drawdown**, 94 trades, concurrent cap reached during the run. Compare
directly to the prior combined test on the mid-cap list: **-7.64%
return, 11.18% max drawdown** (see backtest_2026-09-23.md). A large,
real improvement on both return and worst-case drawdown over the same
window.

## Honest caveat: market cap does not eliminate gap risk

Checked overnight (close-to-next-open) gaps across the same window, the
same check that led to dropping TNGX/ARQT for biotech binary-catalyst
risk:

| Symbol | Worst overnight gap |
|---|---|
| HUBS | **-20.01%** (2026-08-06, earnings) |
| CHKP | -10.74% |
| MAIR | -8.57% |
| PANW | -7.64% |
| CRWD | -6.43% |
| TWLO | -6.10% |
| AR | -5.20% |
| ILMN | -5.00% |
| PTC | -4.89% |
| IR | -3.68% |

**HUBS's -20.01% gap is larger than MDLN's -15.2% that motivated
dropping the biotechs.** This is a genuinely different risk category,
though, not a reason to exclude HUBS the way TNGX/ARQT were excluded:
TNGX/ARQT carried a *specific, avoidable* single-catalyst bet (an
all-or-nothing clinical trial readout) baked into the entire investment
thesis. HUBS's gap looks like an ordinary earnings reaction - a
universal risk every stock in the market carries (including every name
on the prior list, and the S&P 500 broadly), not a special category to
screen out. It's bounded the same way every position's risk is bounded:
`max_position_pct` (20% of portfolio per name) and the 50% aggregate
cap. The combined backtest above already includes this exact gap event
inside its numbers and still came out well ahead of the mid-cap list -
this isn't a hidden risk, it's a priced-in one.

No name was dropped from this top-10 on a hindsight "it backtested
poorly" basis (HUBS, CHKP, MAIR were the three weakest standalone
performers) - that would be cherry-picking after seeing the result,
the same trap this session has avoided all along (RSI's inert winner,
the volume filter's knife-edge, etc.). The watchlist is exactly what the
screener produced, same as every other watchlist this session.

## Net effect

```
Before: GLBE, VVV, TRLV, ESI, CE, BHF, MDLN, OLLI (8 names, $2B+ floor)
After:  CRWD, PANW, TWLO, ILMN, IR, PTC, CHKP, MAIR, AR, HUBS (10 names, $10B+ floor)
```

No sell orders were needed - zero open equity positions at the time.
The production stock scan's market-cap filter was updated in place
(same scan_id) to $10B going forward, so future re-screens of this
watchlist inherit the higher floor automatically.
