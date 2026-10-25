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
- **The role that does the work commits it.** Developer commits code and unit
  tests, Tester integration/E2E tests, Technical Writer documentation, Architect
  contracts and ADRs, Release Engineer workflows and release changes, Reviewer
  merge commits. The CEO commits only CEO-owned documents (`Project.md`,
  `Plan.md`, `Board.md`, `Decisions.md`) and the bootstrap commit - never another
  role's deliverable in its place.
- The product identity `Teamwork <teamwork@agents.nidvue.com>` is **never** a valid
  commit identity: it names the skill, not a role.
- CI enforces this with `teamwork.py identity --audit --range <base>..HEAD`; it
  checks the author, the committer and the `Acting role:` trailer, and allows bot
  dependency updates (`dependabot[bot]`, `github-actions[bot]`, `renovate[bot]`).
- Apply it per commit, without changing the repository config:

```sh
git -c user.name="Developer" -c user.email="developer@agents.nidvue.com" commit ...
```

`teamwork.py commit --role <role> ...` does this for you, and
`teamwork.py identity [--role X]` prints the exact identity.
`TEAMWORK_IDENTITY_DOMAIN` overrides the email domain.

### The constitution, quoted

`AGENTS.md` (Commit identity) is the rule; text in a charter or a reference that
departs from it is wrong, whatever the repository's local configuration says:

- Commit as the **acting role mailbox**: `author == committer ==
  <Role> <role@agents.nidvue.com>` - the role that did the work, never an instance
  number, never another role's mailbox, never the operator's account.
- Apply it **per commit**: `git -c user.name=<Role> -c user.email=<role>@agents.nidvue.com
  commit ...`, or `teamwork.py commit --role <role> ...`, which does the same.
- End the message with `Acting role: <Role>`; the identity gate fails when that
  trailer does not match the author.

A plain `git commit` inherits whatever the repository's own `user.name` / `user.email`
happens to be configured to, and the identity gate fails that commit unless the
configured identity is the acting role mailbox. The repository-local config is
therefore a convenience fallback only and no lane may read it as permission to
skip the per-commit form above.

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
- The threshold is a **binary** threshold (1 MiB = 1048576 bytes), and it is
  decided by **content**, not by the file name: a file is binary when its first
  8192 bytes contain a NUL byte, **except** a head that decodes as printable
  UTF-16 (a UTF-16 document also contains NUL bytes and is still text).
- `teamwork.py commit` refuses to commit a **binary** file above
  `--lfs-threshold` (default 1 MiB) that no LFS pattern covers. A **text**
  record is never refused by the threshold, at any size: it stays a plain file.
- `teamwork.py commit` also refuses a **text** file that a `.gitattributes`
  LFS pattern would route into Git LFS. `.gitattributes` routes a file into
  LFS **by name**, so a text file can be routed there by accident - and a
  document in LFS is a pointer for every reader without an LFS client. The
  check is size-independent, because a text file in LFS is broken at any size.
- The pre-commit hook rule R2 applies the same threshold, the same binary test
  and the same text/LFS mismatch check, so the hook and `commit` agree about
  every file.
- `teamwork.py audit` reports LFS readiness, any large **binary** file no LFS
  pattern covers, and any **text** file a pattern routes into LFS. A large text
  record that no pattern captures (the growing `docs/Team/Archive.md` is the
  standing example) is not a finding.
- A large text record is a **document**: it is committed as a plain file, it
  grows, and the threshold says nothing about it. LFS is for binaries
  (weights, datasets, fonts, native libraries, 3D assets) - a text record in
  LFS is unreadable without a client, and the link check would follow a
  pointer instead of a document.
- The rule, the three gates and the one shared predicate are frozen in
  [Architecture.md](../docs/Team/Architecture.md) section 11.10.

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
- a passing review merges the PR itself: the lane that verified the revision runs
  the merge and deletes the branch, so an approved deliverable never waits for a
  second lane. Independence is enforced against the **author** (never their own
  review or merge), not against a second Reviewer; `--no-merge` separates them when
  a project wants two pairs of eyes on the landing step.
- the merge commit is authored by `Reviewer <reviewer@agents.nidvue.com>` and carries
  the fixed message style (`chore(merge): ...`, evidence pointer to the review).
- generated records (Archive.md, Board.md, Plan.md) are committed by the Reviewer
  as `chore(records): ...` immediately before the merge, so the ledger matches the
  merged revision.
- the archive entry is written at review time, before the merge revision exists,
  so its `branch / merge` field says `pending`; `pr merge` repoints that one line
  to the merge revision and commits the rewrite as a second `chore(records): ...`
  on the base branch (ledger `pr.merge.archive`). The rewrite is never left as an
  uncommitted edit, which would keep `pending` in HEAD and block the next merge
  on a dirty tree. Only an entry still saying `pending` is repointed, and of
  several such entries for one branch only the newest: a reworked task reuses its
  branch name, so rewriting every match would erase the earlier merge revision.
