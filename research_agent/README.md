# Research agent

A separate agent whose sole job is to scan news and SEC filings for the
stocks the trading agent (`trading_agent/`) trades, and log findings to
a file the trading agent can reference for extra context. It never
places, previews, or recommends a trade itself, and it never generates
a buy/sell signal of its own — advisory research support, not a second
strategy. Built 2026-09-23 per owner request: "an additional agent
that's sole job is to conduct research and analysis of our crypto and
stocks based on news sources and SEC filings," scoped down to stocks-only
via AskUserQuestion (see "Known gap: crypto" below) with the explicit
design goal "the trading agent can reference the research to support its
decisions" — a loose, file-based coupling, not a trade gate.

## What's here

| File | Purpose |
|---|---|
| `config.py` | Research-specific settings (lookback windows, news limit, filing form types, earnings lookahead). The watchlist itself is imported directly from `trading_agent.config.STOCK_WATCHLIST` — never duplicated, so it can't drift out of sync when the trading agent's watchlist changes |
| `research_log.py` | `ResearchLogStore` — append-only log of findings (news/SEC filings/upcoming earnings), persisted to `research_log.json`. Modeled directly on `trading_agent/cycle_log.py`'s `CycleLogStore` |
| `daily_digest.py` | Assembles the daily research digest markdown from a day's logged findings, grouped by asset |
| `PLAYBOOK.md` | Step-by-step runbook the daily research Routine follows |
| `research_notes/*.md` | Daily digests, one per weekday — durable, versioned record (not gitignored) |
| `tests/` | Unit tests for the log store and digest formatting |

## Data sources (v1: RobinHood's existing tools only, no new APIs)

- `get_equity_news` — recent news articles per symbol
- `get_sec_filing_index` / `get_sec_filing` — filing discovery and
  section text, prioritizing 8-Ks (material events)
- `get_earnings_results` — upcoming earnings report dates, to flag
  earnings-driven gap risk *before* it happens

## Known gap: crypto has no research coverage in v1

RobinHood's news and SEC-filing tools are equity-specific — there is no
analogous tool for crypto (`trading_agent.config.WATCHLIST`) in this
session's toolset, and crypto pairs aren't SEC filers. The owner was
asked explicitly (AskUserQuestion, 2026-09-23) whether to add a
web-search source to cover crypto anyway, and chose to scope v1 to
stocks-only instead. This is a deliberate, documented scope boundary,
not an oversight — revisit if/when a crypto-relevant news source is
added to the toolset.

## How the trading agent uses this

Loosely coupled, deliberately not a gate (see `trading_agent/PLAYBOOK.md`'s
auto-execution policy): when a signal is presented as a **recommendation**
(oversized, awaiting the owner's approval — the one point in the trading
cycle a human is already in the loop), the trading agent calls
`ResearchLogStore().entries_for_asset(symbol, since=<7 days>)` and
includes any hits alongside the recommendation, so research context is
available exactly when a real decision is being made. Bounded
auto-execution (fresh, confirmed signals at/under `auto_execute_max_usd`)
is untouched by this agent — it stays mechanical and deterministic, as
designed and tested throughout the trading agent's own build.

## Schedule

One persistent Routine, weekdays only (no point scanning stock news on a
day the market doesn't open), firing before market open. Separate from
both trading-agent Routines — its own identity and run history, pausable
independently without touching live trading.
