# Current operating status

**Single page: what is live today.** This summarizes the state of the code
and routines as of 2026-10-24. It is a pointer, not a source of truth:
`config.py` holds the live values, `PLAYBOOK.md` the procedures and
`CHANGELOG.md` the history. If this page and those disagree, they win; fix
this page. Keep it to one screen and update it whenever a strategy or routine
is turned on, off or re-scoped.

## Strategies

| Strategy | State | Notes |
|---|---|---|
| Main bot, crypto (`WATCHLIST`) | **Cut** (owner, 2026-10-08) | Only a protective-exit check for an open AERO position, if one exists. No crypto position is open today. |
| Main bot, stocks (`STOCK_WATCHLIST`: TWLO, ILMN, PTC, CRWD, PANW) | Live, auto-execute | SMA(10,30) hourly cross, stop-loss 4%, take-profit 8% (sells 70%). No live stock trade yet; CRWD/PANW sit on `excellent_watch`, which is alert-only. |
| Income sleeve (`INCOME_WATCHLIST`, 15 ETFs) | Live, `INCOME_AUTO_EXECUTE = True` | Dip percentile + support zone entry, stop-loss 15%, trim +10% (sells 50%). Own limits and state files. Entries need whole shares; the 25% aggregate cap currently leaves less than one share of room. |
| VOLTRAP (options wheel) | Live, `VOLTRAP_AUTO_EXECUTE = True` | No option positions or orders since go-live (2026-10-09). |
| VOLTRAP dry-run (paper) | Running, hypothetical $5,000 | Paper only; places no orders. |
| Research agent | Running, advisory only | Stocks + VOLTRAP watchlists. Never trades or gates a trade. |

`DRY_RUN = False`. The three strategies share one real account and its cash.

## Routines (persistent, UTC unless noted)

| Routine | Schedule | Role |
|---|---|---|
| Hourly trading cycle | hourly, around :08 | Stock steps only 13:30-20:00 UTC on weekdays; otherwise a no-op. |
| Ledger dashboard refresh | :28, 10-16 ET weekdays | Read-only dashboard republish. |
| Income sleeve cycle | 15:00 weekdays | Runs `income_cycle.py`. |
| VOLTRAP daily monitor | 15:45 ET weekdays | Read-only; reconciles expirations. |
| VOLTRAP weekly entry | Mon 09:45 ET | Places contracts within budget. |
| VOLTRAP dry-run (paper) | Mon 09:37 ET | Paper candidate walkthrough. |
| Daily after-action review | 20:05 daily | Writes `daily_logs/DATE.md`, commits and pushes. |
| Research daily scan | 12:00 weekdays | Writes the research log. |
| Weekly watchlist review | Sun 15:00 | Recommendation only; never edits config. |

Routine prompts are stored on the server, not in this repo. They are copies
that drift (the income prompt once passed a removed flag; the VOLTRAP monitor
still says "recommend-only" while `config.py` says auto-execute). Prefer
prompts that point at a PLAYBOOK section over prompts that restate it. See
`docs/proposed-routine-prompts.md`.

## Hard boundaries

- Never change `RISK_LIMITS`, `DRY_RUN`, `WATCHLIST`, `STOCK_WATCHLIST`,
  `VOLTRAP_*` or the `INCOME_*` limits incidentally; each needs explicit owner
  approval.
- Marketable limit orders only, never market orders.
- Parameter changes need real historical backtests (multiple windows,
  worst case first). Rejected ideas (trailing stop, profit lock, RSI,
  liquidity displacement, sustained `excellent_watch` entry, shorter stock
  SMA windows) are indexed in `EVIDENCE_INDEX.md`.
- Runtime state files (`state.json`, `scanner_state.json`, and the other
  runtime JSON files listed in `COLLABORATION.md`) are never edited or
  committed.

## Known stale prose

- `README.md`'s income-sleeve paragraph previously said 8 names (corrected to 15; some adjacent prose still describes the early 8-name state).
- The VOLTRAP daily monitor routine prompt says "recommend-only"; config says
  auto-execute.
- `PLAYBOOK.md` steps 1-6 apply to zero assets and are kept as infrastructure.
