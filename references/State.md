# Memory and task state

Owner: CEO.

Reference for the /teamwork skill. Loaded on demand; `SKILL.md` keeps the
operating procedure.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md) | [Coordination](Coordination.md)

## Memory model

Memory belongs to the **role**, not the instance. `Roles/<Role>/` holds one
short-term file, one long-term file, one archive and one `TaskQueue.md`, shared by
every instance of that role; `Agents/<Instance>/` holds only what is private to
one lane. The CEO additionally owns the global file.

| Layer | File | Loaded | Purpose |
|---|---|---|---|
| Short-term | `Roles/<Role>/ShortTermMemory.md` | at startup (`load`) | working memory for the current tasks |
| Long-term | `Roles/<Role>/LongTermMemory.md` | never; queried (`recall`) | durable facts, interfaces, gotchas |
| Archive | `Roles/<Role>/ArchivedMemory.md` | never; searchable | evicted long-term entries |
| Shared | `Global/GlobalMemory.md` | read on demand | facts no agent should re-ask |
| Lessons | `Roles/<Role>/Lessons.md` | at startup (`load`, first 10 open) | mistakes the role will not repeat |
| Knowledge | `Knowledge.md` (team root) | at startup (`load`, top 10 active) | durable project facts, ranked by importance and uses |
| Context tree | `ctx://` (computed, no file) | on demand (`context ...`) | read-only L0/L1/L2 view over every store above |

```sh
teamwork.py load <agent>                                  # startup context
teamwork.py remember <agent> "<fact>" --key k --importance 0-5 [--pin] [--by <instance>]
teamwork.py recall "<query>" --agent <agent> | --global | --all
teamwork.py touch <agent> <key> [--by <instance>]          # mark as used
teamwork.py forget <agent> <key> [--by <instance>]         # delete an entry
teamwork.py consolidate --all                             # auto maintenance
teamwork.py global "<fact>" --key k --importance 4        # CEO only
```

## One reviser per role

Any role can run several instances (`instance add <role> --count N`). They read
the same memory and claim from the same queue, but **only one instance of a role
revises that role's memory at a time** - otherwise two lanes interleave edits and
the role's memory becomes a merge nobody reasoned about (A adds an entry, B
consolidates and evicts it, A adds the next one against a file it never saw).

```sh
teamwork.py instance add architect --count 2        # scale ANY role
teamwork.py instance list                           # role, instances, memory writer
teamwork.py instance retire architect-3 --reason "trimmed"
teamwork.py memory claim architect --by Architect-2 --reason "rewrite the contract"
teamwork.py memory renew architect --by Architect-2 --ttl 30
teamwork.py memory release architect --by Architect-2
teamwork.py memory contest architect --by Architect-3 --reason "three tasks blocked"
teamwork.py memory extend architect --by CTO --ttl 45 --reason "the rewrite is large"
teamwork.py memory revoke architect --by CTO --reason "that lane is wedged"
teamwork.py memory status [architect] [--json]     # who may write now
```

| Rule | Mechanism |
|---|---|
| One writer per role | `Runtime/Locks/memory-<Role>.claim`, a JSON lease (`instance`, `token`, `expires_ts`, `explicit`, `reason`, `contests`, `arbitrated_by`) |
| Held across several writes | `memory claim` sets `explicit: true` and keeps it until `memory release`, so a coherent update lands whole |
| A single write is still exclusive | `remember`/`forget`/`touch`/`consolidate` take an implicit lease for their own duration and give it back |
| Peers are read-only, never blocked | `load`, `recall`, `board` always work; a mutating command from a peer exits `2` naming the holder and the minutes left |
| A dead lane cannot freeze a role | the lease expires (`MemoryLeaseMinutes`, default 30) and the next writer takes it over |
| A stalled holder is visible, not silent | `memory claim --force "<why>"` or `memory release --force "<why>"` records `memory.claim.force` in the ledger |
| Different roles never contend | one claim file per role; every role revises its own memory in parallel |
| Only the role's own instances (or the CEO) may write it | `memory_actor` refuses a peer role with a scope error |

### A lease that runs long: the CTO rules

