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
      collect the `article_id` values already logged for this symbol —
      `get_equity_news` returns *recent* articles each call, not just
      new ones since the last run, so without this check the same
      article gets re-logged every day it stays in that recent window.
      For each article whose `id` is NOT already logged, call
      `record(symbol, "news", <preview_text or a 1-sentence summary of
      content>, headline=title, publisher=publisher, article_id=id,
      published_at=published_at)`.

   b. **SEC filings.** Call `get_sec_filing_index(symbol,
      form_type=FORM_TYPES, since=<today - LOOKBACK_DAYS>)`. It returns
      `filings: [{filing_id, form_type, description, date_filed}]`.
      Check `entries_for_asset(symbol)` for `filing_id`s already logged
      (same dedup reasoning as news — a filing stays inside the lookback
      window across multiple runs). For each new filing: call
      `get_sec_filing(filing_id)` (no `section`) to get the table of
      contents, then `get_sec_filing(filing_id, section=<id>)` for the
      section(s) that look substantive (skip boilerplate cover pages);
      summarize in 1-3 sentences what it discloses. **8-K filings get
      priority attention** — that's the "material event" form type most
      relevant to a sudden price move (an 8-K explains *why*, after the
      fact, the way an earnings-date flag explains *when*, in advance).
      Call `record(symbol, "sec_filing", <summary>, form_type=form_type,
      filing_id=filing_id, filed_at=date_filed)`.

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
- Always check `entries_for_asset`/`entries_for_date` for an existing
  `article_id`/`filing_id` before calling `record()` for a news article
  or SEC filing — re-scanning the same recent window every day without
  this check would flood the log with duplicates.
- Crypto (`trading_agent.config.WATCHLIST`, the non-stock list) is out
  of scope — never call an equity-only tool (`get_equity_news`,
  `get_sec_filing_index`, `get_earnings_results`) with a crypto symbol.
