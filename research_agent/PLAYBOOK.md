# Research cycle playbook

The runbook an agent session follows on each research cycle. Requires the
`robinhood-trading` MCP server (same connection the trading agent uses).
Run once per weekday, before market open (~8am ET) — news and SEC
filings don't change hour to hour the way price does, so this doesn't
need the trading agent's hourly cadence.

**Scope: stocks only.** `research_agent.config.WATCHLIST` is imported
directly from `trading_agent.config.STOCK_WATCHLIST` — the crypto
watchlist is out of scope for v1 (see README.md's "Known gap: crypto").

## Steps, per cycle

1. **Load config.** `WATCHLIST`, `LOOKBACK_DAYS`, `NEWS_LIMIT`,
   `FORM_TYPES`, `EARNINGS_LOOKAHEAD_DAYS` from `research_agent/config.py`.

2. **For each symbol in `WATCHLIST`:**

   a. **News.** Call `get_equity_news(symbol, limit=NEWS_LIMIT)`. It
      returns `articles: [{id, title, publisher, preview_text, content,
      published_at, source_type}]`, newest first. Before logging
      anything, call `ResearchLogStore().entries_for_asset(symbol)` and
      collect every `article_ids` list already logged for this symbol
      (news entries store a *list* of covered ids, not a single one) —
      `get_equity_news` returns *recent* articles each call, not just
      new ones since the last run, so without this check the same
      article gets re-logged every day it stays in that recent window.
      Filter to articles whose `id` is NOT already covered. If none are
      new, log nothing for this symbol. If one or more are new, write
      **one consolidated entry**, not one entry per article — synthesize
      a single 2-3 sentence summary of what's new across those articles
      (the real signal: price moves, analyst rating/target changes,
      earnings results, material announcements; skip pure filler like
      "$1000 invested N years ago" pieces and mentions where the symbol
      is only feed-tagged, not the subject) and call `record(symbol,
      "news", <consolidated summary>, article_ids=[<ids of every new
      article covered>], article_count=<count>,
      published_at=<newest covered article's published_at>)`. This
      keeps the log to one compact row per symbol per cycle instead of
      up to `NEWS_LIMIT` rows, which is what was driving excessive
      token use before this was changed (2026-09-24 audit).

   b. **SEC filings.** First check `entries_for_asset(symbol)` for any
      existing `source_type="sec_filing"` entries.
      - **Not yet populated for this symbol (bootstrap case, the first
        cycle that covers it):** call `get_sec_filing_index(symbol,
        form_type=FORM_TYPES)` with **no `since`** — fetch whatever's
        most recent regardless of age — and log **only the single most
        recent filing** (the first result; the tool returns
        most-recent-first) as a baseline entry, so the log has a known
        starting point without pulling the symbol's full filing
        history. An empty result here is expected and not an error for
        a foreign private issuer that files 20-F/6-K instead of
        10-Q/10-K/8-K (e.g. CHKP), or a symbol too newly public to have
        one yet (e.g. MAIR, IPO'd April 2026) — log nothing and move on.
      - **Already populated:** call `get_sec_filing_index(symbol,
        form_type=FORM_TYPES, since=<the latest already-logged
        filed_at>)` to fetch only filings newer than what's logged.
        Dedup by `filing_id` against existing entries as a safety net.
      For each new filing found this way: call `get_sec_filing(filing_id)`
      (no `section`) to get the table of contents, then
      `get_sec_filing(filing_id, section=<id>)` for the section(s) that
      look substantive (skip boilerplate cover pages); summarize in 1-3
      sentences what it discloses. **8-K filings get priority
      attention** — that's the "material event" form type most relevant
      to a sudden price move (an 8-K explains *why*, after the fact, the
      way an earnings-date flag explains *when*, in advance). Call
      `record(symbol, "sec_filing", <summary>, form_type=form_type,
      filing_id=filing_id, filed_at=date_filed)` — one entry per filing
      is fine here, unlike news, since new filings are rare per cycle.

   c. **Upcoming earnings.** Call `get_earnings_results(symbol)`. Find
      the last entry where `eps.actual` is `null` (the not-yet-reported
      quarter — entries are ascending, so it's the last one). If
      `report.date` falls within `EARNINGS_LOOKAHEAD_DAYS` of today,
      call `record(symbol, "earnings_upcoming", <one sentence, include
      report.verified status if false — "date not yet confirmed">,
      report_date=report.date, timing=report.timing,
      estimate_eps=eps.estimate)`. Skip silently if no unreported quarter
      is within the window (the common case) — this is the direct
      response to `backtest_2026-09-23.md`'s finding that HUBS gapped
      -20.01% overnight on an earnings reaction with no advance flag.

3. **Build and write the daily digest.** Call
   `research_agent.research_log.ResearchLogStore().entries_for_date(today)`
   (today = current UTC date), then
   `research_agent.daily_digest.format_daily_digest(entries, today)`,
   and write the result to `research_agent/research_notes/<today>.md`.

4. **Commit and push.** `git add research_agent/research_notes/<today>.md
   && git commit` on the current branch, one-line message summarizing
   the day (e.g. "Research digest 2026-09-24: 1 8-K (HUBS), CRWD reports
   in 9 days"), then push.

5. **Notify only if something material was found** — a new SEC filing
   (especially an 8-K) or an earnings date newly inside the lookahead
   window. One `PushNotification`, under 200 characters, naming the
   asset and what was found. Stay quiet on an ordinary day with only
   routine news — matches the trading agent's own notification
   discipline (see `trading_agent/PLAYBOOK.md`'s scanner cycle).

## Hard rules

- Never place, preview, or cancel an order. This agent only reads
  market/news/filing data and writes to `research_agent/research_log.json`
  and `research_agent/research_notes/`.
- Never modify `trading_agent/config.py`, `RISK_LIMITS`, `WATCHLIST`, or
  `STOCK_WATCHLIST` — this agent reads the stock watchlist, it doesn't
  own or change it.
- Always check `entries_for_asset`/`entries_for_date` for existing
  `article_ids`/`filing_id` values before calling `record()` for news or
  a SEC filing — re-scanning the same recent window every day without
  this check would flood the log with duplicates.
- News is logged as one consolidated entry per symbol per cycle, not one
  entry per article — see step 2a. This keeps the log (and the tokens
  spent reading it back) proportional to the watchlist size, not to
  `NEWS_LIMIT`.
- Crypto (`trading_agent.config.WATCHLIST`, the non-stock list) is out
  of scope — never call an equity-only tool (`get_equity_news`,
  `get_sec_filing_index`, `get_earnings_results`) with a crypto symbol.