A lease older than `MemoryStallMinutes` (default 15) is **slow**, and `memory
status` marks it `SLOW`. Any *other* instance of the role can then contest it:

```sh
teamwork.py memory contest architect --by Architect-3 --reason "three tasks are blocked"
```

That records the contest on the lease (`memory.contest`), puts a `P0`
`memory-lease` task on the arbiter's queue once (no duplicate case), and tells
the peer who rules. **The CTO is the arbiter** - it owns engineering standards and
the build and lock policy, so a stuck writer is an engineering question rather
than a dispute between peers. The arbiter rules with one of two commands, each
recorded:

| Ruling | Command | Effect |
|---|---|---|
| more time is fair | `memory extend <role> --by CTO --ttl 45 --reason '<why>'` | the holder keeps the pen for another N minutes; the contests are answered and cleared (`memory.grant`) |
| the pen is removed | `memory revoke <role> --by CTO --reason '<why>'` | the lease is cleared, the role is free immediately (`memory.revoke`) |

Three rules keep the arbiter honest, and the engine refuses otherwise:

- **Only the arbiter (or the CEO) rules.** A peer, including the holder's own
  manager outside that chain, cannot extend or remove another instance's lease.
- **A vacant arbiter folds up.** Without a CTO (a slim roster) the request goes to
  the CEO, and the command says which seat was folded.
- **No party rules its own lease.** A CTO's own memory goes to the CEO; when the
  holder is at the top of the chain too, no seat may rule and the peers are told to
  open a dispute instead.

The holder never rules itself either: a contest from the holder is refused, and
its own `memory release` or `--force` takeover remain the ways out.

The role file lock `Runtime/Locks/role-<Role>.lock` still serialises one write and
the task queue; the lease is the part that survives between commands. Reads take
neither.

**The lease governs the CLI, so the memory file is never edited by hand.** A lane
that writes `Roles/<Role>/ShortTermMemory.md` with an editor or a shell redirect
bypasses every rule above; use `remember`/`forget`/`touch` (or `claim` around
several of them), which also record provenance in the ledger.

Consolidation rules (automatic on `remember`/`load`, run manually by the CEO):

- A short-term entry unused for `STALE_DAYS` (3) with fewer than `MIN_USES` (2)
  uses is **promoted** to long-term when its importance >= 2, otherwise dropped.
- Overflow beyond `SHORT_CAP` (24) is promoted or dropped by score.
- Long-term is capped at `LONG_CAP` (64); the lowest-scoring entries (importance,
  use count, recency) are moved to the archive, pinned entries are never evicted.
- Duplicate keys merge: highest importance, summed uses, newest body.
- Caps are configurable with `TEAMWORK_SHORT_CAP`, `TEAMWORK_LONG_CAP`,
  `TEAMWORK_ARCHIVE_CAP`, `TEAMWORK_STALE_DAYS`, `TEAMWORK_MIN_USES`.
- The memory lease is `MemoryLeaseMinutes` and its stall threshold
  `MemoryStallMinutes` in `Settings.json` (env `TEAMWORK_MEMORY_LEASE_MINUTES`,
  `TEAMWORK_MEMORY_STALL_MINUTES`); the arbiter role is `TEAMWORK_MEMORY_ARBITER`
  (default `cto`).

What belongs where: task-local working notes and in-flight decisions in
short-term; verified interfaces, commands, revisions, gotchas and rejected
approaches in long-term; team-wide facts in global memory (CEO), proposed by the
owner who discovered them; a mistake the role must not repeat in its
`Lessons.md`; a durable project fact in the shared `Knowledge.md`.

### Re-resolving the evidence: `memory verify`

A record's `evidence` line names its ground truth, and `memory verify` re-reads
that ground truth now: `@<sha>` or `rev <sha>` through `git cat-file -e`, a
`path/to/file[:LINE]` against the working tree, an `https://` source against its
access date (`accessed YYYY-MM-DD` or `(YYYY-MM-DD)`, at most 400 days old). Every
kind the evidence names is checked and the worst status wins - `drifted` over
`unverifiable` over `verified` - with the reason naming each kind, so a drifted
path behind a valid revision is reported instead of passing on the revision. A
record whose evidence names none of the three is `unverifiable`, never `drifted`.

```sh
teamwork.py memory verify [--role R] [--limit N] [--json]
teamwork.py memory verify --focus <text | T-ID> [--limit N]   # the best 25, by the 4.1 score
teamwork.py memory verify --apply --by <you>   # stamp the knowledge records it reported
```

`--focus` tunes the pass to a goal (9.1): the text - or a task id, resolved to its
title through `memorypack.task_query` - ranks every record with the frozen 4.1
score, and the first `--limit` (default 25, `0` still means all) are verified in
score order, highest first. The rest are reported as
`# verify: N deferred by --focus`, one line after the footer. Without `--focus`
every record is verified in pointer order and the output is byte-identical to the
pass before the flag.

`--apply` writes exactly two fields on knowledge records, `checked` and
`verify_status`, and appends one `memory.verify` ledger event with the counts:
statements and evidence are never rewritten, no record is deleted, and lessons or
short-term entries are reported only. `memory dream` prints the same `drifted`
group from the same function, so the pass and the command cannot disagree.

## Lessons and project knowledge

Two stores sit beside memory. Both are team-local working state, gitignored and
never committed, and both are written only through their command - a hand edit is
a defect. A missing file is an empty store, never an error.

| Store | File | Scope | Record |
|---|---|---|---|
| Lessons | `Roles/<Role>/Lessons.md` | one role, shared by all its instances | `L-nnnn`: mistake, cause, rule, evidence |
| Knowledge | `Knowledge.md` at the team root | every role, one store | `K-nnnn`: topic, statement, kind, evidence, tags, importance |

### Lessons

One record per mistake:

```text
## L-0001 - <what went wrong>
- role: <role>
- status: open | fixed
- mistake: <the observable failure>
- cause: <why it happened>
- rule: <what the agent does instead>
- evidence: <command @rev -> result>
- task: <T-id>            (optional)
- skill: <tw-name>        (set when a skill fixes it)
- by: <instance>
- created: YYYY-MM-DD
- updated: YYYY-MM-DD
```

```sh
teamwork lesson add --by <you> --mistake TEXT --cause TEXT --rule TEXT --evidence TEXT \
    [--role ROLE] [--task TASK]
teamwork lesson list [--role ROLE] [--status open|fixed|all]
teamwork lesson show L_ID
teamwork lesson fix L_ID --by <you> [--rule RULE] [--skill TW_NAME] [--evidence EVIDENCE]
```

- `add` requires `--by`, `--mistake`, `--cause`, `--rule` and `--evidence`; the
  role defaults to the actor's role. Ids are `L-` plus four digits, allocated
  from the maximum over every role's file, so they are globally unique.
- `list` defaults to every role and `--status all`, sorted by id, one line each.
- `fix` moves an `open` lesson to `fixed` and needs evidence. An already `fixed`
  lesson may be re-proved only with new `--evidence`; without it the command
  exits `1` and changes nothing. A `--skill` must be a registered `tw-` skill of
  kind `mistake`; `skill create --from-lesson` sets the same link from the other
  side.
- `load` prints the role's open lessons (first 10) and the number of fixed ones,
  so every instance starts by reading the mistakes it must not repeat.

### Knowledge

One record is one durable fact about this project:

```text
## K-0001 - <topic>
- statement: <one fact, rule or gotcha, <= 500 chars>
- kind: fact | experience | preference | gotcha | rule   (absent reads as fact)
- evidence: <command @rev -> result | path:line | URL + access date>
- tags: <lower-case kebab comma list> (empty renders `-`)
- owner: <role that first recorded it>
- by: <instance>
- task: <T-id>              (optional)
- importance: 1-5
- uses: N
- status: active | superseded
- supersedes: K-0002        (optional)
- superseded_by: K-0004     (set on the old record)
- created: YYYY-MM-DD
- updated: YYYY-MM-DD
```

```sh
teamwork knowledge add --by <you> --topic TEXT --statement TEXT --evidence TEXT \
    [--kind KIND] [--tags TAGS] [--importance 1-5] [--supersedes K-0002] [--task T]
teamwork knowledge list [--tag TAG] [--role ROLE] [--kind KIND] \
    [--status active|superseded|all] [--limit N]
teamwork knowledge search QUERY [--kind KIND] [--status active|superseded|all] [--limit N]
teamwork knowledge show K_ID
teamwork knowledge touch K_ID --by <you>
```

- `add` requires `--by`, `--topic`, `--statement` and `--evidence`; `--tags`
  defaults to empty and `--importance` to 3. `--kind` defaults to `fact` and is
  one of `experience`, `preference`, `gotcha` or `rule`; a record without the
  field reads as `fact`, so older records need no migration. `list` and `search`
  accept `--kind` to keep one kind, and `load` plus the context L0 show it.
  `--role` on `list` matches the record's `owner` (provenance, not a permission).
- Duplicates are **active-only** and exact after whitespace collapse and
  case-folding of `topic` and `statement`. Re-adding an active duplicate returns
  the existing id and adds nothing; the same topic with a different statement is
  refused (`2`) until the holder is named with `--supersedes`.
- `--supersedes` marks the old record `superseded` with `superseded_by` and links
  the new one; an inactive target is refused except the exact re-instatement
  case. Records are never silently deleted, so history stays readable.
- `list` and `search` default to active records, limit 20 (`0` = all), ordered by
  importance descending, then uses, then updated, then id ascending. `show` reads
  one record including its superseded history; `touch` increments `uses` and is
  how a fact that was actually used rises in the ranking.
- `load` prints the top 10 active records project-wide as
  `- [K-0001] [experience] <topic>: <statement> (uses=N, tags=...)` and the
  active/superseded counts, so the startup read is the most important and most
  used knowledge, not the newest ten.
- `load` and every lane packet open with the memory index (Memory.md 11): a capped
  pointer list `- <topic> -> <file>#<id>` over the active knowledge topics and the
  open lesson titles, in the 4.1 score order for the task, at most 8 lines, and
  `# memory index: N topic(s), M record(s)` / `# index: B bytes (budget 800)`
  around them. It points, it never copies a statement, and a line that would
  overspend `INDEX_BUDGET_BYTES` (800) is dropped rather than truncated.
- The index replaces the verbose `- [L-0001] mistake -> rule` rows `load` used to
  print and is charged against the pack budget (`index + pack <= 4000`), so the
  whole `load` output does not grow by the index's bytes (AC-M22-4, T-0057).

Measured back to back on one store at `8a34759`: the `90502bb` renderer in
`.pi/Scratch/ceo/baseline` and the merged one, run one after the other.

| surface | before `90502bb` | after `8a34759` | delta |
|---|---|---|---|
| `load CEO` | 8112 B | 5455 B | -2657 B |
| `load Developer` | 5746 B | 5776 B | +30 B |
| `load Tester` | 4995 B | 5415 B | +420 B |
| the index block for CEO | n/a | 523 B, 8 lines | n/a |

Both growths are inside the 800 B index bound the `AC-M22-4` ruling allows. Writing
one more lesson (`L-0019`) moved `load CEO` +354 B on the old renderer and 0 B on
the merged one: the index is capped, so a lane's startup read stops tracking the
size of the store. The full table, with the pack, the dream pass and transcript
reach, is `Memory.md` 13.

### Context tree

`ctx://` is a read-only view over the stores above: memory, lessons, knowledge,
skills, docs and tasks. Every node resolves to an existing file or record; the
view adds no file, index, cache or summary sidecar, and a missing store reads as
an empty node. It is not a second store and never replaces `load`, the gates or
the evidence rule.

- **Levels**: L0 is the one-line summary, L1 the record fields, heading tree or
  child list, L2 the full record or file. They are computed at read time and
  never written back; there is no `.abstract.md`/`.overview.md` sidecar and no
  model call.
- **Commands**: `context ls` (default `ctx://`, level 0, limit 20),
  `context tree` (default depth 2), `context read <uri>` (default level 1),
  `context find "<query>" [--scope <uri>]` (default scope `ctx://`, limit 10),
  `context stats` and `context digest <T-id>`. All are read-only.
