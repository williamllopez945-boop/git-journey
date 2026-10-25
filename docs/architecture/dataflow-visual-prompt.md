# Prompt: render the system data flow as diagrams

**How to use:** paste the block below into ChatGPT (or another assistant) to get the
system context diagram, the hourly stock cycle and a daily timeline, as Mermaid code
and images. The structured source of truth is `system-dataflow.md` in this folder:
if the system changes, update that note first, then refresh this prompt's component
and schedule lists. Written 2026-10-24. Contains no account numbers or credentials;
keep it that way.

```text
You are a technical diagrammer. Create a clear, accurate DATA-FLOW visual of an autonomous trading system described below. Do not invent components, services or arrows that are not listed. If something is ambiguous, say so in a short "assumptions" list instead of guessing.

## Deliverables
1. A SYSTEM CONTEXT DIAGRAM (one page): all components, external services and the data that moves between them.
2. A HOURLY STOCK CYCLE DIAGRAM (sequence/flow): what happens in one run, step by step, including where orders can and cannot be placed.
3. A DAILY TIMELINE (a horizontal 24-hour strip, weekdays): when each scheduled job fires. Use UTC as the authoritative axis and label the equivalent US Eastern times for BOTH daylight time (EDT, until 2026-10-31) and standard time (EST, from 2026-11-01). See the schedule rules below: some jobs are fixed in UTC and shift an hour in Eastern at the clock change; others are fixed in Eastern.
Give me each as (a) Mermaid code I can paste into a renderer, and (b) if you can, a rendered image. Use a consistent style across all three. Keep text legible: short labels on arrows, details in the legend, not in the boxes.

## System summary
A small real-money brokerage account (about $1,000) is traded by an AI agent (Claude) that wakes on a schedule, reads a runbook in a Git repository, calls brokerage tools, runs Python helper scripts, and reports to the owner. Three independent strategies share one account's cash. An advisory research agent and a reporting/dashboard layer sit around them. The owner is the only person who can change risk limits or watchlists.

### Actors and control
- OWNER: approves any change to risk limits, watchlists, auto-execute switches, routine schedules. Receives push notifications and Slack posts. Reviews pull requests.
- SCHEDULER: persistent "routines" (cron triggers) that each fire a stored prompt into one persistent agent session.
- AGENT SESSION (Claude): reads the stored prompt, then the runbook (PLAYBOOK.md), then executes. Subject to a permission/safety check on tool and script calls; if a call is denied, the agent reports and stops (it does not work around the denial).
- REVIEWER: Codex (ChatGPT), connected to Slack and GitHub, reviews pull requests. It does not trade.

### Repository (code and docs, committed to Git)
- config.py: watchlists, risk limits, switches (DRY_RUN=False, auto-execute flags). PROTECTED: changed only with explicit owner approval, never by routines.
- Signal modules: equity_signals.py (SMA10/SMA30, relative volume, % change from quotes/historicals), scanner_signals.py (classifies: fresh_buy_cross, fresh_sell_cross, excellent_watch, hold), income_signals.py (dip percentile + support-zone entry).
- Risk and exits: risk_manager.py (position sizing, concurrent and aggregate caps, daily trade cap, 3% daily-loss circuit breaker), exit_criteria.py (stop-loss 4%, take-profit 8% selling 70%), profit_gate.py (holds a sell-cross exit while below breakeven), income_exit.py (stop-loss 15%, trim +10% selling 50%).
- Scripts: run_cycle.py (main bot analysis and fill recording), income_cycle.py (income sleeve analysis and fill recording), daily_review.py, voltrap_state.py / voltrap_candidates.py, watchlist_review.py, reconcile_ledger.py.
- Docs: PLAYBOOK.md (the runbook), STATUS.md, CHANGELOG.md, README.md, dated backtest/evidence files, daily_logs/*.md (committed daily reports).
- legacy/: disabled modules (not in any live flow; show greyed out or omit).

### Local runtime state (gitignored, NEVER committed or edited by hand)
state.json (risk state + trade log), scanner_state.json, position_state.json, cycle_log.json (decision log), income_risk_state.json / income_position_state.json / income_cycle_log.json (income sleeve, isolated from the main bot), voltrap_state.json, research_agent/research_log.json.

### External services
- Brokerage (Robinhood via MCP tools): READ = portfolio, positions, quotes, historicals, orders, realized P/L, option chains/quotes. WRITE = place/cancel equity and option orders (marketable LIMIT orders only, never market orders).
- Slack channel #voltrap-agents-work (notable events + daily report; Codex also reads it).
- Push notifications to the owner.
- GitHub (commits of daily logs and docs, pull requests, Codex review).
- Claude Artifact "Ledger" dashboard (a published web page, read-only view of account state).
- Web search (news only) used by the research agent.
- SEC filing and earnings-date tools (via the brokerage MCP) used by the research agent.

### Schedule rules (read before drawing the timeline)
- Jobs marked [ET] are scheduled in US Eastern time and stay at the same Eastern clock time all year.
- Jobs marked [UTC] are scheduled in UTC. Their Eastern time shifts by one hour at the clock change on 2026-11-01 (EDT = UTC-4 until then, EST = UTC-5 after). Show both.
- Weekdays unless stated.

### Strategies and routines
1. MAIN BOT, STOCKS ONLY (crypto trading is fully cut): hourly routine [ET] 10:08, 11:08, 12:08, 13:08, 14:08, 15:08. Flow: arm daily circuit breaker from portfolio equity -> fetch positions + hourly historicals + quotes for 5 stocks -> run_cycle.py computes SMA/relative volume and classifies -> protective exit checks on any held stock (always run, even if the breaker is tripped) -> for fresh crosses: risk gates (cooldown, caps, profit gate, sizing) -> if auto-execute allowed, preview then place a marketable limit order -> record the real fill in a SEPARATE run_cycle.py --record-only call -> append to cycle_log/state -> notify only if something notable (trade, protective exit, recommendation, blocked signal). excellent_watch is alert-only and never auto-executes.
2. INCOME SLEEVE (15 weekly-distribution ETFs): daily routine [UTC] 15:00 (= 11:00 EDT / 10:00 EST). Flow: portfolio + quotes + daily historicals + positions -> income_cycle.py (own circuit breaker check, entry signal, own exits) -> exits always execute; entries execute as whole-share marketable limit orders, otherwise reported as "could not execute" (no market-order fallback) -> separate --record-only fill recording -> income_* state files -> notify only if notable.
3. VOLTRAP (options wheel: cash-secured puts then covered calls): weekly entry [ET] Monday 09:45 (screen candidates, pick strike by delta, size within budget that reserves cash for the income sleeve, place option order, record in voltrap_state.json) and a daily monitor [ET] 15:45 (read-only: exits immediately if nothing is open; otherwise checks deep-ITM/early-assignment risk and resolves expirations in the state file). A paper dry-run version exists but is paused (show greyed).
4. RESEARCH AGENT (advisory only, never trades or gates a trade): weekday [UTC] 12:00 (= 08:00 EDT / 07:00 EST) scan -> web news + SEC filings + upcoming earnings for the stock and VOLTRAP watchlists -> research_log.json -> daily digest note; the trading agent may read it as context.
5. DAILY AFTER-ACTION REVIEW: [UTC] 20:05 (= 16:05 EDT / 15:05 EST), every day including weekends. Reads cycle_log + trade log + brokerage orders/realized P/L -> writes daily_logs/DATE.md -> commits and pushes to GitHub -> push notification + Slack post.
6. LEDGER DASHBOARD REFRESH: [ET] 10:28, 12:28, 14:28, 16:28 weekdays. Read-only: reads brokerage state + local logs + daily logs -> republishes the Ledger artifact. Never places orders.
7. MONTHLY WATCHLIST REVIEW: [UTC] 1st of the month, 15:00 (= 11:00 EDT / 10:00 EST): recommendation only; backtests candidates; writes a dated review file; never edits config.

### Safety boundaries to make visible in the diagrams
- Only three places can place orders: the main-bot hourly routine, the income-sleeve routine, and the VOLTRAP weekly entry. Everything else is read-only. Mark these three "can place orders" in one color and all read-only flows in another.
- Orders are marketable LIMIT orders only.
- Config (limits, watchlists, switches) flows ONE WAY: owner -> config.py -> everything else. Routines never write to it.
- The income sleeve has its own limits and state files and never writes the main bot's state files.
- A permission check sits between the agent and every tool/script call.

## Visual style
- Left-to-right layout in swimlanes: Owner | Scheduler | Agent session | Repo code | Local state | External services | Outputs (notifications, Slack, GitHub, dashboard).
- Colors: order-capable flows = red/orange; read-only flows = blue; advisory flows = green; owner-controlled config = purple; disabled/legacy/paused = grey and dashed.
- Label every arrow with the data (for example "quotes", "positions", "fill price", "classification", "daily report"). Number the steps on the hourly cycle diagram.
- Include a legend, a title, and a one-line caption per diagram.
- Do NOT include account numbers, API keys, personal names or email addresses anywhere.

## Output order
First list your assumptions (max 5 bullets), then the three diagrams with Mermaid code blocks and images, then a 5-line "how to read this" note.
```
