# VOLTRAP watchlist — 2026-09-26 (first standing list)

Owner request: "work on our watchlists" (crypto/options/stocks). This
is the VOLTRAP (options wheel strategy) pass, sibling to
`watchlist_review_2026-09-26_crypto.md` and `_stocks.md` from the same
request.

**Change in kind, not just content:** `VOLTRAP_WATCHLIST` has been
`[]` since VOLTRAP was built (2026-09-26) — populated live from the
candidate scan each cycle, never a persisted list, since the account
wasn't funded yet and there was nothing to stabilize against. The owner
asked for VOLTRAP to get a real watchlist like crypto/stocks, so this
turns it into a **reviewed, standing list of 8 symbols** — re-screened
periodically (same cadence as the other two, once VOLTRAP has its own
Routines), not recomputed from scratch every cycle. The live per-cycle
screen (`PLAYBOOK.md`'s "Candidate screening" section) still runs before
any real order — this list narrows *which underlyings* get a live
strike/chain lookup, it doesn't replace checking real numbers at
trade time.

## Method

Options wheel candidates don't have a return-based backtest the way
SMA-crossover assets do (`backtest.py` tests trend-following entries/
exits — a CSP-selling income strategy has no equivalent event to
simulate without real historical options pricing, which this session
has no source for). The validation method here is different, matching
what the original VOLTRAP build already established:

1. **Screen**: `run_scan` on the tuned candidate scan
   (`e3983260-740b-4a84-8369-54420cbeafdd`, IV between 35-80%, avg
   options volume > 5,000, open interest > 20,000, price > $5, stock/ETF
   only). 395 matches today, sorted `Last asc` — same 200-row pagination
   cap flagged as a known, still-open gap in the 2026-09-26 system audit;
   revisit the sort once the real budget is set (see `CHANGELOG.md`).
2. **Rank**: `voltrap_candidates.rank_by_voltrap_fit` (illustrative
   $100,000 collateral ceiling, well above the real ~$100 budget, purely
   to avoid the live per-cycle collateral filter from distorting a
   *standing* list meant to survive budget changes) — ranks survivors by
   implied volatility descending.
3. **Screen out binary-catalyst and thin-liquidity names** — the same
   check `watchlist_stocks_2026-09-23_large_cap.md` applied to HUBS/CHKP/
   MAIR, done here via `get_equity_fundamentals` on every name that
   wasn't already vetted in the original VOLTRAP build.

## Screened out

| Symbol | Reason |
|---|---|
| SMMT | Summit Therapeutics — clinical-stage biopharma, lead drug (Ridinilazole) in Phase III trials. Same binary-catalyst risk category as TNGX/ARQT, excluded from the stock watchlist for the same reason. |
| PGEN | Precigen — clinical-stage synthetic-biology biotech, same binary-catalyst risk. Also sitting at a 52-week high the same day as its 79.9%→77.5% IV reading — looks event-driven, not a stable premium source. |
| GRRR | Gorilla Technology — real company, but thin (`average_volume` ~497K shares/day, `market_cap` $387M) even though it cleared the *options*-volume/OI floor. Kept off a standing list meant to be durable, not just today's technical pass. |

## Standing list (top 8 by IV/liquidity, biotech/binary-risk and thin names excluded)

| Symbol | Name | Sector | IV | Last | Open interest | Note |
|---|---|---|---|---|---|---|
| SMCI | Super Micro Computer | AI server hardware | 76.7% | $43.27 | 1,671,682 | Best liquidity by far — already vetted in the original VOLTRAP build (real MARA-style pipeline test) |
| MARA | MARA Holdings | Bitcoin mining | 75.8% | $12.53 | 1,116,369 | Already vetted — the original real `review_option_order` test was on this name |
| OKLO | Oklo Inc | Nuclear/SMR | 76.7% | $38.08 | 551,456 | Pre-revenue but a real, publicly-traded operating company; already vetted |
| CLSK | CleanSpark | Bitcoin mining | 76.2% | $13.93 | 509,632 | Established miner, $3.6B market cap |
| RGTI | Rigetti Computing | Quantum computing | 76.9% | $16.70 | 486,194 | Speculative sector but a real company; already vetted |
| ASST | Strive, Inc. | Bitcoin treasury | 75.5% | $29.45 | 384,128 | Leveraged bitcoin exposure via corporate treasury — explicitly in scope per "leveraged stocks are ok" |
| NVDL | GraniteShares 2x NVDA | Leveraged ETF | 77.2% | $35.70 | 153,898 | Leveraged, explicitly in scope; already vetted |
| SEDG | SolarEdge Technologies | Solar inverters | 78.9% | $32.95 | 90,054 | Established ($2.0B) solar-tech company, real operating business |

Diversified across bitcoin-mining/treasury (MARA, CLSK, ASST), AI/tech
hardware (SMCI, NVDL), and two single-name speculative-but-real
industrials (RGTI, OKLO) plus one renewable-energy name (SEDG) — not
all one correlated cluster, similar reasoning to why the crypto
watchlist excludes an all-meme-coin cluster.

## Net effect on VOLTRAP_WATCHLIST (proposed, not yet applied)

```
Before: []  (populated live from the scan each cycle, never persisted)
After:  SMCI, MARA, OKLO, CLSK, RGTI, ASST, NVDL, SEDG
```

## Scope note

`config.py` has **not** been edited — recommendation only, same as the
crypto/stock sibling docs. **Everything else about VOLTRAP's gating is
unchanged**: no real option order, and no Routine, until (a) the owner
confirms `max_voltrap_pct` and (b) the account shows real free cash for
it (`PLAYBOOK.md`'s "VOLTRAP" section). A standing watchlist doesn't
change that — it changes *what gets checked* once funded, not *when*
funding-gating lifts.

`research_agent` will pick up these 8 symbols once this list is
approved — see its own config change in the same commit as this file,
and `research_agent/README.md`'s updated scope note.