- PR records live in `.pi/Teamwork/Teams/<Team>/Reviews.md` (hidden local state);
  the merged revision is recorded on the task as `merge_commit`. `find_pr` and
  `find_pr_exact` take the branch as an optional third argument, and every PR
  lookup in the merge path passes it: a task reworked after a merge keeps the old
  PR record, so matching an id or a task alone can return the branch that is
  already in the base.

`teamwork.py branch list` shows branch -> PR -> merged state;
`teamwork.py pr list [--open]` is the Reviewer's PR inbox; `audit` and `loop`
report branches that are not merged.

## Push policy - reviewed and staged, never batched

The **Release Engineer** is the role that pushes to the shared remote, and only
after the **Reviewer** has passed the revision with no open finding.

- **Per stage.** A stage ends with a push, not with a merge: once a coherent
  stage is squashed, rebased and merged and the gates below are green on that
  revision, push it, so the remote does not drift far from local `main`. Do not
  sit on a stack of unreviewed commits and do not wait for the release to push.
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
- **Never push a secret or local state.** The privacy scan is the gate: it fails
  on credentials, on private agent-host configuration (auth, settings, sessions,
  model stores) and on tracked local state (`.pi/`, virtualenvs, build output,
  caches, `Scratch/`).

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

## Linting, formatting and type checking

Style is not a matter of taste and not a review topic. It is **automated**: a
machine formats and lints the code, the CI fails when it would have changed
anything, and the reviewer reviews behaviour instead of whitespace. A human never
hand-formats, never argues about line length, and never disables a rule without a
recorded reason.

Rules:

- **One canonical toolchain per language**, configured in the repository and
  reviewed like code. Do not introduce a second formatter or a competing config.
- **Run the fixer before you commit**, then the checker: `make format && make
  lint` (or the language equivalent). The CI form check is not a suggestion -
  unformatted code does not merge.
- **Type-check where the language supports it** (and run the static analyser
  where it exists). A type error is a defect, not a style opinion.
- **Never weaken the gate to pass**: no blanket `# noqa`, no rule removed from the
  config, no formatter excluded from a directory, no `--fix` on a file you did not
  read. If a rule is genuinely wrong for this codebase, disable it *narrowly* with
  a one-line reason in the config and record the decision.
- **Generated code is excluded explicitly**, never left unformatted by accident.
- **Evidence**: the lint/format command and its result go in the task evidence,
  on the same revision as the tests.

| Language | Formatter | Linter | Types / static analysis |
|---|---|---|---|
| Python | `ruff format` | `ruff check` | `mypy` |
| JavaScript / TypeScript | `prettier --write` | `eslint` | `tsc --noEmit` |
| Go | `gofmt` / `goimports` | `go vet`, `staticcheck` | the compiler |
| Rust | `cargo fmt` | `cargo clippy -- -D warnings` | the compiler |
| Java / Kotlin | `spotless:apply` | `checkstyle` / `ktlint` | the compiler |
| C / C++ | `clang-format` | `clang-tidy` | `-Wall -Wextra -Werror` |
| Shell | `shfmt -w` | `shellcheck` | - |
| YAML | `prettier` / `yapf`-style | `yamllint` | - |
| Markdown | `prettier` / `markdownlint --fix` | `markdownlint` | - |
| JSON | language formatter | schema check | - |
| Terraform | `terraform fmt` | `tflint` | `terraform validate` |
| Dockerfile | `hadolint` | `hadolint` | - |

This repository uses the Python row: `ruff check .`, `ruff format --check .` and
`mypy src/teamwork` run in CI (see `pyproject.toml`), and `make lint` /
`make format` wrap them.

## Naming - PascalCase, camelCase, and the ecosystem's rule

Team-created **directories** are PascalCase (`docs/Team/`, `Roles/Developer/`,
`Agents/Tester-1/`, `Runtime/Locks/`). **File names** follow the ecosystem, and
PascalCase or camelCase are perfectly acceptable wherever the ecosystem allows
them - a name is wrong only when it fights its language or its neighbours.

| Kind | Convention | Example |
|---|---|---|
| Team directory | PascalCase | `Agents/Developer-1/`, `docs/Team/` |
| Docs page | PascalCase, kebab only for multi-word slugs | `Architecture.md`, `quick-start.md` |
| Python module / package | `lower_snake_case` (it *is* the import name) | `resources.py`, `teamwork/` |
| Python class / exception | `PascalCase` | `SkillRoot`, `VerificationError` |
| JS / TS component | `PascalCase` file | `ButtonGroup.tsx` |
| JS / TS module, helper | `camelCase` file | `buildIndex.ts` |
| Function / variable | snake_case (Python), camelCase (JS/TS) | `read_text`, `readText` |
| Constant | `UPPER_SNAKE_CASE` | `IDENTITY_DOMAIN` |
| Test file | source name + the ecosystem's test affix | `test_imaging.py`, `Button.test.tsx` |
| Tool-mandated file | the tool's name, never renamed | `pyproject.toml`, `Makefile`, `AGENTS.md` |

Rules: be consistent inside a directory; never rename a file just to satisfy
taste; never break an import name, a case-sensitive module path or a tool's
mandated filename for a naming preference; and if two conventions collide, the
ecosystem's rule wins over a local habit.

