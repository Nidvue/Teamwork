# Engineering policy

Reference for the /teamwork skill. Loaded on demand; `SKILL.md` keeps the
operating procedure.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md)


## Commit identity - role mailbox, never instance numbered

Every team commit is authored **and** committed by the role:

```text
Developer <developer@agents.nidvue.com>
Tester <tester@agents.nidvue.com>
Architect <architect@agents.nidvue.com>
Product Manager <productmanager@agents.nidvue.com>
Project Manager <projectmanager@agents.nidvue.com>
Security Auditor <securityauditor@agents.nidvue.com>
Designer <designer@agents.nidvue.com>
Reviewer <reviewer@agents.nidvue.com>
CEO <ceo@agents.nidvue.com>   CTO <cto@agents.nidvue.com>   COO <coo@agents.nidvue.com>   CFO <cfo@agents.nidvue.com>
```

Rules:

- Display name is the role; email is the lowercase role id at `agents.nidvue.com`.
- **Never** use an instance-numbered identity: no `Developer-1`, no
  `developer-1@agents.nidvue.com`.
- Never use the operator's personal git identity for team work.
- Apply it per commit, without changing the repository config:

```sh
git -c user.name="Developer" -c user.email="developer@agents.nidvue.com" commit ...
```

`teamwork.py commit --role <role> ...` does this for you, and
`teamwork.py identity [--role X]` prints the exact identity.
`TEAMWORK_IDENTITY_DOMAIN` overrides the email domain.

## Commit batching

Accumulate a coherent, locally green change-set and commit once. No per-file,
per-test-run or per-finding micro-commits, no `WIP` churn. Never bundle unrelated
issues, mixed owners, or changes with independent rollback risk. Review the staged
diff, confirm no secrets, and reference the task id.

Commit at **staged milestones** - a finished milestone, a reviewed deliverable, a
closed gate - not on every keystroke.

## Commit message style (fixed)

Use this shape, in this field order, with these field names:

```text
<type>(<area>): <deliverable summary, <=72 chars>

Task: T-0007
Role: Developer
Producers: Developer-1, Developer-2
Goal: <what the task/milestone asked for>
Deliverable: <what was produced: files, docs, tests>
Why: <why this change, what evidence drove it>
Status: <actual state: implemented / reviewed / tested / blocked>
Result: <observed outcome: command @rev -> result>
Docs: <related documents>
Refs: <issues, PRs, disputes>

Acting role: Developer
```

- `type` is one of `feat fix test docs design research refactor perf build ci chore revert`.
- `Producers` = the instances that produced it (never invent one).
- `Goal`, `Deliverable`, `Why`, `Status`, `Result` are mandatory: they answer who,
  what, why, where it stands and what actually happened.
- `Status` states the truth, including "blocked on X" or "awaiting review" - never
  a hopeful claim.
- `Result` carries the evidence pointer (command + revision + observed result).

`teamwork.py commit` builds this message and refuses to commit when `--goal`,
`--deliverable`, `--why`, `--status` or `--result` is missing.

## Git LFS archival

Large and binary content is stored through Git LFS, not the object store.

- `teamwork.py repo` (and `init`) runs `git lfs install --local` and writes
  `.gitattributes` with the LFS patterns: images, audio/video, archives, model
  weights, datasets, fonts, native libraries, 3D assets.
- `.gitattributes` is committed; it is part of the project output.
- `teamwork.py commit` refuses to commit a file above `--lfs-threshold`
  (default 1 MB) that no LFS pattern covers.
- `teamwork.py audit` reports LFS readiness and any untracked large file.

## Branch, PR and merge flow

`main` only ever receives merges performed by the **Reviewer**. No agent commits
to `main`, and no agent merges its own work.

```text
branch start  ->  work + commit  ->  SelfCheck  ->  pr open  ->  review pass/fail
                                                                     |
                                          (pass)  pr merge --by reviewer
                                                                     v
                                                                    main
```

```sh
# 1. every instance works on its own branch
teamwork.py branch start --agent developer-1 --task T-0007          # [--worktree]
#    branch name: developer-1/t-0007-<slug>
# 2. commit staged milestones on that branch (commit refuses on main)
teamwork.py commit --role developer --type feat --task T-0007 ... --all
# 3. your own review + test, then hand a PR to the Reviewer
teamwork.py task set developer T-0007 --status selfcheck
teamwork.py selfcheck developer T-0007 --by Developer-1 --note "..." --test "..."
teamwork.py pr open --agent developer-1 --task T-0007 [--push]
# 4. the Reviewer verifies and rules
teamwork.py review developer T-0007 --by reviewer --result fail  --findings "..."
teamwork.py review developer T-0007 --by reviewer --result pass  --evidence "..."
# 5. only the Reviewer merges, and only after a pass
teamwork.py pr merge --pr P-0003 --by reviewer-2 [--squash] [--delete-branch]
```

