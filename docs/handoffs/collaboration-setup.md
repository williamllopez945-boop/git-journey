# Handoff: collaboration-setup

## Objective and scope

Set up Codex/Claude collaboration, independent workspaces, review ownership,
and reproducible local verification without changing application features.
The task was requested by the owner on 2026-09-26.

Allowed scope: shared instructions, handoff documents, development dependency
setup and ignore rules, and test-only portability/isolation fixes necessary
for the local Windows verification workflow. No production source, strategy,
live configuration, old runbooks, or recorded research/backtests changed.

## Ownership and location

- Status: ready-for-review.
- Assigned implementing agent / current implementation owner: Codex (paused
  after completing setup).
- Assigned reviewing agent / next agent: Claude Code, review only.
- No transfer of implementation ownership has occurred.
- Codex workspace:
  `C:/Users/willi/Documents/Codex/2026-09-26/files-pasted-by-the-user-project/outputs/git-journey-codex`
- Task branch: `codex/collaboration-setup`.
- Claude review workspace:
  `C:/Users/willi/Documents/Codex/2026-09-26/files-pasted-by-the-user-project/outputs/git-journey-claude`
- Review branch: `claude/collaboration-review`, prepared from the commit
  that saves this note. Do not merge it back merely for having the same base.
- Control clone: sibling `git-journey` folder, left on `main`.
- Remote: `https://github.com/williamllopez945-boop/git-journey.git`.
- Default branch: `main`.
- Original base: `e84105f34e8972b4ab6aab9824cec53933beaed8`.
- Current review base (latest fetched GitHub main):
  `2bcdac37be476279aeceb917d73e1d9b7132257c`.
- Latest implementation commit:
  `47b73fb795c133daccf2947099e1cf8bc6dfbfc0`.
- Test/environment commit:
  `3f375c1982610bec5ef602e3c46e8661200bbd34`.
- Latest handoff commit: run
  `git log -1 --format=%H -- docs/handoffs/collaboration-setup.md`.
- Working tree: this note is the final checkpoint; verify it is committed
  and both task worktrees are clean before beginning review.
- No other implementation task was assigned. Do not edit the original
  remote Claude branches or the earlier read-only snapshot under `work/`.

## Completed changes

- Added `COLLABORATION.md` as the common workflow and project-boundary guide.
- Added small `AGENTS.md` and `CLAUDE.md` entry points that both require it.
  None of these files existed at the base revision.
- Added `docs/handoffs/TEMPLATE.md`: one note per task, immutable implementation
  SHA and base, verification evidence, explicit next role, and ownership transfer.
- Added `requirements-dev.txt` (pytest 9.1.1) and ignored per-workspace
  `.venv/` plus VOLTRAP runtime state, retaining all earlier ignore rules.
- Closed discarded `mkstemp` file descriptors before fixture files are
  unlinked, in six existing test modules. Windows had rejected deleting
  these open files; no assertions or production logic were changed.
- Gave the missing-stock-arguments CLI test all four temporary state-path
  overrides; it previously wrote default risk state before argument validation.
- Created local task commits only. No push, default-branch merge, deployment,
  trading, brokerage connection, or credential copying was performed.
- After the owner's update, fetched five newer main commits and merged them
  into this task branch at `47b73fb` without conflicts. Preserved the updated
  cycle log and backtest documents exactly. Local main itself was not advanced.

## Tests and results

Environment: native Windows, Python 3.12.14, pytest 9.1.1.
Each agent workspace has its own ignored `.venv`. It was created with the
Codex bundled Python runtime; ordinary Python 3.12 plus the pinned dev
requirements is sufficient on another machine. Recreate environments if moved.

Baseline (untouched base, disposable archive under `work/baseline-tests`):
**160 passed, 55 failed**, all failures were Windows open-file deletion errors
(`PermissionError: [WinError 32]`). This was tested before the fixture changes.

Updated source (the exact test/application contents saved in `3f375c1`,
unchanged by the documentation commit `a1fc0de`):

```powershell
.\.venv\Scripts\python.exe -m pytest trading_agent/tests/ research_agent/tests/
```

**Passed: 215 tests, 3.82 seconds.** Checked before and after: none of the
seven production-default runtime JSON files existed in the Codex worktree.
No live state was used as a fixture.

After combining the latest GitHub main with setup, re-ran the same full command
at `47b73fb795c133daccf2947099e1cf8bc6dfbfc0`: **215 passed in 2.53 seconds**.
Verified no runtime state was created and production source/application docs
match the current review base (`2bcdac3`) exactly.

Other verification:
- `git diff --check` and staged whitespace checks passed.
- Both instruction entry points resolve to the same shared guidance.
- Relative Markdown links and fenced code blocks in the new guidance checked.
- Test/install commands match the actual repository layout and installed venv.
- Ignore rules checked for `.env`, `.env.local`, `.venv`, and every named
  runtime state path. None are tracked.
- Production Python source and existing application documentation are unchanged
  from current GitHub main; only the named test files under the two agents changed.
- Real historical backtests: not run; no strategy or application behavior changed.

## Outstanding issues and next steps

- Independent Claude review has not happened. Do not describe this setup as
  approved merely because local tests pass.
- Confirm both worktrees and their environments using the local START-HERE
  guide delivered alongside the control clone. The Claude checkout should
  include this note; stop if its actual commit differs unexpectedly.
- Receiving reviewer: inspect `git status`, branch, actual
  `git diff 2bcdac3..47b73fb`, changed tests, and shared guidance. Read this
  note's saving commit too. Verify evidence and run the full suite yourself.
- Report findings first. If saving a report, use
  `docs/handoffs/collaboration-setup.review-claude.md` on the review branch;
  do not rewrite this implementation note while Codex owns it.
- Corrective edits need an explicit transfer or separately assigned fix
  workspace. To return work, stop Claude and give Codex the findings and
  reviewed SHA; Codex remains the implementation owner.
- Publishing/merging into GitHub `main` remains an owner-authorized later step.
  All setup commits are currently local. Start future tasks from this setup
  branch's committed revision until the guidance is merged into `main`.
- A normal Windows shell may not have Python on PATH. The prepared workspace
  environments work without activation; use the executable commands above.
- Prior application docs contain historical descriptions that may differ from
  current settings. This task preserved them rather than changing trading
  policy as part of collaboration setup.

## Receiver acknowledgment

Pending independent review. Put review findings in the reviewer-specific file,
then request any needed transfer before making corrective edits.
