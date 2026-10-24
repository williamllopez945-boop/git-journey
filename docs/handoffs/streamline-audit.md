# Handoff: streamline-audit

Copy this file to `docs/handoffs/<unique-task-id>.md`.
One owner writes this task note; other tasks use other filenames.
Keep secrets, account details, raw live responses, and credentials out.

## Objective and scope

- Objective: implement Phases 0-2 of the streamlining plan from the trading strategy audit (docs/prompt single source of truth, code hygiene). Phase 3 (routine changes) and Phase 4 (behavior changes) are NOT started and need explicit owner approval.
- Allowed files/subsystems: `trading_agent/*.md` docs, `docs/`, no strategy or config code.
- Out of scope: `config.py`, runtime state files, routine schedules/prompts (drafts only), any parameter or limit change, any pushes or merges.
- Dependencies on other tasks / agreed interfaces: none.

## Ownership and location

- Status: ready-for-review (Phases 0-2 complete; further phases await owner approval)
- Assigned implementing agent: Claude Code
- Assigned reviewing agent: Codex (suggested)
- Current implementation owner: Claude Code
- Next agent and role (review does not transfer implementation ownership): reviewer
- Ownership transfer, if any: none
- Absolute workspace path: /home/user/git-journey-streamline (separate worktree; the live runner checkout /home/user/git-journey was left untouched)
- Task branch: claude/streamline-audit
- Remote and default branch: origin (williamllopez945-boop/git-journey), default main
- Original base commit (full SHA): 8ac973f (Daily review 2026-10-23), on claude/robinhood-trading-mcp-sdp3cp
- Latest implementation commit (full SHA; excludes this note's later commit): resolve with `git log -1 --format=%H -- trading_agent/STATUS.md`
- Latest handoff commit: resolve with `git log -1 --format=%H -- docs/handoffs/streamline-audit.md`
- Working tree at handoff: clean
- Other active workspaces / files reserved to other tasks: /home/user/git-journey is the live runner on claude/robinhood-trading-mcp-sdp3cp (daily-review commits land there); do not edit it for this task.

## Completed changes

- Phase 0: baseline in a separate worktree with no runtime state files. 350 tests passed before changes.
- Phase 1 (commit message "Phase 1: add STATUS and evidence index..."): added `trading_agent/STATUS.md`, `trading_agent/EVIDENCE_INDEX.md`, `docs/proposed-routine-prompts.md` (drafts, not applied); collapsed PLAYBOOK's two superseded top-of-file notes into a short pointer (history stays in CHANGELOG 2026-09-24 and 2026-10-08); corrected README's stale 8-name income watchlist statement.
- Phase 2: no code change made. See deviations.
- Decisions or deviations from the original plan:
  1. Evidence files were NOT moved into `evidence/`. `config.py` (protected) and hundreds of references in CHANGELOG/PLAYBOOK/README use bare filenames, so a move would force incidental edits to protected config and a large link rewrite. An index was added instead.
  2. Audit claim corrected: `income_cycle.py` does not import `income_ex_dividend` or `income_candidates`; only its docstring mentions them. There are no dead imports to remove.
  3. Modules with no in-repo importer (`volatility_sizing`, `price_history`, `cost_basis_fallback`, `watchlist_review`, `order_pricing`, `reconcile_ledger`, `income_ex_dividend`, `income_candidates`) are not safe to call dead: the routines import several of them ad hoc by name (for example cost_basis_fallback, order_pricing, watchlist_review). The only modules tied to disabled paths are `income_ex_dividend` and `income_candidates.filter_by_liquidity`. No `legacy/` move was made; this needs an owner decision.
  4. No `active_watchlist` helper or scanner-state pruning was added. There is no code-level "crypto cut" flag (adding one would mean a new config key), the fix is passing `STOCK_WATCHLIST` in the daily review prompt (already in the drafts), and stale scanner rows are harmless while pruning could drop crypto state that matters if crypto is re-enabled.

## Tests and results

- Tested implementation revision: HEAD of claude/streamline-audit
- Environment: Linux, Python 3.11.17 (setup verified 3.12), pytest 9.1.1, local `.venv`
- Exact commands: `.venv/bin/python -m pytest trading_agent/tests/ research_agent/tests/ -q`; `git diff --check`
- Results and counts: 350 passed before and after (docs-only changes)
- Any baseline failure: none
- Historical backtest evidence, if strategy behavior changed: not applicable, no behavior changed

## Outstanding issues and risks

- Unfinished work: Phase 3 (routine changes) and Phase 4 (behavior decisions); the optional `legacy/` move.
- Known limitations: routine prompts live on the server, so the drafts are unapplied; the STATUS.md routine table was written from the stored crons on 2026-10-24 and can go stale.
- Questions requiring an owner decision: approve Phase 3 changes one routine at a time; whether to move the two disabled income modules to `legacy/`; Phase 4 items from the audit.
- Missing environment prerequisites: none.

## Next steps

1. Receiver: verify folder, branch, Git status, base, latest commit and actual diff.
2. Inspect changed docs, re-run the full suite.
3. Report any drift between this note and the repository before continuing.
4. Reviewer: report findings first; do not silently fix them.
5. Owner: decide on Phase 3 and publication. Nothing has been pushed or merged.

## Receiver acknowledgment

- Received by / date:
- Actual inspected implementation SHA:
- Aligned with handoff, or differences found:
- Independently verified checks:
- Findings/report location:
- Next implementation owner and agreed action:
