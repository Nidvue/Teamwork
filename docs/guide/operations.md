# Operations - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Quickstart](quickstart.md) · [Usage patterns](usage.md) · [How it works](how-it-works.md) · [Features](features.md) · [CLI reference](cli.md)

How to run a team that is already staffed: keep it inside provider caps, keep its
memory coherent, resume it after a crash, prove its audit trail and route its
models. Every command here is also listed, with every flag, in the
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

## 6. Day-two checks

| Question | Command |
|---|---|
| Is the team actually moving? | `teamwork board`, `teamwork throughput` |
| Are lanes colliding or duplicating work? | `teamwork coordination --strict` |
| Is the review queue the bottleneck? | `teamwork review --queue` |
| Is any accepted deliverable unarchived? | `teamwork audit` |
| Would the team stop now? | `teamwork loop` |

The stop condition is mechanical: `loop` prints `STOP` only when every acceptance
criterion is verified, every required test layer passed, no review is open and the
chain verifies. `audit` is the human-facing sweep that must also come back clean
before the CEO reports completion.
