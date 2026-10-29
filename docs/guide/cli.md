# CLI reference - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Installation](install.md) · [Quickstart](quickstart.md) · [Architecture](architecture.md) · [CI pipeline](ci.md)

Complete reference for the `teamwork` command-line interface. Every option below
was produced from `teamwork <cmd> --help`.

## Invocation

Three forms are equivalent:

```console
$ teamwork <command> ...            # console script (pip install)
$ python -m teamwork <command> ...  # module
$ python3 scripts/teamwork.py <command> ...   # checkout compatibility shim
```

## Global options

| Option | Meaning |
|---|---|
| `--project PROJECT` | Project directory (default: current directory). |
| `--team TEAM` | Team name (default: the project directory name). |
| `--version` | Print `teamwork <version>` and exit 0. |
| `-h`, `--help` | Show help for the command or subcommand. |

`--project` and `--team` are accepted by every subcommand so each command can
target a specific workspace.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `1` | Generic error, a role/independence refusal, or `loop` says CONTINUE. |
| `2` | Usage error and the gates that explicitly return 2 (e.g. `task set --status done` without evidence; `pr merge` on an unapproved PR). |
| `3` | Nothing to dispatch (`task next`, `pulse`). |
| `4` | Lock timeout. |

## Setup and workspace

### `init`

```text
teamwork init [--agents AGENTS] [--roster {slim,standard,full}] [--force] [--no-git]
```

Create the team workspace and memory files; creates the git repository unless
`--no-git`.

| Option | Meaning |
|---|---|
| `--roster` | Start from a tier: `slim` (default: ceo, architect, developer, tester, reviewer-1, reviewer-2), `standard` (adds product-manager, project-manager, release-engineer) or `full` (all 15 roles). |
| `--agents` | Comma-separated instance names, e.g. `ceo,architect,developer-1,tester-1`. Overrides `--roster`. |
| `--force` | Rewrite generated scaffolding; existing memory, task records and team documents are preserved. |
| `--no-git` | Do not create or check the git repository. |

A tier is a recipe, not a rule. Roles left out of the roster cost no charter, no
shared queue and no memory set, and their work is folded into an existing lane
rather than dropped: the test matrix only requires layers of staffed roles, and
the tribunal keeps a neutral seat (the Reviewer when no CTO/CFO is staffed) so no
party rules its own dispute. `init` prints the folded lanes and warns when
`ceo`, `developer`, `tester` or `reviewer` is missing.

### `repo`

```text
teamwork repo [--no-commit]
```

Ensure a git repository exists and report its status. `--no-commit` skips the
initial commit.

### `map`

```text
teamwork map
```

Print the workspace map and the detected repository layout.

### `agents-md`

```text
teamwork agents-md
```

Create or update the managed teamwork block in `<project>/AGENTS.md`.

### `clean`

```text
teamwork clean [--all] [--dry-run] [--limit LIMIT]
               [--worktrees] [--no-worktrees] [--stale-minutes N]
```

Remove scratch/temp files and reclaim stale worktrees; never touches tracked files.

| Option | Meaning |
|---|---|
| `--all` | Empty `Scratch/` entirely, not only temp patterns. |
| `--dry-run` | Show what would be removed. |
| `--limit` | Cap the number of files removed. |
| `--worktrees` | Reclaim merged, clean worktrees (the default; stated for clarity). |
| `--no-worktrees` | Leave every worktree alone, only sweep files. |
| `--stale-minutes` | Age before a merged, clean worktree is reclaimed (default 60). |

A worktree is reclaimed only when all of these hold: it resolves inside the
project's own `.pi/`, `git status --porcelain --ignored` is empty (a lane's build
cache counts as work), its HEAD is already an ancestor of the base branch, no
`doing`/`selfcheck` task or live slot lease names its lane, it is not
`git worktree lock`ed, and nothing in the tree was written within the stale
window. A removal that fails is reported as `could not be reclaimed`, never
counted as success.

### `agents`

```text
teamwork agents
```

List agent directories in the workspace, with each role's memory writer.

## Instances and the memory pen

Every role can run several instances. They share the role's one memory set and
one `TaskQueue.md`; only one of them revises that memory at a time.

### `instance`

```text
teamwork instance add ROLE [--count N] [--name NAME] [--new-role] [--by BY] [--json]
teamwork instance list [--json]
teamwork instance retire NAME --reason WHY [--by BY] [--force]
```

- `add` scaffolds `Agents/<Role>-N` against the existing `Roles/<Role>/`, so a
  fourth architect costs one directory, not a second memory. A role the team does
  not staff needs `--new-role`: it then gets the shared memory set and charter
  copy like any other.
- `list` prints role, instances, task count and the current memory writer.
- `retire` removes an idle instance's private directory and always keeps the
  role's memory and queue. An instance that still claims a `doing`/`selfcheck`/
  `review` task, holds a provider slot or holds the memory pen is refused until it
  is idle, or requires `--reason` plus `--force` so the record says what was
  abandoned.

### `memory`

```text
teamwork memory claim AGENT --by INSTANCE [--ttl MIN] [--reason WHY] [--force REASON]
teamwork memory renew AGENT --by INSTANCE [--ttl MIN]
teamwork memory release AGENT --by INSTANCE [--force REASON]
teamwork memory contest AGENT --by INSTANCE --reason WHY
teamwork memory extend AGENT --by ARBITER --ttl MIN --reason WHY
teamwork memory revoke AGENT --by ARBITER --reason WHY
teamwork memory status [AGENT] [--json]
```

The lease is `Runtime/Locks/memory-<Role>.claim`. `claim` holds the pen until
`release` or expiry, so a coherent multi-entry update lands whole; a single
`remember`, `forget`, `touch` or `consolidate` takes the lease implicitly for its
own duration and gives it back. While a peer holds an explicit lease every other
instance of that role is read-only: `load`, `recall` and `board` keep working, and
a mutating command exits `2` naming the holder and the minutes left. An expired
lease frees the role; a stalled holder is taken over with `--force "<why>"`,
recorded as `memory.claim.force` in the ledger. Only that role's own instances -
or the CEO - may write its memory.

**A lease that runs long goes to the CTO.** `memory status` marks a lease held
longer than `MemoryStallMinutes` (default 15) as `SLOW`. Any *other* instance of
the role then runs `memory contest <role> --by <you> --reason "<why>"`: that
records the contest on the lease (`memory.contest`), files one `P0`
`memory-lease` task on the arbiter's queue, and names who rules. The **CTO** rules,
because a stuck writer is an engineering question and the CTO owns the build and
lock policy:

| Ruling | Command | Effect |
|---|---|---|
| more time is fair | `memory extend <role> --by CTO --ttl 45 --reason "<why>"` | the holder keeps the pen for another N minutes, contests answered (`memory.grant`) |
| the pen is removed | `memory revoke <role> --by CTO --reason "<why>"` | the lease is cleared and the role is free at once (`memory.revoke`) |

Only the arbiter or the CEO may rule; a peer cannot extend or remove another
instance's lease and exits `2`. On a roster without a CTO the request folds up to
the CEO and the command says which seat was folded. A party never rules its own
lease: a CTO's memory goes to the CEO, and when the holder is the top of the chain
too the peers are told to open a dispute instead. A holder cannot contest itself -
it releases the pen or finishes the update.

## Tasks, board and scheduling

### `task`

```text
teamwork task {add,list,next,set,check,reclaim,rm} ...
```

Manage a role's shared priority queue.

#### `task add`

```text
teamwork task add AGENT TITLE [--priority {P0,P1,P2,P3}]
    [--status {todo,doing,blocked}] [--deps DEPS] [--shared SHARED]
    [--review-profile {fast,standard,deep}]
    [--tags TAGS] [--body BODY] [--bug] [--evidence EVIDENCE]
    [--claimed-by CLAIMED_BY] [--no-review]
```

| Option | Meaning |
|---|---|
| `--deps` | Comma list of dependencies; cross-role as `role:T-0001`. Add `@review` to release once the task is submitted for review, or `@started` once its owner has picked it up, so a downstream lane can start against a frozen interface. |
| `--shared` | Shared board / issue / PR reference. |
| `--review-profile` | Override the profile inferred from the branch diff: `fast` (prose-only), `standard` (code), `deep` (security/release/data/workflow). |
| `--body` | Acceptance criteria / notes. |
| `--claimed-by` | Assign to a specific instance (default: role pool). |
| `--bug` | A defect fix: its self-check is refused until a `tests repro` record proves the defect. |
| `--no-review` | Mark a chore that does not need Reviewer sign-off. |

New tasks cannot start as `review` or `done`; the gates own those states.

#### `task list`

```text
teamwork task list [AGENT] [--all] [--status {todo,doing,selfcheck,review,blocked,done,dropped}]
```

List tasks, priority ordered.

#### `task next`

```text
teamwork task next AGENT [--peek] [--capacity N]
```

Atomically claim the highest-priority executable task of the role. `--peek` does
not claim it.

| Option | Meaning |
|---|---|
| `--peek` | Show what would be claimed, and claim nothing (the output lists every ready task as `ALSO READY`). |
| `--capacity N` | Claim up to `N` executable tasks at once, for a lane that works in parallel; one `task.claim` record is written per claimed task, so `trace` shows each claim. `0` or a negative value is treated as `1`, never as "take nothing". Default `1`. |

A lane that fills its capacity holds `LANE_WIP` (2) deliverables at once: one in
review plus the next in progress. `pulse` uses the same arithmetic to fill each
lane to its limit instead of handing work only to idle lanes; a Reviewer lane
takes one deliverable at a time.

#### `task set`

```text
teamwork task set AGENT HANDLE [--claimed-by CLAIMED_BY]
    [--status {todo,doing,selfcheck,review,blocked,done,dropped}]
    [--priority {P0,P1,P2,P3}] [--deps DEPS] [--title TITLE]
    [--evidence EVIDENCE] [--force REASON]
```

Update status, priority or dependencies. `--force` overrides evidence/self-check
/review gates, requires a reason, and is recorded and audited.

#### `task check`

```text
teamwork task check
```

Verify the whole task graph the queues describe: every dependency resolves to an
existing task, no task depends on itself, no dependency cycle exists (the path is
printed), no queue holds one open id twice, and every task has a priority. Exit
`2` lists every problem; `0` prints `0 problems in N role queue(s)`.

The same check runs on write: `task add` and `task set --deps` refuse with exit
`2` instead of writing a queue that cannot run, because `task next` would only
report the lane as idle.

#### `task reclaim`

```text
teamwork task reclaim AGENT HANDLE --as BY --reason REASON [--force REASON]
```

Take back a task whose owner went silent. It refuses while the owner still holds
a live slot (a working lane is not a silent one); `--force` with a reason takes
over a confirmed dead lane and is recorded.

#### `task rm`

```text
teamwork task rm AGENT HANDLE --by BY [--force REASON]
```

Remove a task (own role only).

### `board`

```text
teamwork board
```

Cross-agent board with counts and each role's next task.

### `parallel`

```text
teamwork parallel
```

Show free concurrency slots, ready work, and how many lanes to start.

### `pulse`

```text
teamwork pulse [--commit] [--interval INTERVAL]
```

CEO wake-up: print idle lanes, ready work and a dispatch plan. `--commit` applies
the assignments now. `--interval` stores the pulse interval in minutes. Exit code
`3` means nothing to dispatch.

### `slot`

```text
teamwork slot {acquire,release,list,renew,reap} ...
```

Reserve/release provider concurrency slots (respect the caps in
`Settings.json`).

#### `slot acquire`

```text
teamwork slot acquire --agent AGENT [--provider PROVIDER] [--task TASK] [--wait WAIT]
```

Take a slot; `--wait` seconds waits for a free one.

#### `slot release`

```text
teamwork slot release --agent AGENT [--provider PROVIDER] [--by BY] [--force REASON]
```

Give a slot back.

#### `slot list`

```text
teamwork slot list [--provider PROVIDER]
```

Show slots per provider.

#### `slot renew`

```text
teamwork slot renew --agent AGENT [--provider PROVIDER]
```

Extend the lease while still working.

#### `slot reap`

```text
teamwork slot reap [--provider PROVIDER]
```

Drop dead or stale slots.

## Memory

### `load`

```text
teamwork load AGENT [--limit LIMIT]
```

Print the ROLE's short-term memory (startup context).

### `remember`

```text
teamwork remember AGENT TEXT [--by BY] [--src SRC] [--rev REV]
    [--layer {short,long}] [--key KEY] [--importance IMPORTANCE]
    [--tags TAGS] [--pin]
```

Add or update an entry in the ROLE's shared memory. It takes the role's memory
pen for the duration of the write (and the consolidation that follows it), so a
peer's concurrent write waits its turn instead of interleaving; `--by` should name
the instance, because that is who the implicit lease names.

### `global`

```text
teamwork global TEXT [--by BY] [--src SRC] [--rev REV]
    [--key KEY] [--importance IMPORTANCE] [--tags TAGS] [--pin]
```

Add or update an entry in global shared memory (CEO-owned).

`--by` names who recorded the entry, `--src` what it comes from (a task, a
document, a run) and `--rev` the revision it was verified at. The audit gate
reports a memory entry without a `by` as a blocker, so a global entry is
recorded with its provenance the same way a role entry is.

A merge never overwrites provenance that is already there. The three fields
describe one recording act and travel together: an entry recorded without an
author is completed by a later writer, an entry that already has an author
keeps it, and a later writer who is not the author can neither take over the
entry nor graft their own `src` and `rev` onto it.

### `recall`

```text
teamwork recall [QUERY] [--agent AGENT] [--all] [--global]
    [--layer {both,short,long}]
```

Search memory.

### `touch`

```text
teamwork touch AGENT HANDLE [--layer {short,long}] [--by INSTANCE]
```

Mark an entry as used; `HANDLE` is an `M-0003` id, a key, or a substring.

### `forget`

```text
teamwork forget AGENT HANDLE [--layer {short,long}] [--by INSTANCE]
```

Delete an entry.

### `consolidate`

```text
teamwork consolidate [--agent AGENT] [--all] [--dry-run] [--by INSTANCE]
```

Promote stale short-term entries and evict long-term overflow. It needs the role's
memory pen like any other write; `load` runs it opportunistically and skips it
silently while a peer holds the pen.

### `stats`

```text
teamwork stats [--agent AGENT] [--all]
```

Show memory sizes and cap violations.

## Criteria and tests

### `criteria`

```text
teamwork criteria {add,verify,reopen,rm,list} ...
```

Acceptance criteria as records; they are the STOP condition.

#### `criteria add`

```text
teamwork criteria add --id ID --text TEXT --owner OWNER --by BY
```

Record a verifiable statement (`AC-1`, `AC-login`, ...) and who records it.

#### `criteria verify`

```text
teamwork criteria verify ID --by BY [--evidence EVIDENCE] [--test TEST] [--rev REV]
```

Mark verified with independent evidence. `--by` must not be the owner.

#### `criteria reopen`

```text
teamwork criteria reopen ID --by BY [--reason REASON]
```

Clear a verification.

#### `criteria rm`

```text
teamwork criteria rm ID --by BY [--force REASON]
```

Remove a criterion (CEO only).

#### `criteria list`

```text
teamwork criteria list
```

Show criteria and status.

### `tests`

```text
teamwork tests {add,run,repro,require,rm,plan,list} ...
```

Layered tests, each owned and run by its own role.

#### `tests add`

```text
teamwork tests add --layer LAYER [--area AREA] [--owner OWNER]
    [--task TASK] [--command COMMAND] [--no-owner-check] [--force REASON]
```

`--layer` is one of `goal,requirements,plan,tech,release,data,process,cost,system,ui,docs,unit,integration,acceptance,security`.

#### `tests run`

```text
teamwork tests run ID --by BY --result {pass,fail} --evidence EVIDENCE
    [--rev REV] [--command COMMAND] [--baseline BASELINE]
    [--artifact PATH]... [--replay REPLAY] [--force REASON]
```

Record a layer run as an evidence packet. `--artifact` names a file inside the
project that proves the result; it is hashed (`path:sha256:bytes`) and the digest
is appended to the ledger. `--baseline` is the state before the run and
`--replay` is the command another agent can rerun.

#### `tests repro`

```text
teamwork tests repro TASK --by BY --pre-rev REV --pre-evidence EVIDENCE
    --post-rev REV --post-evidence EVIDENCE [--role ROLE] [--artifact PATH]...
    [--force REASON]
```

Prove a defect before fixing it. `TASK` is the defect's `T-id` (`task add --bug`),
searched on every role queue (task ids are per queue, so an id that exists on
several queues is refused until `--role` names the owner); the proof is stored on
that task (`repro`,
`repro_artifacts`, `repro_by`), not on a layer record, so it cannot leak to a
sibling bug. The failing run at `--pre-rev` must contain `fail`/`FAIL`, the
passing run at `--post-rev` must contain `pass`/`PASS`, and in a git workspace
the pre-revision must be an ancestor of the post-revision. A `--bug` task cannot
pass its self-check until this record exists, and `audit` reports a closed bug
task without one.

#### `tests require`

```text
teamwork tests require --area AREA --layers LAYERS --by BY
    [--reason REASON] [--force REASON]
```

Declare which layers an area must cover.

#### `tests rm`

```text
teamwork tests rm ID --by BY [--force REASON]
```

Remove a test record.

#### `tests plan`

```text
teamwork tests plan
```

Coverage matrix, role coverage and gaps.

#### `tests list`

```text
teamwork tests list [--layer LAYER]
```

List test records.

## Review and archive

### `review`

```text
teamwork review [AGENT] [HANDLE] [--queue] [--full] [--packet]
    [--claim] [--release] [--renew] [--by BY]
    [--result {pass,fail}] [--evidence EVIDENCE] [--artifact PATH]...
    [--baseline BASELINE] [--replay REPLAY] [--findings FINDINGS]
    [--keep-branch] [--no-merge] [--force REASON]
```

Reviewer: independent second review of a deliverable. `--queue` lists everything
awaiting review. **A pass merges the PR at once** and closes its branch: the
Reviewer that verified the revision runs the merge itself, so a passing review
never waits in a second queue. `--keep-branch` keeps the branch; `--no-merge`
lands only the verdict and leaves the merge to `pr merge`. A fail returns the
task to its owner. `--artifact` binds a verification artifact (hashed into the
ledger) to the verdict; `--baseline` and `--replay` record where the
verification started and how to rerun it. `--force` overrides the review gates
and requires a recorded reason.

Several Reviewers may run at once, so a lane announces what it took:
`review --next --by <reviewer>` claims the highest-priority unclaimed deliverable
and prints its packet in one atomic step, and
`review <role> <T-id> --claim --by <reviewer>` pins a specific one. A claim is a
work lease scaled to its profile - base `ReviewLeaseMinutes` /
`TEAMWORK_REVIEW_LEASE_MINUTES` (20 min) ×1 for a prose diff, ×2 standard, ×4 deep,
capped by `ReviewLeaseMaxMinutes` - so a deep review is not taken over mid-flight
while a prose one frees its item quickly. `--renew` extends it, and `--release`
hands an unfinished one back. `review --next` claims the highest-priority unclaimed
deliverable and prints its packet in one step; it exits `3` when the queue is empty.
A lease nobody renews expires and the next lane takes it over; `--force <reason>` releases another lane's live claim, which is the
case where that lane is dead. The claim, renew and release modes take no
`--result` - the verdict is a separate call.

`--packet` prints what a Reviewer needs before claiming: the inferred profile
(`fast` prose-only, `standard` code, `deep` security/release/data/workflow), the
changed files and diffstat, the author's self-check, the gate set for that profile
and the ordered checklist. `--queue --packet` prints a packet per item. The queue
lists only work the author has submitted - a `todo` has no frozen diff - and is
sorted by priority then age; it prints the lane capacity, the per-profile lease and
the number of expired claims, so the CEO can see when to staff another Reviewer
lane.

Independence is about the **author**, not about a second Reviewer: the author
never reviews or merges its own work, and a Reviewer who co-authored a
deliverable cannot review it. A pass that cannot merge (a conflict, a dirty
tree) keeps the verdict and prints the exact `pr merge` to finish - the work is
then not in the base branch yet, and the message says so.
`--queue` clips each evidence and findings line at 600 characters and marks what it
omitted (`... (+N chars: --full)`); `--full` prints them whole - the stored records
always keep the full text.

### `selfcheck`

```text
teamwork selfcheck AGENT HANDLE [--by BY] [--result {pass,fail}]
    [--note NOTE] [--test TEST] [--baseline BASELINE] [--artifact PATH]...
    [--replay REPLAY] [--force REASON]
```

Author's own review and test before submitting for review. A passing self-check
requires a `--test` line; `--note` records what was re-read, and
`--baseline/--artifact/--replay` attach the rest of the evidence packet. A
`--bug` task is refused until a `tests repro` record exists for it.

### `archive`

```text
teamwork archive [--agent AGENT] [--full]
```

