# Handoff: soxl-poc-plan

Copy this file to `docs/handoffs/<unique-task-id>.md`.
One owner writes this task note; other tasks use other filenames.
Keep secrets, account details, raw live responses, and credentials out.

## Objective and scope

- Objective: produce the architecture, data-source and validation plan requested in `#voltrap-agents-work` (2026-10-26) for a SOXL day-trade proof of concept, at one share at a time, before any code or paper loop.
- Allowed files/subsystems: `docs/design/soxl-daytrade-poc-plan.md`, this note.
- Out of scope: any code, `config.py`, routines, runtime state, paper loop, brokerage orders, pushing, merging.
- Dependencies on other tasks / agreed interfaces: follows the architecture note (`docs/architecture/system-dataflow.md`).

## Ownership and location

- Status: ready-for-review (plan awaiting owner approval)
- Assigned implementing agent: Claude Code
- Assigned reviewing agent: Codex (suggested)
- Current implementation owner: Claude Code
- Absolute workspace path: /home/user/git-journey-soxl (separate worktree)
- Task branch: claude/soxl-poc-plan
- Remote and default branch: origin (williamllopez945-boop/git-journey), default main
- Original base commit (full SHA): fb370f3e9060a44b8a0b30a7d5e7dfa4bc7c96b2
- Latest implementation commit: resolve with `git log -1 --format=%H -- docs/design/soxl-daytrade-poc-plan.md`
- Working tree at handoff: clean
- Other active workspaces: /home/user/git-journey is the live runner; do not edit it for this task.

## Completed changes

- The plan document, including data findings from read-only probes on 2026-10-26: daily bars real back to 2021-10-26; 5-minute bars real on 2026-04-28 and 2026-07-28 but interpolated (flat, zero volume) on 2026-01-28, and hourly/30-minute bars interpolated on 2025-10-28 and 2024-10-28.
- Decisions: scope fixed by the owner as one share at a time, long only, backtest and paper only; the existing repo RSI is a simple (non-Wilder) RSI, so the audit tests both conventions.

## Tests and results

- Docs only; no code. Full suite re-run at the committed head is recorded in the commit message and the final report.

## Outstanding issues and risks

- The intraday data window is short (about 6 to 9 months), limiting any day-trade conclusion. Day-trade/PDT rules for this account type are unverified.
- Questions requiring an owner decision: the four open questions in section 9 of the plan.

## Next steps

1. Receiver: verify the plan against the probes and the repo; report findings first.
2. Owner: approve scope, data window and validation plan (M0) before any code.

## Receiver acknowledgment

- Received by / date:
- Actual inspected implementation SHA:
- Aligned with handoff, or differences found:
- Independently verified checks:
- Findings/report location:
- Next implementation owner and agreed action:
