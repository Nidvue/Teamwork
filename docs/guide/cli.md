# CLI reference - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Installation](install.md) · [Quickstart](quickstart.md) · [For agents](for-agents.md) · [Usage patterns](usage.md) · [Operations](operations.md) · [How it works](how-it-works.md) · [Features](features.md) · [Architecture](architecture.md) · [CI pipeline](ci.md) · [CLI: records and knowledge](cli-records.md) · [CLI: review and governance](cli-review.md) · [CLI: feature teams and git workflow](cli-workflow.md) · [CLI: audit and control](cli-audit.md)

Complete reference for the `teamwork` command-line interface, in five pages.
Every option was produced from `teamwork <cmd> --help`.

| Page | Covers |
|---|---|
| [CLI reference](cli.md) | every command, grouped by job |
| [CLI: records and knowledge](cli-records.md) | learning, context, criteria and tests |
| [CLI: review and governance](cli-review.md) | review, archive, decisions, disputes, red lines, skills |
| [CLI: feature teams and git workflow](cli-workflow.md) | features, branches, PRs, commits, hooks |
| [CLI: audit and control](cli-audit.md) | ledger, trace, coordination, loop, model, scripts |

This page carries invocation, global options, exit codes and the commands that
set up a workspace, scale roles, run the queue and edit memory - plus the
coordination surface (the agent mailbox and attention items) and the live-state
feed.

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
teamwork clean [--agent AGENT | --team-wide] [--all] [--dry-run]
               [--limit LIMIT] [--worktrees] [--no-worktrees]
               [--stale-minutes N]
```

Remove scratch/temp files and reclaim stale worktrees; never touches tracked files.
One lane is in scope: the lane worktree you run from, or the one `--agent` names.
From the base checkout no lane owns the tree, so a run that names neither refuses
with exit 2 and removes nothing; `--agent` with `--team-wide` is refused the same
way.

| Option | Meaning |
|---|---|
| `--agent` | Clean only this lane's Scratch (default: the lane worktree you run from). |
| `--team-wide` | Clean every lane's Scratch plus `Global/` and `Roles/`, printing each location before removal; a stray file sitting directly in `Agents/` belongs to no lane and is left alone. |
| `--all` | Empty the Scratch/ in scope entirely, not only temp patterns; a team-wide run still only removes temp files from `Global/` and `Roles/`. |
| `--dry-run` | Show what would be removed. |
| `--limit` | Cap the number of paths printed (default 40); removal is not capped. |
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
teamwork instance add ROLE [--count N] [--name NAME] [--new-role]
                       [--under TEAM_LEADER] [--by BY] [--json]
teamwork instance list [--json]
teamwork instance retire NAME [--reason WHY] [--by BY] [--force]
teamwork instance prune [--by BY] [--reason WHY] [--dry-run] [--keep-required]
```

- `add` scaffolds `Agents/<Role>-N` against the existing `Roles/<Role>/`, so a
  fourth architect costs one directory, not a second memory. A role the team does
  not staff needs `--new-role`: it then gets the shared memory set and charter
  copy like any other.
- `--under TEAM_LEADER` attaches a squad specialist (`developer`, `tester`,
  `designer`, `data-engineer`, `technical-writer`) to the team leader it works
  for. The attachment is **one private file**, `Agents/<Instance>/Team.md`: it is
  a fact about that instance and never a reporting line, so `ROLE_PARENT` does not
  change and a specialist has exactly one manager at a time. What it does change
  is the team a leader visibly leads: `map` prints the leader's `F-nnnn` and the
  instances under it, and a squad member escalates to that leader, who escalates
  to the CTO. It is refused
  (`2`) for a target that is not a team-leader instance, for a team-leader (a
  leader's only manager is the CTO - more teams is `instance add team-leader`
  with no `--under`), for the shared services and the independent lanes
  (`architect`, `project-manager`, `release-engineer`, `reviewer`, `ceo`, `cto`,
  `coo`, `cfo`, and `security-auditor`, which audits the lane above and the team
  it would be attached to and is never attached), and for a name that already
  exists - moving a specialist is `instance retire` then `instance add --under`,
  so no command can write a second `under:` line.
- `list` prints role, instances, task count and the current memory writer, with
  each instance's manager: `(under:<TeamLeader>)` when it is attached to a team,
  `(reports:<CTO|CEO|User>)` on the line `ROLE_PARENT` gives its role.
- `retire` **moves** an idle instance's private directory to
  `Runtime/Retired/<Instance>/` and always keeps the role's memory and queue. Its
  `Artifacts/`, `Reports/` and `WorkLog.md` are evidence and are never deleted; a
  second retirement of the same name gets a timestamped sibling. An instance that
  still claims a `doing`/`selfcheck`/`review` task, holds a provider slot or holds
  the memory pen is refused until it is idle, or requires `--reason` plus
  `--force` so the record says what was abandoned. Before a cut, verify
  `git rev-parse HEAD` is at or after the move-only revision (`b9e5135`): the
  first cut ran from a stale checkout and lost 102 artifact paths (`L-0001`).
  `parallel` says how many lanes the ready work supports; `list` is the roster.
- `prune` folds **every idle instance** in one pass: a lane is idle only when it
  claims no `doing`/`selfcheck`/`review` task, holds no provider slot, no memory
  pen, no review claim and no live lane record, and its role has no ready work.
  Each fold is the same move-only retirement (`Runtime/Retired/<Instance>/`, role
  memory and queue stay) with its own ledger record, so nothing is lost and a
  second `prune` is a no-op. The **CEO is never folded** - it is the only voice to
  the user. `--keep-required` also keeps one instance of each gate-critical role
  (`ceo`, `developer`, `tester`, `reviewer`) so an automatic fold cannot strand a
  gate; without it the team drains to the CEO and `instance add <role>` restaffs
  on demand. `--dry-run` prints the plan and moves nothing. `pulse --commit` runs
  the same fold for the **surplus** seats (keeping the gate roles), so a wake-up
  that finds nothing to dispatch does not leave a dozen idle agents behind.

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

#### `memory pack`, `search`, `verify`, `dream`

```text
teamwork memory pack [--role ROLE] --task T-ID|TEXT [--budget BUDGET]
teamwork memory search [--role ROLE] QUERY
teamwork memory verify [--role ROLE] [--focus TEXT|T-ID] [--limit N] [--json] [--apply] [--by BY]
teamwork memory dream [--role ROLE] [--dry-run] [--apply] [--by BY]
```

Four memory operations beyond the pen:

| Command | What it does |
|---|---|
| `memory pack` | Assembles a task-scoped pack - the entries worth injecting for one task, ranked and cut to `--budget` bytes - so a lane reads the relevant memory instead of every entry. |
| `memory search` | Deterministic search over the role's memory (short, long and archived), the same scoring the pack uses. |
| `memory verify` | Re-checks every evidence citation a record carries: each cited revision must exist and each cited path must still exist. It reports per kind and the **worst status wins** (`revision drifted | revision: <sha> is a commit here; path: <p> is missing`). `--focus` narrows it, `--json` is machine-readable, `--apply` rewrites the records it can repair; the default is report-only. |
| `memory dream` | Proposes promotions (a stale short-term entry that belongs in long-term memory), edits and prunes. `--dry-run` is the default; `--apply` writes them and records the pass in the ledger. |

`memory verify` is the answer to a memory that cites a revision the tree no longer
has: the record keeps its text, but the drifted evidence is named instead of
reading as verified. `load` shows the role's memory; these commands decide what
belongs in it.

## Tasks, board and scheduling

### `task`

```text
teamwork task {add,list,next,set,check,reclaim,rm,archive} ...
```

Manage a role's shared priority queue.

#### `task add`

```text
teamwork task add AGENT TITLE [--priority {P0,P1,P2,P3}]
    [--status {todo,doing,blocked}] [--deps DEPS] [--feature F-0001]
    [--shared SHARED] [--review-profile {fast,standard,deep}]
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
| `--feature` | Slice the task to a `ready` or `active` feature (`F-0001`); the record is written as `- feature: F-0001` after `- deps:`, and a queue written without the flag is byte-identical to before the field existed. A `proposed` feature is not frozen yet and a `done`/`dropped` one takes no work, so both are refused (`2`). Only that feature's own squad may claim the task - see [`feature`](cli-workflow.md#feature). |

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

A task that carries `--feature F-nnnn` belongs to one feature team: it is
executable by an instance iff the record's `owner` is that instance, or the
instance's `Agents/<Instance>/Team.md` names that owner, **and** the record is
`active`. An instance with no `under:` never executes a feature task, a leader
executes only its own, and a `ready` feature's tasks are queued and held. A task
with no `--feature` belongs to no team and stays executable by any instance of
its role. When everything ready is another team's, the command says so and exits
`3`:

```text
teamwork: Developer-2 (developer) has no executable task of its own team
  (2 ready in the queue, 2 held by another team)
  - T-0071 [P1] feature=F-0002 owner=TeamLeader-1
