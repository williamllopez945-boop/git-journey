# Handoff: orb-alpaca-data

## Objective and scope

- Objective: retrieve genuine vendor-supplied historical five-minute SIP equity bars for the current VOLTRAP watchlist, retaining available regular-session history for Claude Code's ORB evaluation.
- Allowed files/subsystems: `research_agent/data/orb_5min/<SYMBOL>.csv`, its `README.md`, and this task note.
- Out of scope: strategy logic, configuration/risk/watchlist changes, ORB backtesting, live trading, orders, production runtime state, main/protected-branch writes.
- Dependencies/interfaces: six-column CSV `timestamp,open,high,low,close,volume`; UTC bar-start timestamps. Dataset README describes session filtering and source limitations.

## Ownership and location

- Status: ready-for-review
- Assigned implementing agent: Codex
- Assigned reviewing agent: Claude Code
- Current implementation owner: Codex (paused at handoff)
- Next agent and role: Claude Code, reviewer; review does not transfer implementation ownership.
- Ownership transfer: none. William authorized execution of Claude's Slack data handoff on 2026-09-27, including publication to the named task branch.
- Absolute workspace path: `/workspace/scratch/1134d0bce130/orb-alpaca-data`
- Task branch: `codex/orb-alpaca-data`
- Remote: `https://github.com/williamllopez945-boop/git-journey.git`; default branch verified as `main`.
- Original base commit: `9b661576030655c57c9b5ef78ec6b3a0cbdbbd56`
- Latest implementation commit: `435516e1bb08380ab18bca4a0db77f5104598ec9`
- Latest handoff commit: resolve with `git log -1 --format=%H -- docs/handoffs/orb-alpaca-data.md`.
- Working tree at handoff: clean after committing this note; `.venv` is ignored and local.
- Other workspaces: Claude's standing `claude/robinhood-trading-mcp-sdp3cp` branch is reserved to Claude and was not checked out, used as a base, or pushed. This is a fresh isolated clone.

## Completed changes

- Done: verified AGENTS.md/COLLABORATION.md, research runbooks, current watchlist, and exact approved base; fetched eight symbols through the last completed regular session (2026-09-25); filtered using Alpaca's exchange calendar; validated data; documented coverage, gaps, hashes, and source caveats.
- Done: produced 956,660 regular-session rows from 1,622,231 source rows. Successful terminal empty queries confirm pagination exhaustion for every requested symbol/window.
- Done: full repository tests and diff checks. No application source file changed.
- Deviations: temporary connector internal errors required resumable retries; page limits were 5,000 and later 10,000. Cursors advanced only after a successful response was saved. No failed response, capability probe, padding, or synthetic replacement entered the deliverable.
- The market-data connector does not expose interpolation flags or adjustment selection. Preserve vendor bars and describe the limits rather than claiming independent exchange-print verification.
- Final export validation initially detected a truncated SEDG working CSV (197,651 rows versus 209,256 source-validated rows). Regenerated it from the saved source pages using an atomic file replacement. The independent validator then passed all 956,660 rows, and all eight staged Git blobs matched the documented SHA-256 hashes before the implementation commit. Root cause of the initial truncation was not established; no source prices were altered to resolve it.

### Exact delivered coverage

| Symbol | First UTC timestamp | Last UTC timestamp | Rows | Missing opening ranges |
|---|---|---|---:|---:|
| SMCI | 2016-01-04T14:30:00Z | 2026-09-25T19:55:00Z | 178,029 | 524 |
| MARA | 2017-10-30T13:30:00Z | 2026-09-25T19:55:00Z | 162,240 | 124 |
| OKLO | 2021-07-08T14:10:00Z | 2026-09-25T19:55:00Z | 61,372 | 598 |
| CLSK | 2020-01-24T14:30:00Z | 2026-09-25T19:55:00Z | 127,551 | 36 |
| RGTI | 2021-04-22T14:45:00Z | 2026-09-25T19:55:00Z | 96,363 | 128 |
| ASST | 2023-02-03T15:45:00Z | 2026-09-25T19:55:00Z | 53,000 | 231 |
| NVDL | 2022-12-13T15:45:00Z | 2026-09-25T19:55:00Z | 68,849 | 47 |
| SEDG | 2016-01-04T14:30:00Z | 2026-09-25T19:55:00Z | 209,256 | 8 |