- **Scope**: `--scope` is a URI prefix such as `ctx://role/developer` or
  `ctx://project/knowledge`; a node outside it is never returned, and an unknown
  scope exits `2`. Retrieval is deterministic token matching over L0/L1 - no
  embeddings, network or index - and it never reads L2.
- **Transcripts**: `--scope transcripts` is the one non-URI scope, and it is
  additive - every other scope's output stays byte-identical. It searches the two
  append-only sources the engine writes and otherwise never reads, one hit per
  unit: `Ledger.jsonl#<n>` for one ledger event (rendered from its
  action/actor/target/detail, not the raw JSON) and
  `Agents/<Instance>/WorkLog.md:<line>` for one worklog line. Ranking is the same
  4.1 score, the output is capped at 10 hits and 2,000 bytes with the
  `# search:` footer `memory search` prints, a hit's text clips at 200
  characters, and a query that shares no term returns an honest empty result.
  The reader streams the file line by line, so a 100k-line ledger costs a line of
  memory, not the file. `recall --transcripts` appends the same block under
  `## transcripts`; without the flag `recall` prints exactly what it did before.
- **Docs**: `ctx://project/docs` enumerates the work tree at read time (an
  untracked doc appears, a tracked file deleted from the work tree disappears),
  never the git index.
- **Kinds**: a knowledge record carries `kind` (`fact` default, `experience`,
  `preference`, `gotcha`, `rule`). A lesson stays the record of a mistake; an
  `experience` is a reusable approach that worked. `context digest` proposes
  `lesson add` / `knowledge add --kind experience` templates from a task but
  writes nothing; the proposed title is capped at 120 characters and the cause
  at 300.
- **No secret is surfaced**: the view prints only what is already stored; the
  docs are privacy-scanned and the records obey the same red line.

### Why they are not committed

`Lessons.md` and `Knowledge.md` are the team's working experience, not project
output: they change after every task, they carry local incident detail and
revision-specific evidence, and committing them would turn every append into a
merge conflict, a review target and a privacy surface. The durable, user-facing
result of that experience is written where it belongs - `docs/Team/` for the
project's records and `docs/guide/` for the product's documentation. Both stores
are still evidence-bearing: a `K-` record without evidence, or a lesson without
the run that proved it, is opinion. Never store a credential, token or personal
data in either store, and cite knowledge as `K-0001` plus its evidence, never as
the record's authority.

## Context economy and the token budget

The startup read is the always-on floor; history is a recall cost, not a startup
cost. A whole `Archive.md` read is ~0.63M tokens on this revision against a
~0.11-0.15M startup, so answer a question by id:

| Question | Command |
|---|---|
| What did the review decide about this task? | `archive --task T-nnnn` |
| What decisions exist, by kind? | `decision list [--kind KIND]` |
| What is open, in flight or waiting? | `board` |
| Follow one task, criterion, test or PR | `trace <id>` |
| What does the context tree say? | `context find` / `context read <uri>` |

Never read all of `Archive.md`, `Decisions.md`, `Plan.md` or a `TaskQueue.md`;
the largest queue is ~64k tokens at the M18 cut. `archive` also accepts
`--limit N`, `--all` and `--full`; its default is the 8 most recent entries.
Task ids are per role, so a repeated id can return more than one role's entry;
read the heading's role.

### Token budget and roster

- `harness budget` reports the **startup** read (`AGENTS.md` block + `SKILL.md` +
  the role charter + short memory + open lessons + top-10 knowledge) per
  instance against `AlwaysOnBudgetKb` (122880 B default), and exits 1 while any
  row is over. `--recallable` reports the **recall-only** surface - long-term and
  archived memory, fixed lessons, superseded knowledge - which `load` never
  prints; it is a visibility row, not a second cap.
- When a startup row is over, trim what `load` prints (memory entries, the
  lesson/knowledge caps) or record why an entry stays; never raise the cap to
  make the row pass.
- `throughput` re-reads review latency, verdict/rework share, queue depth,
  instance count and surface bytes (AGENTS, SKILL, Archive, Decisions, Plan,
  docs/Team, largest TaskQueue) with a `//4` token estimate; `--json` is the
  machine form.