```

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

#### `task archive`

```text
teamwork task archive AGENT
```

Fold that role's finished tasks out of the live queue and into its archive file,
so a long-lived role's `TaskQueue.md` stops growing and a `load` stays small. Only
`done` and `dropped` tasks move; an open task is never archived. Run it after a
merge, when the role's queue is longer than the work in front of it.

### `board`

```text
teamwork board
teamwork board --check [--json]
teamwork board --write [--json]
```

Cross-agent board with counts and each role's next task. `--check` compares the
two task tables of `docs/Team/Board.md` with the role queues and exits `1` naming
every stale row (`0` when equal); `--write` renders them from the queues and exits
`0`, naming every row it drops because no in-scope queue record carries it.
`--json` prints one object (`board`, `ok`/`written`, `tasks`, `queues`, and
`problems`/`dropped`) and is only valid with `--check` or `--write`. A board that
is missing its tables, or a queue set that cannot be read, is a setup error
(`2`), never a clean check.

The committed board is written by the **merging Reviewer**, not by the feature
branch: `pr merge` (and therefore a passing `review`) re-renders it from the
queues and commits it as a `chore(records)` change after the merge. A branch that
still carries its own render is not an error - `preflight` charges only drift the
branch itself caused - but the merge's re-render makes the carried copy irrelevant,
so no lane needs to hand-render before submitting. If that carried copy conflicts
with a base that moved, the rebase the probe prints should **drop** it (the merge
writes the file) instead of rendering it again. `board --write` is the repair
command for a board that is already on the base; a render that could not be
committed says so and names it.

### `parallel`

```text
teamwork parallel
```

Show free concurrency slots, ready work, and how many lanes to start.

### `pulse`

```text
teamwork pulse [--commit] [--interval INTERVAL] [--mode {off,observe,auto}]
               [--agent AGENT] [--spawn] [--no-scale]
```

CEO wake-up: print idle lanes, ready work and a dispatch plan. `--commit` applies
the assignments now. `--interval` stores the pulse interval in minutes. Exit code
`3` means nothing to dispatch. `--commit` also **sizes the roster to the work**: it
adds an instance for every `LANE_WIP` units of ready work and one Reviewer per
unclaimed deliverable, bounded by the per-role cap (4), the per-wake cap (6),
`LaneMax` and the free provider slots, then folds the seats it cannot feed. An
`observe`/`off` wake is a report: it claims nothing, adds nothing and retires
nothing. `--no-scale` dispatches to the current roster only.

### `swarm`

```text
teamwork swarm run [--lanes N] [--waves N] [--minutes MINUTES] [--lane-minutes MINUTES]
                   [--poll SECONDS] [--mode MODE] [--host HOST] [--by BY] [--dry-run]
                   [--no-scale]
```

The engine's own supervisor. It measures what is in hand - ready tasks and
unclaimed reviews, weighted 1 for prose, 2 for code, 3 for a
security/release/data unit and +1 for a bug - and starts `ceil(weight / 3)` lanes,
bounded by the free provider slots and `LaneMax` (default 8). Before the first
wave it sizes the **roster** to the same measurement (`instance add`, bounded by
the per-role and per-wake caps and the free slots; `--no-scale` skips it), so the
lane count is not capped by how many instances happened to be staffed. The number
is re-derived every wave, so the swarm scales up as the board grows and down (to
zero) as it drains, and each lane's budget follows its unit: 10 tool calls/10 min for
prose, 16/25 for code, 24/40 for a deep unit. It starts one detached process per
lane and returns; the next wake reconciles the finished lanes and computes the next
wave.

A claim with no live lane behind it (for example after `pulse --commit`) is
adopted for its instance; an assignment that leaves no self-check, PR or status
change gets a bounded retry (`LaneAttempts`, default 2), and past that the claim
stays on the board and the CEO decides. A deliverable in `review` becomes a
Reviewer lane. `--dry-run` prints the measured policy and the next wave and starts
nothing. `--lanes N` caps the policy, `--fixed --lanes N` turns it off. Dispatch
requires the `auto` accept mode (`PulseMode`), like `pulse --commit`.

```text
# Swarm (/project/.pi/Teamwork/Teams/Project)
# accept mode: auto (from default: no PulseMode in Settings.json) | attempts 2
# | swarm budget 60m | sizing: complexity
## complexity (score 6 -> moderate)
- ready: 3 task unit(s) (standard 3) from 1 queue(s)
- reviews: 0 unclaimed deliverable(s)
- assigned: 0 unit(s) claimed with no live lane
- queue: 3 open task(s), 0 open feature(s), 0 dependency edge(s)
- in flight: 0 lane(s), 2692 free provider slot(s)
- policy: up to 2 lane(s) this wave, bound by the complexity score (LaneMax 8);
  budget per unit: standard 16 call(s)/25m
```

```sh
teamwork swarm run --dry-run
teamwork swarm run --lanes 6 --minutes 90 --poll 5
```

### `lane`

```text
teamwork lane {start,list,status,logs,wait,stop,reap,preempt} ...
```

One lane is one child process with a packet in `Agents/<Instance>/Runs/<run>.md`,
a record in `Runtime/Lanes/<run>.json` and a log beside the packet. The record
survives the CLI call that started it.

#### `lane start`

```text
teamwork lane start --agent AGENT [--task TASK] [--review-owner ROLE] [--prompt TEXT]
                    [--prompt-file PATH] [--model MODEL] [--provider PROVIDER]
                    [--minutes MINUTES] [--tool-budget N] [--attempt N] [--attempts N]
                    [--resume] [--host HOST] [--print]
```

Start one lane. `--task` claims it (or `--review-owner` claims the review),
writes the packet and launches the host CLI; `--print` writes the packet and
prints the command without starting anything. `--resume` reuses the lane's host
session on a retry. The launcher is the detected host, `LaneHost`, or a
`TEAMWORK_LANE_CMD` template split without a shell.

#### `lane list`, `lane status`, `lane logs`

```text
teamwork lane list [--all] [--limit N] [--full]
teamwork lane status [HANDLE] [--live]
teamwork lane logs HANDLE [--lines N]
```

Inspect lanes: `list` shows live records by default, `status` reconciles each
record with its process, outcome file and budget before printing, and `logs` tails
a lane's output.

#### `lane wait`, `lane stop`, `lane reap`

```text
teamwork lane wait HANDLE... [--timeout SECONDS]
teamwork lane stop HANDLE [--reason REASON] [--by BY]
teamwork lane reap
```

`wait` blocks until the named lanes end; `stop` signals a lane's process group,
records why and releases its provider lease; `reap` reconciles lanes that died
without writing an outcome and frees their slots.

#### `lane preempt`

```text
teamwork lane preempt HANDLE [--message M-0001] [--reason REASON] [--by BY]
```

Stop a lane because an urgent message displaced it: the lane is stopped, its task
is marked `paused` with the message id that displaced it, and a mailbox lane is
started for the recipient. `lane resume <T-id>` returns the task to `doing` once
the mailbox is empty. The supervisor runs this on its next wave for any instance
holding a pending `urgent` message, so an operator rarely needs it by hand.

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

## Coordination

Two records carry work that is not a task: a message to another agent, and an
item that needs a person.

### `message`

```text
teamwork message send --from SENDER --to TO --subject SUBJECT
    [--priority {urgent,high,normal,low}] [--body BODY] [--task TASK] [--reply-to M-ID]
teamwork message inbox --for INSTANCE [--all] [--json]
teamwork message take M-ID --for INSTANCE --by BY
teamwork message done M-ID --for INSTANCE --by BY --result RESULT [--drop]
```

The mailbox is `Runtime/Mailbox/<Instance>/M-nnnn.json`, one file per message,
mutated under `Runtime/Locks/mailbox.lock`. It is not a second ledger: the ledger
records that a message was sent, taken and done; the mailbox holds the message.

| Verb | What it does |
|---|---|
| `send` | Queues a message for another instance. The subject is one line (120 chars), the body is capped at 4000. A recipient that is not in the roster is refused with exit `2` and the known names. |
| `inbox` | The pending messages in priority order, then oldest first. `--all` includes taken and done; `--json` prints one JSON object per message. |
| `take` | Claims a message for one lane, so a second lane of the same role cannot process it twice. Taking a message another lane holds is refused. |
| `done` | Closes it with the result (`--drop` records it as dropped instead). A message another lane took cannot be closed by you. |

Priority is the contract: `urgent` is the only one that preempts. The supervisor
stops the recipient's lane, marks its task `paused` with the message id, runs a
mailbox lane that drains the queue, and `lane resume` puts the paused task back.
`high`, `normal` and `low` never interrupt a step; they are read at the next step
(or in the lane packet, which opens with `## Messages for you`). Use a message for
a review finding the author must act on, a fact another role holds, an interface
change that invalidates a peer's work, or a hand-off - not to assign work (that is
`task add`) and not to report progress (that is the worklog).

