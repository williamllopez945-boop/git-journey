# Research cycle playbook

The runbook an agent session follows on each research cycle. Requires the
`robinhood-trading` MCP server (same connection the trading agent uses).
Run once per weekday, before market open (~8am ET) — news and SEC
filings don't change hour to hour the way price does, so this doesn't
need the trading agent's hourly cadence.

**Scope: stocks + VOLTRAP candidates, not crypto.**
`research_agent.config.WATCHLIST` is the union of
`trading_agent.config.STOCK_WATCHLIST` and `VOLTRAP_WATCHLIST` (added
2026-09-26 — every VOLTRAP candidate is a real stock/ETF underneath the
option, so the same equity tools apply). The crypto watchlist
(`trading_agent.config.WATCHLIST`) is still out of scope (see
README.md's "Coverage" section).

## Steps, per cycle

1. **Load config.** `WATCHLIST`, `LOOKBACK_DAYS`, `NEWS_LIMIT`,
   `NEWS_ALLOWED_DOMAINS`, `FORM_TYPES`, `EARNINGS_LOOKAHEAD_DAYS` from
   `research_agent/config.py`.

2. **For each symbol in `WATCHLIST`:**

   a. **News (source changed 2026-09-29 — see `config.py`'s "News source
      change" note: `get_equity_news` does not exist in this session's
      toolset; `WebSearch` is the replacement, owner-approved).** Call
      `WebSearch(query="<symbol> stock", allowed_domains=NEWS_ALLOWED_DOMAINS)`
      — one call per symbol; a bare ticker plus "stock" reliably surfaces
      that company rather than an unrelated word (e.g. a plain "AR" would
      not). Results are search-result blocks with a title, URL, and a
      short snippet, newest/most-relevant first per the tool's own
      ranking (no reliable `published_at` field the way `get_equity_news`
      had — don't fabricate one). Before logging anything, call
      `ResearchLogStore().entries_for_asset(symbol)` and collect every
      `urls` list already logged for this symbol under `source_type="news"`
      (news entries store a *list* of covered URLs, not a single one,
      same shape as the old `article_ids` field it replaces) — a fresh
      search returns whatever is currently prominent, not just new items
      since the last run, so without this check the same story gets
      re-logged every day it stays prominent. **Legacy entries logged
      before 2026-09-29 carry `article_ids` (RobinHood article UUIDs),
      not `urls` — never compare a WebSearch URL against an old
      `article_ids` list; only compare URLs against URLs.** Filter to
      results whose URL is NOT already covered. If none are new, log
      nothing for this symbol. If one or more are new, write **one
      consolidated entry**, not one entry per result — synthesize a
      single 2-3 sentence summary of what's new across those results (the
      real signal: price moves, analyst rating/target changes, earnings
      results, material announcements; skip pure filler like "$1000
      invested N years ago" pieces and results where the symbol is only
      tangentially mentioned, not the subject) and call `record(symbol,
      "news", <consolidated summary>, urls=[<URLs of every new result
      covered>], result_count=<count>,
      kind=<"baseline" if this symbol had no prior "news" entry, else
      "delta">)`. This keeps the log to one compact row per symbol per
      cycle instead of up to `NEWS_LIMIT` rows, which is what was
      driving excessive token use before this was changed (2026-09-24
      audit) - and the `kind` tag (also 2026-09-24) makes that
      baseline/delta split explicit and queryable rather than implicit
      in "was this the first entry."

   b. **SEC filings.** First check `entries_for_asset(symbol)` for any
      existing `source_type="sec_filing"` entries.
      - **Not yet populated for this symbol (bootstrap case, the first
        cycle that covers it):** call `get_sec_filing_index(symbol,
        form_type=FORM_TYPES)` with **no `since`** — fetch whatever's
        most recent regardless of age — and log **only the single most
        recent filing** (the first result; the tool returns
        most-recent-first) as a `kind="baseline"` entry (a short factual
        summary, e.g. "Most recent {form_type} on file at first coverage
        of this symbol" — no need to fetch/summarize its content), so
        the log has a known starting point without pulling the symbol's
        full filing history. An empty result here is expected and not an
        error for a foreign private issuer that files 20-F/6-K instead of
        10-Q/10-K/8-K (e.g. CHKP), or a symbol too newly public to have
        one yet (e.g. MAIR, IPO'd April 2026) — log nothing and move on.
      - **Already populated:** call `get_sec_filing_index(symbol,
        form_type=FORM_TYPES, since=<the latest already-logged
        filed_at>)` to fetch only filings newer than what's logged.
        Dedup by `filing_id` against existing entries as a safety net.
        Log each as a `kind="delta"` entry.
      For each new filing found this way: call `get_sec_filing(filing_id)`
      (no `section`) to get the table of contents, then
      `get_sec_filing(filing_id, section=<id>)` for the section(s) that
      look substantive (skip boilerplate cover pages); summarize in 1-3
      sentences what it discloses. **8-K filings get priority
      attention** — that's the "material event" form type most relevant
      to a sudden price move (an 8-K explains *why*, after the fact, the
      way an earnings-date flag explains *when*, in advance). If
      `get_sec_filing` 404s ("Filing content is not available") — seen in
      practice for routine 8-Ks filed the same day as a 10-Q, likely the
      accompanying Item 2.02 results filing — don't block on it: log the
      entry anyway from the filing index metadata alone (form_type +
      date_filed), with a summary noting content wasn't available, rather
      than skipping the filing entirely. Call `record(symbol, "sec_filing",
      <summary>, form_type=form_type, filing_id=filing_id,
      filed_at=date_filed, kind="delta")` — one entry per filing
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

4. **Local only — do not commit.** Owner request 2026-10-05: the daily
   digest is a local record, not a git-tracked one. Write the file and
   stop there; never `git add`/`git commit`/`git push` it.
   `research_agent/research_notes/*.md` is gitignored for exactly this
   reason — see the `.gitignore` comment. (Supersedes this step's
   earlier "commit and push" instruction; `research_log.json` remains
   the durable structured record either way, unaffected by this change.)

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
- Never modify `trading_agent/config.py`, `RISK_LIMITS`, `WATCHLIST`,
  `STOCK_WATCHLIST`, or `VOLTRAP_WATCHLIST` — this agent reads those
  watchlists, it doesn't own or change any of them.
- Always check `entries_for_asset`/`entries_for_date` for existing
  `urls`/`filing_id` values before calling `record()` for news or a SEC
  filing — re-scanning the same recent window every day without this
  check would flood the log with duplicates. Legacy news entries (before
  2026-09-29) carry `article_ids` instead of `urls` — never cross-compare
  the two; see step 2a.
- News is logged as one consolidated entry per symbol per cycle, not one
  entry per result — see step 2a. This keeps the log (and the tokens
  spent reading it back) proportional to the watchlist size, not to
  `NEWS_LIMIT`.
- Crypto (`trading_agent.config.WATCHLIST`, the non-stock list) is out
  of scope — never call an equity-only tool (`WebSearch` for news,
  `get_sec_filing_index`, `get_earnings_results`) with a crypto symbol.