## Commit hygiene - rebase and squash before review

Commit while you work, then **clean up before the review**. A reviewer reads the
final diff; the intermediate noise is your problem, not theirs.

- `git rebase -i` onto the latest default branch, squash `wip` / `fixup!` /
  "oops" commits, reorder into a logical sequence, and drop debug leftovers.
- Each commit is one coherent, self-contained change-set that follows the commit
  style. A commit whose only purpose is to repair the previous commit is noise.
- **Target one commit per task.** Squash-merge into the default branch produces
  exactly that, so the history reads as one idea per task.
- Rebase onto the default branch before opening or updating the request, and
  resolve conflicts locally - never in the merge UI.
- **Never rebase or force-push a shared branch**, and never rewrite a commit that
  is already on the default branch or a published tag: rewrite only your own
  unpushed work. Anything else is a red line needing the CEO's authorization.
- Rebasing is not a way to hide a review: the Reviewer sees the squashed diff and
  the conversation that produced it.

## Warnings are errors

A warning is a defect that has not broken anything **yet**. Treat every one as a
failure: the build, the tests, the linter, the type checker, the compiler and the
CI annotations must all come out clean, and "it is only a warning" is not an
argument a reviewer accepts.

- **Make the tool fail on warnings**, in the config, not in a habit:
  `ruff check` (any finding fails), `mypy --warn-unused-ignores` +
  `--warn-redundant-casts`, `pytest -W error` (plus
  `filterwarnings = ["error"]` in `pyproject.toml`), `cargo clippy -- -D warnings`,
  `go vet ./...`, `eslint --max-warnings 0`, `tsc --noEmit` (strict),
  `-Wall -Wextra -Werror`, `shellcheck -S style`, `hadolint --failure-threshold style`.
- **Fix the cause.** Upgrade the dependency, replace the deprecated call, delete the
  dead branch, annotate the type. A warning whose root cause is fixable is not
  exempted.
- **Suppress narrowly when the cause is genuinely external** (a third-party
  deprecation that no version fixes yet): one line, one rule, one path - never a
  project-wide blanket - always with a reason and, where possible, the version or
  date at which the exemption is re-checked. A blanket `# noqa`, a global
  `filterwarnings = ["ignore"]` or a deleted rule is a red line.
- **CI annotations count.** A "Node.js 20 is deprecated", an unpinned action, a
  cache-path notice or a deprecation banner in a workflow log is a warning: bump
  the action, add the cache step or remove the step that produces it.
- **Test output counts.** Warnings raised by the project's own code fail the suite;
  warnings from a dependency get a narrow, reasoned filter entry.
- **Evidence**: the clean run - `pytest -q` with zero warnings, `ruff check` clean,
  `mypy` clean - goes in the task evidence on the same revision as the tests.

## File discipline

Keep only what the project needs. Update an existing document instead of creating
a near-duplicate; delete superseded drafts; don't commit generated files, caches,
editor noise or local state. Every file in the repository should be something the
project needs to build, run, test, document or ship.

### Comments - write none that the code already says

A comment is a maintenance liability: it is not compiled, it is not tested, and
it goes stale silently. Add one only when the *why* cannot be expressed in the
code itself.

Write a comment **only** for: a non-obvious reason or constraint (a spec, a bug
workaround with its reference, a platform quirk, a security decision), a public
API contract that a caller cannot infer, or a unit that is genuinely ambiguous.

Never write:

- a comment that restates the next line (`# increment i`);
- section banners for self-evident code (`# --- helpers ---` over three helpers);
- a docstring that repeats the function name (`"""Return the name."""`);
- changelog-in-code (`# added in v1.2`, `# removed the old branch`);
- commented-out code - delete it, git remembers;
- `TODO` / `FIXME` / `XXX` / `HACK` with no owner and no tracked task; if it
  matters, file it as a task and cite the id, otherwise drop it;
- a comment that contradicts the code. A stale comment is a defect: fix or delete
  it in the same change that made it stale.

Prefer a clear name, a small function or an explicit type over an explanatory
comment. When a comment is warranted, write what the code cannot say, in one line.

### Working tree - clean, structured, current

- **One canonical home per file.** Do not scatter drafts next to the real thing.
- **Delete temp and stale files as you go**: `*.orig`, `*.rej`, `*.bak`, `*~`,
  `*.tmp`, `*.log`, `.DS_Store`, `Thumbs.db`, generated caches, scratch copies,
  superseded drafts, empty directories. `teamwork.py clean` removes the patterns
  it knows; do the rest by hand in the same task, not "later".
- **Never commit** build output, caches, local state, editor noise, secrets, or a
  file whose only purpose is to be regenerated.
- **Scratch stays private and ephemeral**: `Agents/<Instance>/Scratch/`, gitignored,
  emptied before the task closes. If a scratch artefact is worth keeping, move it
  to its canonical path and commit it; if not, delete it.
- **Leave the tree cleaner than you found it.** A reviewer who cannot tell
  deliverable from debris will fail the task.
