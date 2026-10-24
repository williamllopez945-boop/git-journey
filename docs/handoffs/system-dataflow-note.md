# Handoff: system-dataflow-note

Copy this file to `docs/handoffs/<unique-task-id>.md`.
One owner writes this task note; other tasks use other filenames.
Keep secrets, account details, raw live responses, and credentials out.

## Objective and scope

- Objective: add a referenceable architecture and data-flow note (plus a diagram-generation prompt) that future builds can use to structure new strategies and routines.
- Allowed files/subsystems: `docs/architecture/`, one pointer line in `trading_agent/STATUS.md`, this note.
- Out of scope: any code, `config.py`, runtime state, routine schedules/prompts, pushing, merging.
- Dependencies on other tasks / agreed interfaces: builds on the merged streamline audit (PR #8).

## Ownership and location

- Status: ready-for-review
- Assigned implementing agent: Claude Code
- Assigned reviewing agent: Codex (suggested)
- Current implementation owner: Claude Code
- Absolute workspace path: /home/user/git-journey-dataflow (separate worktree)
- Task branch: claude/system-dataflow-note
- Remote and default branch: origin (williamllopez945-boop/git-journey), default main
- Original base commit (full SHA): 397bcac94b951ea057afb277f87f302383ede853
- Latest implementation commit: resolve with `git log -1 --format=%H -- docs/architecture`
- Working tree at handoff: clean
- Other active workspaces: /home/user/git-journey is the live runner on claude/robinhood-trading-mcp-sdp3cp; do not edit it for this task.

## Completed changes

- `docs/architecture/system-dataflow.md`: layers, two Mermaid diagrams (system context, hourly cycle), component inventory, state ownership matrix, 11 design rules, new-strategy checklist, failure modes already seen.
- `docs/architecture/dataflow-visual-prompt.md`: prompt for an image/diagram assistant, same content as the one shared in chat on 2026-10-24.
- `trading_agent/STATUS.md`: pointer to both.
- Decisions: Mermaid blocks were written by hand and not rendered in this environment (no renderer); syntax should be checked in a renderer. The note describes structure, not live values, to avoid drift.

## Tests and results

- Environment: Linux, Python 3.11.17, pytest 9.1.1, local `.venv`.
- Command: `.venv/bin/python -m pytest trading_agent/tests/ research_agent/tests/ -q`
- Result: see the commit message / re-run at the reviewed head (docs-only change, expected 350 passed).
- Historical backtest evidence: not applicable, no behavior changed.

## Outstanding issues and risks

- Unfinished work: none for this task.
- Known limitations: Mermaid not rendered; schedules and routine names in the note can go stale (STATUS.md is the live table).
- Questions requiring an owner decision: push and open a pull request when ready.

## Next steps

1. Receiver: verify folder, branch, status, base and diff; render the Mermaid blocks; re-run the full suite.
2. Reviewer: report findings first; do not silently fix.
3. Owner: approve pushing and merging.

## Receiver acknowledgment

- Received by / date:
- Actual inspected implementation SHA:
- Aligned with handoff, or differences found:
- Independently verified checks:
- Findings/report location:
- Next implementation owner and agreed action:
