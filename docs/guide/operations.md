# Operations - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Quickstart](quickstart.md) · [Usage patterns](usage.md) · [How it works](how-it-works.md) · [Features](features.md) · [CLI reference](cli.md)

How to run a team that is already staffed: keep it inside provider caps, keep its
memory coherent, resume it after a crash, prove its audit trail, route its models,
watch its live state, route a message between agents and keep the token budget
true. Every command here is also listed, with every flag, in the
[CLI reference](cli.md).

## 1. Provider slots: never overload one endpoint

A slot lease is the team's admission control. Each provider has a configured cap
in `Settings.json` (for example 64 concurrent agents on a cloud host and a much
larger cap on a direct API), and a lane that needs a model takes a lease before
it starts model-heavy work:

```console
$ teamwork parallel
$ teamwork slot acquire --agent Developer-1 --provider deepseek
$ teamwork slot renew --agent Developer-1      # a long task, before the lease expires
$ teamwork slot release --agent Developer-1
```

`parallel` prints used, cap and free per provider plus the executable work that
could start right now. If the cap is reached, the lane does work that needs no
slot or switches provider - it never blocks the whole team, and it never kills a
peer's lease to make room. A live lease also protects the lane from `reclaim`:
reclaiming a live lane is refused unless the lease is dead.

The lease is infrastructure, not evidence: releasing a slot changes no record and
gates nothing. What it prevents is a fleet of agents rate-limited into failure at
the same moment.

## 2. The one memory pen

Memory belongs to the role. `Developer-1..N` read the same
`Roles/Developer/` files, and exactly one instance may revise them at a time:

```console
$ teamwork memory claim developer --by Developer-2 --reason "rewrite the build notes"
$ teamwork memory status developer
$ teamwork memory release developer --by Developer-2
```

A single `remember` takes the pen for its own duration; a multi-entry rewrite
claims it first and releases it when done. A peer's write while the pen is held is
refused, not merged - the engine never interleaves two edits into one memory file.

A lease that runs past `MemoryStallMinutes` is **contested, not waited out**:

```console
$ teamwork memory contest developer --by Developer-3 --reason "three tasks are blocked"
$ teamwork memory extend developer --by CTO --ttl 45 --reason "the rewrite is large"
#   or: teamwork memory revoke developer --by CTO --reason "that lane is wedged"
```

The CTO rules the contest, because a stuck writer is an engineering question. On
a roster without a CTO the request folds up to the CEO. A party never rules its
own lease, and a holder cannot contest itself: it releases the pen or finishes.
The ruling is recorded in the ledger, so "who removed the lock" always has an
answer.

## 3. Resume after a crash or a new session

All team state is on disk and none of it is in a process. A fresh agent starts
with three commands:

```console
$ teamwork load developer-1     # the role's short-term memory and open lessons
$ teamwork task next developer-1
$ teamwork map                  # roles, instances, open work
```

There is no handover meeting and no chat history to replay. `load` prints the
role's memory, its open lessons and the top-ranked project knowledge; `task next`
claims the highest-priority executable task whose dependencies are done; `map`
shows the tree. If a question is not answered by memory, `recall` queries
long-term memory and `context find` searches the derived view over memory,
lessons, knowledge, skills, docs and tasks.

A crashed lane's branch and worktree stay on disk. The next instance of the role
sees the task still `doing` (or `selfcheck`), finishes it and submits; a dead
lane's lease can be reclaimed with `reclaim`, a live one cannot.

## 4. The audit trail

Every mutation - a task, a criterion, a test record, a verdict, a merge - is
appended to `Ledger.jsonl` with `by`, `src` and `rev` provenance. Each record
carries the previous record's digest, so the chain is tamper-evident:

```console
$ teamwork ledger verify
$ teamwork ledger show --tail 20
$ teamwork trace T-0007
$ teamwork ledger export
```

- `ledger verify` recomputes the chain and fails on a single changed byte.
- `ledger show` reads recent events without loading the history.
- `trace` follows one task, criterion, test or PR end to end.
- `ledger export` writes a manifest - record digests plus the merged revision -
  that someone who does not trust the team can verify on their own.

A broken chain blocks `loop` from printing `STOP`. The ledger is append-only: the
team never edits, reorders or truncates it, and the digest function is frozen, so
changing it would invalidate every existing workspace.

## 5. Model routing

The engine ships no model and calls no LLM API. It reads what the host exposes.
`teamwork model auto` detects the agent host where the environment identifies it,
assigns the strongest available model to the decision lanes (CEO, Architect,
Reviewer, Security Auditor) and the economy model to the mechanical lanes, and
prints the plan as a dry run:

```console
$ teamwork model auto            # dry run: show the assignments
$ teamwork model auto --apply    # write them into Settings.json
$ teamwork model auto --json     # the same plan, machine readable
$ teamwork model set reviewer --provider anthropic --model strong
$ teamwork model get reviewer
```

The precedence is: an instance's own setting wins over the role default, and an
explicit `model set` wins over what detection proposed. `auto` never invents a
model id it did not read from the environment - when the host is unknown it says
so and writes nothing. That is the whole routing model: quality where output
compounds, the cheapest capable model where it does not.

## 6. Watch the team: live state and the widget

An instance is idle only while it holds no task, no memory pen, no provider slot,
no review claim and no live lane. Idle is cheap but not free: a seat is a
directory, a memory set and a queue entry, so a team that drains its work should
drain its roster too. `pulse --commit` folds the surplus seats on every wake, and
`teamwork instance prune` folds every idle instance in one move-only pass -
`Runtime/Retired/<Instance>/`, with the role's memory and queue kept and a ledger
record per fold. `--keep-required` keeps one instance of each gate-critical role,
`--dry-run` prints the plan, and `instance add <role>` restaffs when work returns.
The CEO is never folded.

The other half is scaling: `pulse --commit` and `swarm run` add an instance for
every `LANE_WIP` units of ready work and one Reviewer per unclaimed deliverable,
bounded by the per-role cap (4), the per-wake cap (6), `LaneMax` and the free
provider slots. `--no-scale` dispatches to the current roster, and an
`observe`/`off` wake is a report that adds and retires nothing. So the work - not
the roster, and not one lane - bounds how fast a stage lands.

`status` is the operator panel and the UI feed in one command:

```console
$ teamwork status                      # every instance, plus the recent lanes
$ teamwork status --agent Reviewer-1   # one instance
$ teamwork status --json               # the stable feed (schema 2)
```

The panel prints each instance's state (`busy`/`idle`), its current task, the
task title, elapsed time and progress, plus a `# Lanes` block for the recent lanes
(live first, then newest). The JSON feed carries `schema`, `generated`, `count`,
`counts` (`busy`, `idle`, `ready`, `review`, `lanes`), an `instances` array and a
`lanes` array; every row names the `model` and `provider` it runs with, so a
routing mistake is visible in the feed rather than inferred from a log.

The packaged status extension (`extensions/teamwork-status.ts`) renders that feed as a
bounded widget - at most 12 lines and 100 columns, one line per lane, busy rows
before idle, every idle instance collapsed into one counted line - and a footer
status line with the busy/total count. It refreshes every 5 s, is silent when no
engine is found, and `/teamwork-status` toggles it. It imports only `node:`
built-ins and the host's own packages, so installing it adds no dependency, and
removing it changes nothing in the protocol.

## 7. The agent mailbox

An agent that needs another agent to do, check or answer something sends a
message. It is queued, prioritised and delivered in the recipient's next lane
packet:

```console
$ teamwork message send --from Reviewer-1 --to Developer-2 --priority high \
      --subject "T-0131 needs the repro line" --task T-0131
$ teamwork message inbox --for Developer-2
$ teamwork message take M-0001 --for Developer-2 --by Developer-2
$ teamwork message done M-0001 --for Developer-2 --by Developer-2 --result "<evidence>"
```

`urgent` is the only priority that preempts: the supervisor stops the recipient's
lane, marks its task `paused` with the message id, runs a mailbox lane that drains
the queue, and `lane resume <T-id>` puts the task back. `high`, `normal` and `low`
wait for the recipient's next read, so a message never interrupts a step. `take`
makes exactly one lane process a message, which is what stops two instances of the
same role from doing the work twice.

Use it for a review finding the author must act on, a fact another role holds, an
interface change that invalidates a peer's work, or a hand-off. It is not a task
queue (`task add`), not a progress log (the worklog) and not a channel to the user
(only the CEO reports).

## 8. Token economy

The team's own startup read is a measured number, not a feeling:

```console
$ teamwork harness budget                 # per-instance bytes against the cap
$ teamwork harness budget --recallable    # what load never prints
$ teamwork throughput                     # surface bytes with latency and rework
```

The cap is `AlwaysOnBudgetKb` (122880 B per instance). When a row is over, the
surface is trimmed - never the cap raised. Three mechanisms keep it true:

| Mechanism | What it saves |
|---|---|
| The memory index | `load` prints a capped index block instead of every memory entry; the entries stay on disk and `recall` reads them on demand. |
| The `ctx://` tree | L0/L1/L2 levels let a lane read a summary or a record instead of a file; `context find` answers a question without loading `Archive.md`, `Decisions.md` or a task queue. |
| Read by id | `archive --task T-ID`, `decision list`, `trace T-ID` and `board` answer the question the agent actually asked. A whole `Archive.md` is roughly 0.63M tokens against a ~0.11-0.15M startup. |

A lane's own budget follows its unit: 10 tool calls and 10 minutes for prose, 16
and 25 for code, 24 and 40 for a security/release/data unit. `LaneToolBudget` in
`Settings.json` overrides the tool-call side for every unit when set.

## 9. Day-two checks

| Question | Command |
|---|---|
| Is the team actually moving? | `teamwork board`, `teamwork throughput` |
| Are lanes colliding or duplicating work? | `teamwork coordination --strict` |
| Is the review queue the bottleneck? | `teamwork review --queue` |
| Is any accepted deliverable unarchived? | `teamwork audit` |
| Would the team stop now? | `teamwork loop` |
| Is anyone idle and holding a seat? | `teamwork instance list`, `teamwork pulse` |
| Close the idle seats and release them | `teamwork instance prune --keep-required` |

The stop condition is mechanical: `loop` prints `STOP` only when every acceptance
criterion is verified, every required test layer passed, no review is open and the
chain verifies. `audit` is the human-facing sweep that must also come back clean
before the CEO reports completion.
