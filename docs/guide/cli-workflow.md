# CLI: feature teams and git workflow - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [CLI reference](cli.md)

Feature-team records, branches, pull requests, commits, identities and the
installed git hooks.

This page is one part of the [CLI reference](cli.md) set; the overview lists every group.

## Feature teams

A **feature** is one vertical slice one squad can build, test and ship without
another squad's merge. One Team Leader owns it and its squad; several teams work
in parallel; one Architect freezes every interface and one Project Manager keeps
the record set. The records live in **one committed file**,
`docs/Team/Features.md`, because the independence rule below is a predicate over
all open features at once - split it per team and no single read answers the
question, so two leaders can each "win" their own check without either having
seen the other.

The file is an ordinary committed document: `feature add` and `feature set` write
it **in the caller's checkout**, under `Runtime/Locks/features.lock`, and the
caller commits its edit on its own branch. The Reviewer's merge lands it. A
conflict in it is a document conflict the merging Reviewer resolves one row
against another; no command picks a winner.

### `feature`

```text
teamwork feature add STATEMENT --owner TEAM_LEADER --paths P[,P...]
                     [--interface REF] [--depends-on F-nnnn[,F-nnnn...]]
                     --by BY [--json]
teamwork feature set F-nnnn --state STATE [--interface REF] [--paths P[,P...]]
                     [--depends-on F-nnnn[,F-nnnn...]] --by BY [--json]
teamwork feature list [--state STATE] [--json]
teamwork feature check [F-nnnn...] [--json]
```

`--by` is **required** on `add` and `set`: it is the caller naming itself, and the
authority is checked on what it resolves to. It resolves in `allow_role=False`
mode - an instance whose name matches, a bare role with exactly one instance, or a
refusal (a role name satisfies no instance check) - and a `feature` write exits
`2`, never the engine's default `1`.

#### The record

| Field | Meaning | Who may write it |
|---|---|---|
| `id` | `F-nnnn`. Allocated as one more than the highest number visible at the caller's revision. There is no counter file and no reservation: a refused `add` writes nothing and consumes nothing, so the next successful add offers the same number. An id is never reused, and a landed record's id never changes | the command |
| `statement` | One line: what ships, as the user-visible result. A second feature stating the same thing is not a refusal; `add` prints `teamwork: F-0001 already records that statement - not duplicated` and exits `0` | the owner |
| `owner` | Exactly one `team-leader` instance, the squad's only manager. At `add` it must be the caller, so no lane can file a slice on another leader's behalf, and a leader holds one open feature at a time | the owner |
| `interface` | The frozen-interface reference: an anchor in `Architecture.md` (`Architecture.md#13`) or a decision id (`D-20261029-Architect-2`). `-` while the record waits on its freeze | an `architect` caller |
| `paths` | Comma-separated owned writable paths: the feature's whole write set. Required and non-empty - a feature that owns no path cannot be independent of anything, it is a plan, not a slice | the owner, validated by the command |
| `depends-on` | Comma list of `F-nnnn` **work** dependencies, or `-`. A dependency is green only when the target is `done`; a feature that needs only an earlier feature's contract records the frozen anchor in `interface` instead and has no dependency at all | the owner |
| `state` | `proposed` -> `ready` -> `active` -> `done`, or `dropped` | the command, on `feature set` |
| `created`, `updated` | ISO dates, the audit pair every record carries | the command |

#### The states

| Transition | Who may issue it | What it releases |
|---|---|---|
| `proposed` -> `ready` | an `architect` caller | the freeze. The record enters the open set: `feature check` starts comparing its paths, `task add --feature` accepts the id and `pulse` prints its team line. Nothing executes yet |
| `ready` -> `active` | the record's `owner` instance | **execution**: `task next` hands the squad the tasks carrying the feature, and `feature`-layer test records may be opened. A `ready` feature's tasks are queued and held |
| `active` -> `done` | the record's `owner` instance | the owned paths (a closed record is released, not compared), every dependency on it turns green, the leader's one-open-feature slot frees, and the `feature`-layer record closes with its merge evidence |
| `proposed`/`ready` -> `dropped`, and `active` -> `dropped` once every task carrying the feature is terminal | the record's `owner` instance | the same releases as `done`; the id stays taken |

`done` and `dropped` are terminal: reopening is a new record with a new id. A
`done` transition waits until every task carrying `feature: F-nnnn` is `done`, and
`dropped` from `active` waits until every such task is terminal. `paths` cannot
change once the record is `active` - the claim is final when the work starts.

```text
teamwork: features + F-0003 [proposed] ship the record set  owner=TeamLeader-1 paths=2
teamwork: features ~ F-0003 [proposed] -> [ready] interface=Architecture.md#13
```

`set` prints the from/to pair and then one `<field>=<value>` per changed field, in
the record's field order (`interface=`, `paths=<n>`, `depends-on=`); a field the
command did not change is not printed, so a pure transition prints the pair only
and `set --state ready` on a `ready` record prints `[ready] -> [ready]`. Edits are
applied before the state is evaluated, so `set F-0003 --state ready --interface
Architecture.md#13` is one command.

A refusal is one shape per verb, and the reason is one sentence from a closed set:

```text
teamwork: no feature added: F-0002 F-0001 share a writable path: src/a.py
teamwork: F-0003 stays [proposed]: ready needs a frozen interface: --interface <anchor-or-decision>
teamwork: F-0003 stays [ready]: active is the record owner's transition: --by must be TeamLeader-1 (you are TeamLeader-2)
teamwork: F-0003 stays [active]: done while 2 task(s) carrying feature: F-0003 are not done (T-0071, T-0072)
teamwork: F-0003 stays [active]: dropped from [active] needs every task carrying feature: F-0003 terminal (open: T-0071)
teamwork: F-0003 stays [active]: paths cannot change from [active]: the claim is final when the work starts
teamwork: F-0003 stays [dropped]: a record in [dropped] is terminal; open a new feature
teamwork: F-0003 stays [proposed]: a state cannot be skipped forward (proposed -> ready -> active -> done)
teamwork: F-0003 stays [proposed]: unknown state 'shipped' (proposed, ready, active, done, dropped)
```

`F-0003 stays [-]` when no such record exists.

#### `feature list` and `feature check`

```text
# Features (2 open / 3 total) @ 1a2b3c4
- F-0001 [active] ship the record set
    owner=TeamLeader-1 interface=Architecture.md#13
    paths=src/a.py,src/b.py
    depends-on=-
```

The header is dated: `@ <short-sha>` when the working copy is clean, so the bytes
read are exactly that revision's, and `@ worktree` when it is not - an uncommitted
row or edit is at no revision, and printing `HEAD` for it would date the answer to
a commit that does not contain it. `--state` filters the listing and both counts
then describe the filtered set; a filter that matches nothing prints the header
and exits `3`. An unknown state exits `2`.

`feature check` evaluates **rules 1-4 over the open records** (`ready` and
`active`) and **rule 5 over every record**, open or closed:

| # | Rule | Finding |
|---|---|---|
| 1 | no two open features own overlapping writable paths | `F-0001 F-0002 share a writable path: src/a.py` |
| 2 | no open feature depends on another feature's in-flight work | `F-0001 depends on in-flight F-0002 (state=active)` |
| 3 | one open feature per leader | `TeamLeader-1 owns 2 open features: F-0001, F-0002 (rule 2: one open feature per leader)` |
| 4 | no owned path is a glob, outside the repository, checkout state, a generated artifact or the records file | `F-0001 claims a glob (src/*.py); name the directory instead` |
| 5 | no two records carry one id, over every record | `F-0001 is allocated twice (TeamLeader-1, TeamLeader-2); renumber the arriving record before it lands` |

Both sides of a comparison are normalised once (`\` to `/`, no leading `./`, no
repeated `/`, no trailing `/`, NFKC, then case-folding) and then a claim covers
another when they are equal or one is a directory above it, matched on `/`. So
`src/teamwork` and `src/teamwork/` are the same claim and cover
`src/teamwork/engine.py`, while `engine.py` and `engine_extra.py` do not collide.
Nothing is `stat`'ed and no glob is expanded, so a dirty worktree and a fresh clone
answer the same question. A path is inside the repository by a **string** test:
not absolute, no drive prefix, no `..` segment - `src/new_module.py` is inside
whether or not it exists. Case differences are a collision on every platform, and
a closed record's paths are released rather than compared.

```text
# feature check: 2 open feature(s), 0 problem(s) @ 1a2b3c4
teamwork: feature check: 1 problem(s) in 2 open feature(s) @ 1a2b3c4:
  - F-0001 F-0002 share a writable path: src/a.py
  ...
```

`check` exits `0` green, `2` on any finding or an unknown id, and `1` only when
the records file cannot be read at all. `feature check F-0003` checks exactly the
named records: a named `done`/`dropped` record contributes no finding except a
rule-5 duplicate.

**A shared frozen interface is not a collision.** Two features that name the same
anchor in `interface` are parallel work - the Architect froze it before either
squad started - which is the whole point of the field. What is refused is a shared
*writable path*.

**The duplicate id, and the renumber rule.** Allocation is max+1 per revision, so
an id cannot be duplicated inside one branch and can be across two: two leaders
cut from the same base each read `F-0003` as free and each branch carries a row
with that id. Neither allocation is a mistake and neither row is discarded. The
merge path runs `feature check` at the merged tree and refuses the merge with the
rule-5 finding, and the **merging Reviewer** resolves it as a document conflict:
the record already reachable from the target branch keeps its id, because that id
is already in the target's history; the record **arriving from the branch** is
renumbered to the next free `F-nnnn` at the merged tree, in one edit to its `id`
and to the `feature: <old id>` field of every task on that branch that carries it.
`statement`, `owner`, `paths`, `depends-on`, `state` and `interface` are
untouched, nothing is dropped and nothing is refiled, and the renumber happens
**before** the record lands. Because the check reads only the caller's revision, a
lane whose branch predates another feature's record can be green while the merged
tree is red; rebase before you check, and read the `@ revision` the answer is
dated at. `preflight`, `review --result pass` and `pr merge` all run the check at
the tree that would be landed, so the collision is refused there instead.

#### `--json`

One object per invocation, keys in the order written, nothing else on stdout, and
the exit code is identical with and without the flag:

```json
{"id": "F-0003", "state": "ready", "changed": true, "rev": "1a2b3c4"}
{"rev": "1a2b3c4", "open": 2, "total": 3, "features": [{"id": "F-0001", "statement": "...", "owner": "TeamLeader-1", "interface": "Architecture.md#13", "paths": ["src/a.py"], "depends_on": [], "state": "active", "created": "2026-10-29", "updated": "2026-10-29"}]}
{"rev": "1a2b3c4", "ok": true, "features": 2, "problems": []}
```

A refusal prints the same reason string the plain line carries - `{"id": null,
"state": null, "changed": false, "reason": "...", "rev": "..."}` for `add` (no
number is allocated, so none is printed or consumed) and the record's id and
current state for `set` - so a script never has to parse prose twice. A read
verb's misuse prints `{"rev": "...", "error": "..."}`.

## Git workflow

### `branch`

```text
teamwork branch {start,list} ...
```

#### `branch start`

```text
teamwork branch start --agent AGENT --task TASK [--base BASE] [--worktree]
```

Create and switch to the task branch. `--worktree` uses a separate worktree
under `Runtime/Worktrees/`.

#### `branch list`

```text
teamwork branch list
```

Branches with PR and merge state.

### `pr`

```text
teamwork pr {open,list,merge} ...
```

#### `pr open`

```text
teamwork pr open --agent AGENT --task TASK [--title TITLE]
    [--summary SUMMARY] [--base BASE] [--push]
```

Submit a PR to the Reviewer. `--push` pushes the branch if a remote exists.

#### `pr list`

```text
teamwork pr list [--open]
```

The Reviewer's PR inbox.

#### `pr merge`

```text
teamwork pr merge --pr PR [--by BY] [--squash] [--keep-branch]
    [--delete-branch] [--force REASON]
```

Reviewer: merge an approved PR. The merged branch is deleted unless
`--keep-branch` is given. `--force` overrides the review gate and requires a
recorded reason. `--pr` takes a PR id or a task id; a task id is resolved
against the task's current branch, so a task reworked after an earlier merge
reaches its live PR record instead of the one already integrated in the base.

The merge always advances the base *branch*: a base recorded as a revision
instead of a branch name is mapped back to the local branch pointing at that
commit (preferring `main`, accepting a unique match) and refused with exit `2`
when no branch points at it, because a merge built on a detached HEAD leaves the
base where it was and publishes nothing. The merge runs in the work tree that
has the base checked out, so a merge started from an instance worktree still
lands on the base instead of failing on `git checkout`.

Before it touches the work tree, `pr merge` re-runs the mergeability probe
against the base it is about to advance (`git merge-tree --write-tree <base>
<branch>`) and refuses with exit `2`, naming the conflicting paths and the rebase
command, when the branch no longer merges. A verdict is a statement about a
revision, not a promise that the base has not moved since it was recorded, so
nothing is checked out, committed or recorded on that path. `--force <reason>`
records the override in the `pr.merge.forced` ledger record.

After the merge the `branch / merge` line of the matching
`docs/Team/Archive.md` entry is repointed from `pending` to the merge revision
and that one-line rewrite is committed on the base branch as its own
`chore(records)` commit (Reviewer identity), so the archive never disagrees with
the branch history and the work tree is left clean for the next merge. If the
base branch has no entry for the branch yet - the review pass writes entries in
whatever work tree it ran in - the accepted-results entry is appended on the
base first and rides along in the same commit, so the base always records what
shipped. Only an entry still saying `pending` is repointed: a task reworked
after a merge reuses its branch name, and rewriting every match would erase the
earlier merge revision from the archive.

After the merge and its records commit, the merging Reviewer re-renders
`docs/Team/Board.md` from the role queues with the product's own renderer
(`teamwork.board`) and commits it as another `chore(records)` commit. The landing
has just moved this task to `done` with its merge revision, so this is the only
render that can leave a board equal to the queues - including rows another lane
moved while the branch waited. A render that cannot be written or committed is
reported as `the merge ... is LANDED, but docs/Team/Board.md ... is STALE`, with the
`board --write` repair command; the merge record is never rolled back.

### `commit`

```text
teamwork commit [--role ROLE]
    [--type {feat,fix,test,docs,design,research,refactor,perf,build,ci,chore,revert}]
    [--area AREA] [--task TASK] [--producers PRODUCERS] [--goal GOAL]
    [--deliverable DELIVERABLE] [--why WHY] [--status STATUS] [--result RESULT]
    [--docs DOCS] [--refs REFS] [--paths PATHS] [--all] [--allow-main]
    [--dry-run] [--no-check-lfs] [--lfs-threshold LFS_THRESHOLD]
```

Commit a change-set with the fixed style and the role commit identity.

| Option | Meaning |
|---|---|
| `--paths` | Comma-separated paths to stage. |
| `--all` | Stage every change. |
| `--allow-main` | Override the main-branch protection (rare; explain why). |
| `--no-check-lfs` | Skip the large-file LFS check (enforced by default). |

### `identity`

```text
teamwork identity [--role ROLE]
teamwork identity --audit [--range REV..REV] [--strict-authors] [--guard-committer]
```

Show the role commit identity, e.g. `Developer <developer@agents.nidvue.com>`.

`--audit` fails when a commit in the range was not authored and committed by the
acting role. It checks the author, the committer and the `Acting role:` trailer,
skips the forge's synthetic pull-request merge ref, and allows bot dependency
updates only when both the bot name and a `users.noreply.github.com` mailbox
match. An author outside the team identity domain is reported as skipped by
default; `--strict-authors` turns that into a failure. The default range
is `origin/main..HEAD`, then `HEAD~1..HEAD`, then `HEAD`; a range beginning with
`-` is rejected. CI runs it on every pull request and every push to `main`.

`--guard-committer` is the narrower gate CI runs on every push (the
`committer-guard` job). It passes a commit when its **committer** is a role
mailbox, and it also passes the host stamp a forge writes into the commit it
creates - `noreply@github.com` (or `noreply@gitlab.com`) - but only when the
**author** of that commit is a role mailbox or an allowlisted bot dependency
update (`dependabot[bot]`, `github-actions[bot]`, `renovate[bot]` with their
`users.noreply.github.com` mailbox). The host stamp is transport, not identity;
the author still has to be the team or a bot. So the guard does read an author
fact: a host-stamped commit with a personal author fails. Measured on a commit
authored by `jane@example.com` and committed by `GitHub <noreply@github.com>`,
`guard_committer_identity()` exits 1 with `- 5d4b5393b3d1 FAIL committer GitHub
<noreply@github.com> (author Jane Doe <jane@example.com>)`. The full author
check is `--audit`, which CI runs on every pull request and every push to
`main`.

### `harness`

```text
teamwork harness list
teamwork harness lint [--verbose]
teamwork harness budget [--limit KB] [--recallable]
```

The harness is everything around the model: the always-on prompt and rules, the
memory, the tool guidance, the skills, the scripts and the in-loop hooks. This
group names that surface, validates it, and prices it.

| Subcommand | What it does |
|---|---|
| `list` | eight rows, one per component (C1..C8), each with its activation class, the bytes it costs and the role that owns it. `always-on` is paid on every run, `on-demand` only when invoked, `in-loop` is enforced rather than instructed. C5 (subagents) is a lane packet, not a file, so its class and bytes are `-`. |
| `lint` | the whole-proposal checks, before anything is probed: `IDENTITY` (frontmatter `name:` equals the directory, `description:` non-empty), `TRIGGER` (the skill is named in an always-on surface - an unnamed skill is dead text nobody is told to load), `SUBCOMMAND` (every `teamwork.py <verb>` in a skill exists in the CLI), `HELPER` (every repo-relative path a skill references is shipped), `EVIDENCE` (a registered `shared` skill carries a verdict row). Exit 1 with one `- PROBLEM <RULE> <path>: <detail>` line per finding. `--verbose` also prints one `# checked: <file> -> <RULE> verdict` line per file read. |
| `budget` | the **startup** read per instance - `AGENTS.md` block + `SKILL.md` + the role charter + short memory + open lessons + top-10 knowledge - against `AlwaysOnBudgetKb` in `Settings.json` (default 120 KiB = 122880 B; `--limit` overrides for one run). Exit 1 when any instance is `OVER`: always-on prose is the expensive option, so the cap is what makes "cut something to pay for it" a rule rather than an intention. `--recallable` prints the recall-only bytes instead - long-term/archived memory, fixed lessons and superseded knowledge, which `load` never prints; it is a visibility row, not a second cap. |

`list` and `lint` work from any checkout; `budget` needs the team workspace
because it measures it. A hook installed by `hooks install` is measured through
`git rev-parse --git-path hooks`, so a linked worktree reports the hook that is
actually running rather than a zero from a path that does not exist.

### `hooks`

```text
teamwork hooks install [--force] [--reason WHY]
teamwork hooks status
teamwork hooks uninstall
teamwork hook pre-commit
teamwork hook pre-push [REMOTE] [URL]
```

Install, inspect or remove the two git hooks that enforce, in the tool loop, the
rules the prose can only ask for. `install` writes `pre-commit` and `pre-push` into
the directory git actually reads hooks from (`git -C <root> rev-parse
--path-format=absolute --git-path hooks`), so it works in a linked worktree where
`<toplevel>/.git` is a file, and it honours `core.hooksPath`. Hooks are opt-in:
`teamwork init` never installs them, and `TEAMWORK_SKIP_HOOKS=1` makes both exit 0
unchanged.

`install` works **per stage**. A stage that already belongs to someone else - the
common case is `git lfs install`, which writes `.git/hooks/pre-push` - does not
block the other one: the foreign hook is moved to `<stage>.teamwork-foreign` and
run by the teamwork hook after the rules pass, so the LFS hook keeps working and
`pre-commit` (R1, no commit on the default branch) is installed regardless. The
refspec list git writes to `pre-push`'s stdin is copied once and fed to both hooks.
`hooks status` says which stages chain a preserved hook. `hooks uninstall` hands
the preserved file back its own name instead of leaving it stranded.
`--force` replaces a foreign hook instead of preserving it, and then `--reason` is
required: the replacement is recorded in the team ledger where the project has one,
so a quiet overwrite cannot happen.

The shim **fails closed**. If `git rev-parse --show-toplevel` cannot answer or
`scripts/teamwork.py` is absent, it prints a message naming the bypass and exits
non-zero rather than passing: a guard that cannot run must not look like a guard
that ran. `TEAMWORK_SKIP_HOOKS=1` is the documented escape.

The guard is **local only**. `git commit --no-verify` and `git push --no-verify`
skip these files, `core.hooksPath` can point the hooks somewhere else, and a clone
that never ran `hooks install` does not have them at all - so the forge-side rule
(branch protection / a ruleset on the default branch) remains the enforcement that
covers a hostile or careless clone. The hook is the cheap in-loop half of the same
rule, never the whole control.

| Hook | Rule | Override |
|---|---|---|
| `pre-commit` | R1 refuse a commit on the default branch, including the root commit on an unborn branch | `TEAMWORK_ALLOW_MAIN=1` |
| `pre-commit` | R2 refuse a staged file above 1 MiB that no `.gitattributes` LFS pattern covers | - |
| `pre-commit` | R3 a commit identity that is not a role mailbox warns on stderr and does not block | - |
| `pre-push` | P1 refuse a non-fast-forward update to the default branch | `TEAMWORK_ALLOW_FORCE=1` |
| `pre-push` | P2 refuse deleting the default branch | - |

`status` prints `installed`, `absent` or `foreign` per hook plus the literal
directory it probed; `uninstall` removes only hooks carrying the
`teamwork-managed hook` marker and never touches a foreign hook, and `install`
refuses to overwrite one without `--force`. The shim resolves the engine from the
git root and is a no-op when `scripts/teamwork.py` is absent, so a copied
repository cannot inherit a hook that fails.


## The rest of the reference

- [CLI reference](cli.md) - every command, grouped by job.
- [CLI: records and knowledge](cli-records.md) - learning, context, criteria and tests.
- [CLI: review and governance](cli-review.md) - review, archive, decisions, disputes, red lines, skills.
- [CLI: feature teams and git workflow (this page)](cli-workflow.md) - features, branches, PRs, commits, hooks.
- [CLI: audit and control](cli-audit.md) - ledger, trace, coordination, loop, model, scripts.