Show the reviewed-result archive (the team's evidence ledger). The
`self-check`/`author evidence`/`reviewer evidence`/`findings history` lines are
clipped at 600 characters with an `... (+N chars: --full)` marker; `--full`
prints them whole. `docs/Team/Archive.md` itself always stores the full text, and
`pr merge` rewrites only the `branch / merge` line of the matching entry so it
records the real merge revision instead of `pending` - as a committed
`chore(records)` change on the base branch, not as an uncommitted edit. The
entry is written where the task's base branch is checked out, so the base
carries it; a base branch that has no entry yet gets one from `pr merge` before
the merge commit is made.

## Decisions, disputes and governance

### `decision`

```text
teamwork decision {add,list} ...
```

#### `decision add`

```text
teamwork decision add --by BY [--kind KIND] [--title TITLE] --decision DECISION
    [--why WHY] [--evidence EVIDENCE] [--context CONTEXT] [--options OPTIONS]
    [--falsify FALSIFY] [--consequences CONSEQUENCES] [--task TASK] [--rev REV]
    [--status {proposed,accepted,superseded,rejected}] [--force REASON]
```

`--kind` is one of `technical,governance,redline,tribunal,scope,cost,process`.
A decision without evidence is refused.

#### `decision list`

```text
teamwork decision list [--kind KIND]
```

List recorded decisions.

### `dispute`

```text
teamwork dispute {open,round,escalate,sign,resolve,list} ...
```

Challenge a design or decision with counter-evidence.

#### `dispute open`

```text
teamwork dispute open --by BY --against AGAINST --topic TOPIC
    [--evidence EVIDENCE] [--position POSITION] [--task TASK]
```

#### `dispute round`

```text
teamwork dispute round ID --by BY --message MESSAGE
```

Add a rebuttal round (capped at three, then the tribunal).

#### `dispute escalate`

```text
teamwork dispute escalate ID --by BY
```

Send an unresolved dispute to CEO + CTO + CFO.

#### `dispute sign`

```text
teamwork dispute sign ID --by BY
```

A tribunal member signs the ruling.

#### `dispute resolve`

```text
teamwork dispute resolve ID --by BY --decision DECISION [--force REASON]
```

Record the binding ruling.

#### `dispute list`

```text
teamwork dispute list [--open]
```

### `redline`

```text
teamwork redline {record,close} ...
```

#### `redline record`

```text
teamwork redline record --by BY --action ACTION --why WHY
    [--alternative ALTERNATIVE] [--authorized AUTHORIZED]
```

Record a refused red-line action. Never crossed silently.

#### `redline close`

```text
teamwork redline close ID --by BY [--reason REASON] [--force REASON]
```

Close a resolved red line.

### `skill`

```text
teamwork skill {create,share,candidates,rm,list} ...
```

Team skills: extract repeated flows into `<project>/.agents/skills/<name>/SKILL.md`.

#### `skill create`

```text
teamwork skill create --name NAME [--role ROLE] --for DESCRIPTION --by BY
    [--body BODY] [--body-file BODY_FILE] [--force] [--allow-main]
```

#### `skill share`

```text
teamwork skill share NAME --by BY [--to TO]
```

Notify same-role peers so they reuse it. `--to` is a comma list of roles,
defaulting to the owner role.

#### `skill candidates`

```text
teamwork skill candidates [--min-tasks MIN_TASKS]
```

Find flows worth extracting.

#### `skill rm`

```text
teamwork skill rm NAME --by BY
```

#### `skill list`

```text
teamwork skill list
```

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
creates - a `users.noreply.github.com` committer - but only when the **author**
of that commit is a role mailbox. The host stamp is transport, not identity; the
author still has to be the team. So the guard does read an author fact: a
host-stamped commit with a personal author fails. Measured on a commit authored
by `jane@example.com` and committed by `123456+jane@users.noreply.github.com`,
`guard_committer_identity()` exits 1 with `- 0851b9bd6493 FAIL committer
123456+jane <123456+jane@users.noreply.github.com> (author Jane Doe
<jane@example.com>)`. The full author check is `--audit`, which CI runs on every
pull request and every push to `main`.

### `harness`

```text
teamwork harness list
teamwork harness lint [--verbose]
teamwork harness budget [--limit KB]
```

The harness is everything around the model: the always-on prompt and rules, the
memory, the tool guidance, the skills, the scripts and the in-loop hooks. This
group names that surface, validates it, and prices it.

| Subcommand | What it does |
|---|---|
| `list` | eight rows, one per component (C1..C8), each with its activation class, the bytes it costs and the role that owns it. `always-on` is paid on every run, `on-demand` only when invoked, `in-loop` is enforced rather than instructed. C5 (subagents) is a lane packet, not a file, so its class and bytes are `-`. |
| `lint` | the whole-proposal checks, before anything is probed: `IDENTITY` (frontmatter `name:` equals the directory, `description:` non-empty), `TRIGGER` (the skill is named in an always-on surface - an unnamed skill is dead text nobody is told to load), `SUBCOMMAND` (every `teamwork.py <verb>` in a skill exists in the CLI), `HELPER` (every repo-relative path a skill references is shipped), `EVIDENCE` (a registered `shared` skill carries a verdict row). Exit 1 with one `- PROBLEM <RULE> <path>: <detail>` line per finding. `--verbose` also prints one `# checked: <file> -> <RULE> verdict` line per file read. |
| `budget` | always-on bytes per instance - `AGENTS.md` block + `SKILL.md` + the role charter + that role's memory - against `AlwaysOnBudgetKb` in `Settings.json` (default 120 KiB, `--limit` overrides). Exit 1 when any instance is `OVER`: always-on prose is the expensive option, so the cap is what makes "cut something to pay for it" a rule rather than an intention. |

`list` and `lint` work from any checkout; `budget` needs the team workspace
because it measures it. A hook installed by `hooks install` is measured through
`git rev-parse --git-path hooks`, so a linked worktree reports the hook that is
actually running rather than a zero from a path that does not exist.

### `hooks`

```text
teamwork hooks install [--force]
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

## Audit and control

### `ledger`

```text
teamwork ledger {show,verify,repair,export} ...
```

The append-only, hash-chained audit trail.

#### `ledger show`

```text
teamwork ledger show [--tail TAIL] [--action ACTION] [--actor ACTOR] [--target TARGET]
```

Inspect the trail.

#### `ledger verify`

```text
teamwork ledger verify [--reconcile]
```

Recompute the hash chain. `--reconcile` repairs a head cache left by a crash.

#### `ledger repair`

```text
teamwork ledger repair --by BY --reason REASON [--force REASON]
```

Drop a torn tail and record the repair.

#### `ledger export`

```text
teamwork ledger export [--dry-run] [--by BY]
```

Write an externally verifiable audit manifest (`docs/Team/AuditManifest.json`).

### `trace`

```text
teamwork trace HANDLE [--full]
```

Follow one task, criterion, test or PR through every record. Free-text evidence
(evidence, findings, review notes, dispute rounds, rulings) is clipped at 600
characters with an `... (+N chars: --full)` marker; `--full` prints it whole.

### `coordination`

```text
teamwork coordination [--strict] [--json] [--commit]
```

Coordination health from the records the team already writes: duplicate
branches/tasks/shared references, verification lanes on one model, review
evidence copied from the author, reviewer monoculture, abandoned PRs, merge
fraction, and slot starvation. Stale open PRs remain `audit`'s check. The default
report is diagnostic; `--strict` exits `1` while a high-severity finding is open
and is the milestone gate; `--commit` appends the result to the ledger; `--json`
is machine-readable. Mechanisms and the failure each check addresses:
`references/Coordination.md`.

### `links`

```text
teamwork links [--no-reciprocity]
```

Check markdown cross-links, external URLs and back-links. `--no-reciprocity`
skips the bidirectional back-link requirement. Exit code `1` when issues exist.

### `audit`

```text
teamwork audit [--stale-days STALE_DAYS]
```

Find fabricated completions, stale work, duplicates, LFS problems and link
health.

### `code-scanning`

```text
teamwork code-scanning [--commit] [--limit N] [--full]
```

Read the forge's open code-scanning alerts and route each one to the role that
owns the file. The Release Engineer owns this gate: an `error`, `critical` or
`high` alert on the default branch is a known defect in the revision that ships.
Without `--commit` it only prints the plan
(`<number> [<severity>] <rule> <path>:<line> -> <role>`); with it, one `P0` task
per (owner, rule, file) is filed in that role's queue, carrying the alert
numbers and the `gh api` command as evidence. Re-running is safe: a title
already in the queue is not duplicated.

Exit codes:

| Code | Meaning |
|---|---|
| `0` | the alerts were read and none blocks the release |
| `1` | a blocking alert is open - with or without `--commit`, filing a fix does not close the gate |
| `2` | the alerts could not be read: no origin, no `gh`, no auth, no scanner, non-JSON output |

Routing follows file ownership (`SCAN_ROUTE` in `src/teamwork/config.py`):
`scripts/privacy_scan.py` and `docs/Team/AuditReport.md` to the Security
Auditor, `src/**`, `scripts/**` and `tests/**` to the Developer, `.github/**`
and `docs/Team/Release.md` to the Release Engineer, `docs/Team/Architecture.md`
to the Architect, `docs/**` to the Technical Writer, `roles/**`,
`references/**` and `templates/**` to the CEO, `README.md` and `assets/**` to the
Designer. An alert with no file, or a file no pattern covers, goes to the
Release Engineer.

Exit `2` is the honest degraded mode: a host that is not a forge, has no `gh`,
is unauthenticated, or has code scanning disabled prints
`- cannot verify: unreadable: ...` and never `no open alert`, because nothing was
verified. Fixing the code is the normal close; dismissing an alert is a Security
Auditor triage with a recorded reason, never a silent one.

### `loop`

```text
teamwork loop [--full]
```

Stop-condition check: may the team stop? Prints `STOP` or `CONTINUE` with
reasons. Detail past 220 characters is clipped by default; `--full` prints every
line whole.

### `refresh`

```text
teamwork refresh [--dest DIR] [--host HOST] [--source DIR] [--repo URL]
                 [--remote origin] [--branch main] [--mirror]
                 [--no-fetch] [--check] [--dry-run] [--quiet]
```

Keep the **installed** skill equal to the remote. The host loads the copy in its
skills directory, not the checkout, so updating one without the other leaves the
agent reading stale text - measured once on this machine as an old `SKILL.md`
plus 8 engine modules that were simply missing.

1. Resolve the source: `--source`, else `$TEAMWORK_SOURCE`, else the bundle in
   use when it is a git checkout, else the tool-managed mirror checkout
   `.teamwork-source` (`--mirror` forces that case). The mirror sits beside the
   skills directory, one level higher when that directory is literally named
   `skills`. The destination is resolved from the host's skills directory -
   `--dest` names one directly, `--host` selects a host's default - so
   `~/.pi/agent/skills/teamwork` mirrors through
   `~/.pi/agent/.teamwork-source`, and `--host agents` uses
   `~/.agents/.teamwork-source`.
2. In a checkout: fetch `--remote/--branch` and fast-forward. A dirty tree is
   never clobbered - the checkout is mirrored as it stands and the command says
   "fast-forward skipped".
3. Mirror into `--dest` (default the host's skills directory). Files the source
   no longer ships are deleted, files outside the bundle trees are never touched,
   and a stale `__pycache__` is removed.
4. Print the reminder to reload the host when anything was written.

`--check` reports drift and exits `1` without writing; `--dry-run` prints the
file plan; `--no-fetch` mirrors the local checkout only (`--repo` is required
just once, to create the mirror). `scripts/sync_skill.py` and `make sync-skill` /
`make sync-check` are the same mirror for a checkout that has no `teamwork` on
`PATH`.

### `version`

```text
teamwork version
```

Print the version and exit (same as `--version`).

### `selftest`

```text
teamwork selftest
```

Offline smoke test of the install; no network, no workspace required.

### `model` - per-agent configuration and automatic routing

```text
teamwork model set <role|instance> --provider P --model M
teamwork model get <role|instance>
teamwork model list
teamwork model auto [--apply] [--json]
```

The skill ships no model and calls no LLM API: every agent runs through the host's
own API, so the model is a property of the **agent**, not of the project.

- `set` writes a role default, or an instance override when the name carries an
  instance suffix (`developer-1`). The instance wins over the role.
- `get` prints the effective model and where it came from (`agent`, `role` or
  `unset`); `list` prints the whole roster.
- `auto` reads the **runtime environment** - the running agent host and the model
  it exposes - and routes the strongest available model to the decision lanes
  (Reviewer, Architect,
  Security Auditor, CEO, CTO) and the economy model to the mechanical lanes
  (developers, testers, writers, formatting, link checks). It is a dry run by
  default; `--apply` writes it and records `model.auto` in the ledger. It never
  invents a model id: a lane with nothing available is reported `unset` together
  with the variable to set (`TEAMWORK_MODEL_STRONG`, `TEAMWORK_MODEL_ECONOMY`).
  `TEAMWORK_AGENT_HOST` pins host detection when the markers are ambiguous.

Automatic routing policy: [references/Concurrency.md](https://github.com/Nidvue/Teamwork/blob/main/references/Concurrency.md).

### `imaging probe`

```text
teamwork imaging probe [--json]
```

The Designer's capability probe for **generated raster assets**. It is offline by
design: it reads environment variables and `PATH` only, never the network, so it
cannot leak a prompt or hang.

Resolution order: `TEAMWORK_IMAGE_MODEL` (explicit override) ->
`TEAMWORK_IMAGE_PROVIDER` -> the first ambient provider with a ranked image
model, in the order openai, google, black-forest-labs, stability, replicate,
local, ollama-cloud. "Best quality" is the first generally available model of the
detected provider, ranked in `teamwork.engine.IMAGE_MODEL_RANKING`.

When no model is detected it prints the fallback ladder instead of failing:
local model, then a hand-authored SVG. The full process - plan one prompt per
asset in `docs/Team/Design.md`, generate at least four candidates off one seed
base, review every candidate visually, improve the winner until it passes,
integrate, record evidence - plus the privacy and licence red lines, is the
Designer's own policy in
[`roles/designer.md`](https://github.com/Nidvue/Teamwork/blob/main/roles/designer.md).

## Auxiliary scripts

### `scripts/privacy_scan.py`

```text
python3 scripts/privacy_scan.py [--tree] [--staged] [--history] [--all]
                                [--allow FILE] [--root DIR] [--json]
                                [--reveal] [--reveal-to PATH] [--quiet]
```

The privacy gate. It fails (exit `1`) on personal data, credentials, private
domains, absolute home paths and agent-host configuration in the tracked tree,
the index and the full git history. `--tree`, `--staged` and `--history` combine;
`--all` sets all three; the default is `--tree`. Exit `2` is a usage or git
error. CI runs `--tree --history --allow .github/privacy-allow.txt`.

**No character of a matched value reaches stdout or stderr.** There is
deliberately no flag that sends a secret to a log: a log line survives the session
(CI logs are retained and world-readable, terminals are recorded, `tee` output
outlives the shell), and a partly masked preview such as `ev***et` already hands
the first and last characters of a credential to every reader of that log.

Plain output therefore names the rule, not the value -
`src/mod.py:12: [critical/api-token] <redacted-api-token>` - which says what fired
and where. The value itself is held outside the report record, so no reporting
sink (the text line, `--json`, a CI annotation) can serialise it by accident.

| Option | Meaning |
|---|---|
| `--reveal` | append a stable fingerprint to each finding line - `sha256:` plus 12 hex characters of the unsalted SHA-256 of the full value. Use it to tell two findings apart or to confirm that a rotated secret really is gone. It is not usable as the credential and does not embed any prefix of it |
| `--reveal-to PATH` | write the raw matched values to a file you name, for local remediation only. The file is created `0600` and **refuses to overwrite** an existing path (exit `2`); each line is `location<TAB>rule<TAB>fingerprint<TAB>value`; a `WARNING` naming the file is printed to stderr; a partial file is deleted on error |
| `--json` | machine-readable report. It carries the same rule-named evidence; the raw value is not an item of any finding, so it is not in the JSON either |
| `--quiet` | only the one-line `PASS`/`FAIL` summary |
| `--allow FILE` | allowlist, one regular expression per line with an optional `# reason` |

Remediation workflow: run with `--reveal` to locate and identify, then
`--reveal-to /a/path/only/you/can/read` to recover the exact strings, rotate the
credential, delete the file, and rewrite history if it was committed. Never pass
`--reveal-to` in CI, never commit the output, and never paste it into a ticket or
a chat - the file is plaintext by construction.