- `parallel` says how many lanes the ready work supports and `instance list` is
  the roster. `slim` is the default; add an instance only for a named
  deliverable. `instance retire` MOVES the idle directory to
  `Runtime/Retired/<Instance>/` (a repeat gets a timestamped sibling) and never
  deletes artifacts, reports or the worklog. Before a cut, verify `git rev-parse
  HEAD` is at or after the move-only revision (`b9e5135`): the one cut from a
  stale checkout deleted 102 artifact paths and is recorded as `L-0001`.

### Review first pass and slices

The author's self-check note answers the boundary/empty/duplicate/second-call
case, the contract surface, concurrency and shared writes, and the exact scope;
the Reviewer judges the requirement and its acceptance layer. On a code task the
Tester records the full suite once at the revision and the Reviewer cites it
(`--credit`), so the ~30-minute suite is paid once. `preflight` warns when the
diff passes its profile slice: 6 files / 300 changed lines (`fast`), 12/600
(`standard`), 24/1,200 (`deep`); split it or say why it is one coherent
contract. The warning is not a failure.

## Task lists and priority

Every role keeps one shared `TaskQueue.md`, priority ordered; any of its instances
may claim from it. `P0` = critical path
code, `P1` = tests/verification, `P2` = docs/polish, `P3` = nice-to-have.

```sh
teamwork.py task add <agent> "<title>" --priority P1 --deps architect:T-0003 \
    --shared <issue/PR> --body "acceptance criteria"
teamwork.py task next <agent>            # highest-priority task with deps done
teamwork.py task list <agent>            # ready/blocked per task
teamwork.py task set <agent> T-0002 --status doing
teamwork.py task set <role> T-0002 --status selfcheck   # then selfcheck, pr open, review, pr merge
teamwork.py board                        # all queues: counts, next task, blockers
```

Rules: dependencies are explicit (`agent:T-0001` for cross-agent), a task with
unmet dependencies is never started, a finished task is marked `done` with
evidence before the agent looks for the next one, and an agent with executable
work never idles.

## The agent mailbox: queued, prioritised, preemptible

`Inbox.md` is prose; the mailbox is the channel agents actually use. One message is
one JSON record under `Runtime/Mailbox/<Instance>/<M-id>.json`, mutated under
`Runtime/Locks/mailbox.lock`; ids are per recipient and never reused.

```sh
teamwork.py message send --from <you> --to <instance> --priority <p> \
    --subject '<one line>' [--body '<detail>'] [--task <T-id>] [--reply-to <M-id>]
teamwork.py message inbox --for <instance> [--all] [--json]
teamwork.py message take <M-id> --for <instance> --by <you>
teamwork.py message done <M-id> --for <instance> --by <you> --result '<what you did>'
teamwork.py lane preempt <run> --message <M-id> [--reason '<why>']
teamwork.py lane resume <T-id>
```

| priority | rank | delivery |
|---|---|---|
| `urgent` | 0 | preemption: the supervisor stops the recipient's lane, sets the task `paused` with the message id, and starts a mailbox lane |
| `high` | 1 | the recipient's next read, before any new long work |
| `normal` | 2 | the recipient's next read, in order |
| `low` | 3 | the recipient's next read, in order |

Order is `(priority rank, created)`. A lane packet opens with
`## Messages for you (<n> pending: ...)` and the rows in that order; `message inbox`
is the same list on demand, so a long lane re-checks between steps.

State machine: `pending -> taken -> done | dropped`. `take` refuses a message another
lane holds and refuses one already closed, so one message is processed once; `done`
records the result the sender reads. `lane resume` returns a paused task to `doing`;
a `paused` task is in flight, so `loop` will not report STOP while one waits.

Why preemption is the supervisor's and not a peer's: an agent is one process and
cannot be interrupted mid-turn by another process. The cheap path is the queue (the
recipient reads it at its next step, nothing is lost); the expensive path is the
supervisor stopping the lane, because it is the only component that owns process
lifecycle. A message never carries authority - it carries a request, and the
recipient still records its own evidence.

Ledger actions: `message.send`, `message.take`, `message.done`, `lane.preempt`.