## Tests and results

- Tested implementation revision: the implementation SHA above. Checks also passed on the original base before the data files were produced.
- Environment: Linux, Python 3.12.14, isolated `.venv`, pytest 9.1.1 from `requirements-dev.txt`; no credentials copied and no live runtime state used.
- Full-suite command: `.venv/bin/python -m pytest trading_agent/tests/ research_agent/tests/` — **215 passed**. These are existing unit tests, not a historical ORB backtest.
- Data audit command: `python3 /workspace/scratch/1134d0bce130/orb-fetch/audit_data.py` — passed all eight symbols; validated original pagination ordering, unique timestamps, bar alignment, OHLCV bounds, regular-session inclusion, activity counts, and missing-calendar slots. Temporary scratch audit utilities and raw retrieval pages are outside the task diff.
- Independent delivered-file check: `python3 /workspace/scratch/1134d0bce130/orb-fetch/verify_csv.py` — passed all delivered rows, matching source-audit counts and SHA-256 hashes.
- Diff checks: `git diff --check` and `git diff --cached --check` — passed; staged paths were explicitly limited to the requested data/README and this note.
- No baseline failures. No backtest, strategy performance claim, build, deployment, live cycle, account-state access, or order operation performed.

## Outstanding issues and risks

- Data gathering is complete for the successful provider query window; no implementation work remains for this task.
- Publication is blocked: terminal `git push -u origin codex/orb-alpaca-data` failed because no GitHub credentials are available, and the connected GitHub app's create-blob request returned HTTP 403 `Resource not accessible by integration`. No remote branch was created or updated. Local commits are ready for review; an incremental Git bundle preserves them for transfer to a repository containing the original base commit. Publishing the requested branch still requires an authorized GitHub write connection or an authenticated local environment.
- Missing opening bars and entirely missing sessions are documented per symbol. Do not silently fill them or treat incomplete opening ranges as valid ORB setups.
- Alpaca's documented default is unadjusted bars; the connector does not expose adjustment control. Corporate actions require separate reconciliation for cross-date returns.
- Default symbol mapping includes predecessor histories: OKLO before 2024-05-10 and RGTI before 2022-03-02 must be separated from the current operating businesses. NVDL has a leverage-objective change and splits. See README's primary-source links.
- Source availability is not an IPO date or a guarantee of full lifetime history. No full corporate-action audit or cross-vendor validation was performed.
- Current-watchlist selection has survivorship/selection bias. OHLCV alone cannot establish bid/ask execution, intrabar stop/target order, short availability, or options profitability.
- Descriptive quarterly intraday-range statistics document differing volatility conditions only; they are not strategy/backtest results or recommended test-window selection.
- Environment prerequisites: Python and the pinned pytest dependency for repository checks; authorized Alpaca connector access only if the reviewer chooses to reproduce source retrieval. No secret values belong in the handoff.

## Next steps

1. Claude: fetch only the task branch into your own clean review workspace; inspect the base, implementation SHA, handoff commit, status, and actual diff.
2. Verify CSV hashes against README, recheck source/session coverage and corporate-action boundaries, and rerun relevant checks plus the full repository suite.
3. Report findings first and record any drift. Do not silently fix this task's files or take implementation ownership merely by reviewing.
4. Continue ORB evaluation only under the separately assigned evaluation scope; this handoff does not authorize parameter changes or live activation.
5. No main merge, production-branch push, deployment, or live operation is part of this task. Codex stops at ready-for-review.

## Receiver acknowledgment

Write only after a clear ownership transfer permits editing this note. Otherwise put findings in `docs/handoffs/orb-alpaca-data.review-claude.md` on the review branch.

- Received by/date: pending reviewer.
- Actual inspected implementation SHA: pending reviewer.
- Alignment, independently verified checks, and findings location: pending reviewer.
- Next implementation owner/action: Codex retains implementation ownership until explicitly reassigned.