### `attention`

```text
teamwork attention add --text TEXT --kind {authorization,decision,blocker,review} [--task TASK] --by BY
teamwork attention list
teamwork attention resolve M-ID --by BY --resolution RESOLUTION
```

An attention item is the one thing an agent may not decide alone: an
authorization, a decision that changes the goal, a blocker, or a review the CEO
must arbitrate. `add` records it (the intern protocol's "proactivity is a record"
path), `list` prints the open items oldest first, and `resolve` closes one with the
decision that settled it. The CEO reads this list; it is not a channel to the user.

## Live state

### `status`

```text
teamwork status [--json] [--agent INSTANCE]
```

One row per instance and one row per live lane, so the operator panel and the
status widget answer "who is working on what, and with which model". `--agent` narrows
the rows to one instance; an unknown name exits 2, a team with no instance prints
`- no instance` and exits 3, and the JSON feed exits 0 even when empty.

The text form prints `# Lanes (N)` and one line per lane before the instance
rows, then one instance line each (task id, title, elapsed, progress percent),
never wider than 110 columns.

`--json` emits schema 2, additive to schema 1:

```json
{
  "schema": 2,
  "generated": "2026-11-12T19:00:00",
  "count": 17,
  "counts": {"busy": 8, "idle": 9, "ready": 0, "review": 2, "lanes": 6},
  "instances": [{"instance": "Developer-1", "role": "developer", "state": "busy",
                 "task": "T-0130", "title": "...", "elapsed_text": "12m",
                 "progress": "attempt 1/2, 60% of 25m", "progress_pct": 60,
                 "model": "deepseek-chat", "provider": "deepseek", "lane": "L-0383",
                 "lane_state": "running", "elapsed": 720}],
  "lanes": [{"id": "L-0383", "instance": "Developer-1", "role": "developer",
             "task": "T-0130", "state": "running", "elapsed_text": "12m",
             "model": "deepseek-chat", "provider": "deepseek", "attempt": "1/2"}]
}
```

`counts.lanes` always equals the length of the `lanes` array the same call
returns, so a header stays true under `--agent`. Lanes are live first, then the
most recent by `created` (id ascending as the tiebreak), bounded to 6; a review
lane carries `task: ""`; the order is stable across two calls with no state
change. `model` and `provider` resolve once per call from
`Settings.json` -> `Models.agents[<Instance>]`, else `Models.roles[<role>]`, else
`""` for both - an unset model is never guessed.

## Memory

### `load`

```text
teamwork load AGENT [--limit LIMIT]
```

Print the ROLE's short-term memory (startup context), then its open lessons
(first 10) and the top 10 active project knowledge records, with the counts of
fixed lessons and superseded knowledge. The ranking and caps are the memory
model's; the full lifecycle is in `references/State.md`.

A name this team cannot resolve - no registered instance, and no role directory
for a canonical role - is refused with exit `1` and creates nothing, and the
refusal lists the roles the team does know (`Roles/<Name>/` on its own is not
proof: an old `remember` bug could create one for any spelling).

### `remember`

```text
teamwork remember AGENT TEXT [--by BY] [--src SRC] [--rev REV]
    [--layer {short,long}] [--key KEY] [--importance IMPORTANCE]
    [--tags TAGS] [--pin]
```

Add or update an entry in the ROLE's shared memory. It takes the role's memory
pen for the duration of the write (and the consolidation that follows it), so a
peer's concurrent write waits its turn instead of interleaving; `--by` should name
the instance, because that is who the implicit lease names. A name the team
cannot resolve is refused with exit `1` before any directory is created, so a
typo never becomes a role.

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


## The rest of the reference

- [CLI reference (this page)](cli.md) - every command, grouped by job.
- [CLI: records and knowledge](cli-records.md) - learning, context, criteria and tests.
- [CLI: review and governance](cli-review.md) - review, archive, decisions, disputes, red lines, skills.
- [CLI: feature teams and git workflow](cli-workflow.md) - features, branches, PRs, commits, hooks.
- [CLI: audit and control](cli-audit.md) - ledger, trace, coordination, loop, model, scripts.