Rules enforced mechanically:

- `commit` refuses to run on `main` (`--allow-main` overrides, and must be
  justified); work belongs on a task branch.
- `pr open` refuses without a branch and without a recorded self-check.
- `pr merge` refuses if `review_status != passed`, and refuses a merger that is
  not the Reviewer - an author can never merge their own work.
- a merge conflict aborts cleanly and comes back to the owner to rebase.
- **the merged branch is deleted** (`pr merge` retires it, including its worktree;
  `--keep-branch` opts out). `audit` and `loop` report merged-but-still-open
  branches until they are gone.
- with several Reviewers, the instance that passed the verdict cannot also merge
  it: one verifies, another merges. With a single Reviewer instance the same one
  does both, recorded as `review.merge_self` and flagged by `audit`.
- the merge commit is authored by `Reviewer <reviewer@agents.nidvue.com>` and carries
  the fixed message style (`chore(merge): ...`, evidence pointer to the review).
- generated records (Archive.md, Board.md, Plan.md) are committed by the Reviewer
  as `chore(records): ...` immediately before the merge, so the ledger matches the
  merged revision.
- PR records live in `.pi/Teamwork/Teams/<Team>/Reviews.md` (hidden local state);
  the merged revision is recorded on the task as `merge_commit`.

`teamwork.py branch list` shows branch -> PR -> merged state;
`teamwork.py pr list [--open]` is the Reviewer's PR inbox; `audit` and `loop`
report branches that are not merged.

## Push policy - reviewed and staged, never batched

The **Release Engineer** is the role that pushes to the shared remote, and only
after the **Reviewer** has passed the revision with no open finding.

- **Per milestone.** Push after each reviewed + merged deliverable so the remote
  does not drift far from local `main`. Do not sit on a stack of unreviewed
  commits and do not wait for the release to push.
- **Pre-push gates on the exact revision:** build, tests, `privacy_scan.py
  --tree --history`, and the link check all green. A red gate is not pushed.
- **Post-push:** watch CI and confirm green **on that SHA**; record the revision,
  run ids and conclusions.
- **Red run -> route it.** Code -> Developer, test -> Tester, contract ->
  Architect, workflow/packaging/flake -> Release Engineer, scope -> CEO. Re-run
  after the fix.
- **Red lines:** force-pushing a shared branch, rewriting published history or
  retagging a release needs the CEO's explicit authorization and is recorded with
  `teamwork.py redline record`. Tags and public releases are the CEO's step,
  prepared and verified by the Release Engineer.
- **Never push a secret.** The privacy scan is the gate that enforces it.

## Worktrees (optional but recommended for parallel writers)

`branch start --agent <Instance> --task <T-id> --worktree` creates the branch,
adds a worktree at `<Team>/Runtime/Worktrees/<Instance>/` and records both on the
task. The main tree stays on its own branch; the agent works inside the worktree.

- Run `teamwork.py` from the worktree: it resolves the team from the path
  (`Runtime/Worktrees/<Instance>` -> team root), so you never need `--project`,
  and it never creates a second team tree.
- From anywhere else, pass `--project <repo>` or set `TEAMWORK_ROOT`.
- `pr merge --delete-branch` also retires the worktree when the branch is still
  checked out there.

## Worktree location

All worktrees, clones and scratch state live inside the repository at
`<Team>/Runtime/Worktrees/<Instance>/` (managed by `branch start --worktree`). Never create a
worktree, clone or scratch workspace in `$HOME`, `/tmp`, a sibling directory, or
any path outside the repository.

## Repo-local working state

A repository's wiki clone lives at `<repo>/.pi/wiki/`, never beside it. All
per-repository working state stays under that repository's own `.pi/`.

## Worktree hygiene

At the start and end of each task remove your own scratch: temp logs, one-off
dumps, finished-task artifacts. Cleanup is untracked/ignored-only; never delete
tracked, uncommitted, unmerged or evidence-bearing files, and never run
`git clean -fdx`. Prefer `teamwork.py clean` (temp patterns) and
`teamwork.py clean --all` (your `Scratch/`). Keep `Artifacts/` and `Reports/` for
things that are actually deliverables or evidence.

## Build economy

Never delete build caches to get a "clean slate": no `cargo clean`,
`rm -rf target/`, `rm -rf node_modules/`, `rm -rf dist/ build/ .venv/`. Build
only the touched scope; run the workspace-wide suite only at the pre-merge gate.
Reuse or cite an existing green run on the same revision instead of re-running
it. Report `BUILD: <command> · built|reused · <seconds>`.

## File discipline

Keep only what the project needs. Update an existing document instead of creating
a near-duplicate; delete superseded drafts; don't commit generated files, caches,
editor noise or local state. Every file in the repository should be something the
project needs to build, run, test, document or ship.
