# Concurrency and reuse

Owner: CEO.

Reference for the /teamwork skill. Loaded on demand; `SKILL.md` keeps the
operating procedure.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md) | [Coordination](Coordination.md)

## Concurrency budget and resource reuse

Run everything as parallel as the providers allow, never past their caps.

| Provider | Concurrent agents | Use it for |
|---|---|---|
| Ollama Cloud | 64 | focused reasoning lanes: architecture, review, disputes, analysis |
| DeepSeek official API | ~2500 | wide independent fanout: many developer/tester/designer sub-tasks, bulk docs and research |

Caps live in `.pi/Teamwork/Teams/<Team>/Settings.json` and are overridable with
`TEAMWORK_PROVIDER_LIMITS="ollama-cloud=64,deepseek=2500"`.

### Slots are leases

Every model-heavy task holds a lease in `.pi/Teamwork/Teams/<Team>/Runtime/Slots/<provider>/`.
Leases expire after `TEAMWORK_SLOT_TTL_MINUTES` (90) so a crashed lane cannot
leak capacity.

```sh
teamwork.py slot acquire --agent developer-3 --provider deepseek --task T-0012
teamwork.py slot renew   --agent developer-3          # every ~60 min on long work
teamwork.py slot release --agent developer-3
teamwork.py slot list                                  # used / cap / free per provider
teamwork.py slot reap                                  # expire dead leases
```

At the cap, `slot acquire` fails with exit 3 instead of blocking. The lane then
does work that needs no slot (read, plan, review a peer's output), fans out on
another provider, or waits for a lane to release - it never stalls the team.

### Plan the parallelism

```sh
teamwork.py parallel
# - focused reasoning lanes (ollama-cloud): 7 free
# - bulk fanout lanes (deepseek): 2496 free
# - start up to 7 new lane(s) now (ready tasks: 12)
# - 3 lane(s) already hold a slot: hand the next task to a running lane first
# - independent sub-tasks only: one writer per file
```

The CEO uses this before every dispatch round: fill every free slot with
independent ready work, and scale instances of **any** role - `developer-N`,
`tester-N`, `reviewer-N`, and equally `architect-N` or `cto-N` - to the available
capacity rather than to a fixed number (`teamwork.py instance add <role> --count N`).
Instances of one role share its memory and queue, and the memory lease
(`memory claim <role> --by <instance>`, `references/State.md`) keeps exactly one of
them revising that memory while the rest read.

### The lane runtime: the engine starts the lanes itself

`swarm run` is the supervisor. It needs no host plugin: the engine starts each
lane as a detached child process (`teamwork.lanerun` wrapping a host CLI or a
`LaneCommand` template), records it under `Runtime/Lanes/`, and reconciles it from
that record afterwards.

| Piece | Path / command | What it carries |
|---|---|---|
| packet | `Agents/<Instance>/Runs/<run>.md` | the assignment, charter, exact commands, budget, result contract |
| record | `Runtime/Lanes/<run>.json` | agent, task, provider lease, pid, deadline, outcome |
| outcome | `Runtime/Lanes/<run>.outcome.json` | written by the wrapper: exit code, `timeout`, or `interrupted` |
| log | `Agents/<Instance>/Runs/<run>.log` | the lane's whole output, tailed with `lane logs` |

A **wave** is computed from the board at the moment it starts - ready tasks by
priority, unclaimed reviews, free provider slots, unfinished assignments - so the
next unit of work is decided from records, never from a plan written in advance.
Its **size** is measured, not requested: each unit weighs 1 (prose), 2 (code) or 3
(security/release/data, plus 1 for a bug), the wave runs `ceil(weight / 3)` lanes,
and that number is re-derived every wave and bounded by the free provider slots and
`LaneMax` (default 8). A lane's budget follows the same profile: 10 tool calls and
10 minutes for prose, 16 and 25 for code, 24 and 40 for a deep unit (scaled from
`LaneMinutes`, default 25). Scale changes are printed and recorded (`swarm.scale`):

```text
## complexity (score 6 -> moderate)
- ready: 3 task unit(s) (standard 3) from 1 queue(s)
- assigned: 0 unit(s) claimed with no live lane
- policy: up to 2 lane(s) this wave, bound by the complexity score (LaneMax 8);
  budget per unit: standard 16 call(s)/25m
```

Two rules keep the sizing honest: a claim the board already made with **no live
lane** behind it is adopted for that instance (that is what makes `pulse --commit
--spawn` one command), and an assignment is retried at most `LaneAttempts` times
and never re-adopted after a lane has spent an attempt - the measured failure was
a supervisor that re-planned one stalled task for 783 waves.

```sh
teamwork.py swarm run                 # one async wave, then return (--wait drains)
teamwork.py swarm run --dry-run       # the measured policy + next wave, start nothing
teamwork.py pulse --commit --spawn    # one async wake: reconcile, dispatch, return
teamwork.py swarm run --lanes 6       # cap the policy at six lanes
teamwork.py swarm run --fixed --lanes 4 --minutes 90 --poll 5
teamwork.py lane status --live        # what is running right now
teamwork.py lane logs L-0007 --lines 60
teamwork.py lane stop L-0007 --reason "superseded by L-0008"
teamwork.py lane reap                 # reconcile, free slots, recycle finished seats (--keep opts out)
```

- **One lane, one assignment.** A wave hands one unit to each idle instance
  round-robin and fans the rest out; a second unit in one run stays the CEO's
  `LANE_WIP` choice, so no queue piles onto one lane.
- **Dispatch is asynchronous by default.** `swarm run` and `pulse --commit --spawn`
  start the wave and return; every lane is a detached process that runs
  independently, and the next wake reconciles and refills. `--wait` is the batch
  drain (and `--waves N` implies it) - for CI, never for the live loop.
- **A provider lease is taken with the process** and released when it ends, so the
  cap in `Settings.json` bounds concurrent lanes without a second bookkeeping path.
- **A budget is enforced, not requested.** `LaneMinutes` (default 25) is a hard
  wall clock: the wrapper terminates the child and records `timeout`.
- **Progress is read from the board.** `LaneAttempts` (default 2) bounds retries of
  an assignment that left no self-check, PR or status change; past the budget the
  claim stays and the CEO decides. An exit code is never a substitute for a record.
- **Reviews become lanes.** A deliverable in `review` is claimed for a Reviewer
  instance in the next wave; the reviewer lane claims, verdicts, and its pass
  merges - the same gate, one process further out.
- **A finished job leaves nothing staffed.** `lane reap` retires the instance of every
  lane that ended and holds nothing else (move-only, record repointed), so the seat
  is recycled without a separate prune; the pulse fold does the same on each wake.
- **State survives the supervisor.** No live object is required: `lane reap` and a
  re-entered `swarm run` resume from `Runtime/Lanes/`.

`pulse --commit` is the one-shot dispatch (claim the plan into the queues);
`swarm run` dispatches the next wave from the same board and obeys the same caps.
Neither blocks by default - `--wait` is the batch drain - so a team can mix them
freely and no lane waits on another.

### Work-in-progress, not lane count, is the throughput

A lane that holds one task and waits for its review is idle capacity. The engine
therefore schedules on **capacity**, not on idleness:

| Concept | Default | Where |
|---|---|---|
| `LANE_WIP` - units one lane may hold (`doing` + `selfcheck`) | 2 | `engine.LANE_WIP` |
| Reviewer claims per lane | 1 | `review --claim` lease |
| Provider capacity | `Settings.json` (`ollama-cloud` 64, `deepseek` 2500) | `parallel`, `pulse` |

`task next <lane> --capacity N` claims N executable tasks at once; `pulse
--commit` tops every lane back up to its limit and refuses to plan more work than
there are free provider slots, printing the shortfall. A claim that is still live
blocks its lane; an expired claim is open for take-over, which is exactly what the
next pulse hands out.

### Stream the dependencies

`deps: role:T-id` waits for `done` and is the slowest possible edge. Two earlier
release points exist and should be used for every contract-shaped dependency:

| Dep form | Releases when | Use it for |
|---|---|---|
| `role:T-id@started` | the owner has picked the task up | shadow work, fixtures, environment setup |
| `role:T-id@review` | the work is submitted for review | testing and docs against a frozen interface |
| `role:T-id` (default) | the task is `done` and merged | anything that needs the merged artifact |

Using `@review` on every interface dependency is what lets the tester, the writer
and the next developer start in the same hour rather than after a full review
cycle.

### Reuse before you recompute

- Reuse a **running lane** before spawning a new one - the teammate already holds
  its memory, role and context.
- Reuse **evidence**: if a verification already passed on the same revision, cite
  it (`BUILD ECONOMY`) instead of re-running.
- Reuse **research and artifacts**: read global memory, long-term memory and
  `docs/Team/` before producing anything new; update in place, never duplicate.
- Reuse **build/test caches**; never rebuild from scratch for a clean slate.
- Reuse **the same artifact across lanes**: a frozen interface, fixture or script
  is shared, not re-created per task.
- Deduplicate before dispatch: `teamwork.py audit` flags near-identical tasks.

### Parallelism rules (non-negotiable)

- One writer per file/worktree. Concurrency never means two agents editing the
  same file.
- Only independent tasks run together; dependent tasks queue on their `deps`.
- The Reviewer, the Project Manager and the CEO are lanes too - keep them fed.
- **Review concurrency is the number of lanes, not the depth of the queue.**
  `pulse --commit` fans unclaimed deliverables out one per idle Reviewer lane and
  records a `review.claim` lease on each (`ReviewLeaseMinutes` base, default 20
  min, scaled by the review profile: ×1 fast, ×2 standard, ×4 deep, capped by
  `ReviewLeaseMaxMinutes`): the holder counts as busy, another lane is refused
  while the lease is live, a verdict or `--release` clears it, `--renew` extends
  it, and an expired lease is open for take-over. The base is deliberately shorter
  than the provider-slot TTL (`SlotTtlMinutes`, 90 min): a dead Reviewer must not
  freeze a deliverable for a slot lifetime, while a deep review is not taken over
  mid-flight by a lease sized for prose. Staff at least `reviewer-1` and
  `reviewer-2`, add a lane when the unclaimed queue is deeper than twice the lane
  count, and never stack the backlog on one lane.
- **Review has a profile and a packet.** The profile is inferred from the diff
  (fast for prose-only, deep for security/release/data/workflow, standard
  otherwise); `review <role> <T-id> --packet` prints it with the diff, the author's
  self-check and the exact gate set. The queue sorts by priority then age and
  prints the capacity line.
- Never exceed a provider cap to "go faster": the extra lanes fail, and the
  failure costs more than the parallelism gains.


## Per-agent model configuration

The skill does **not** ship a model and does not call an LLM API itself. Each
agent runs through the host's own API, so the model is a property of the *agent*,
not of the project, and every lane can pick one independently:

```sh
teamwork.py model set reviewer   --provider anthropic --model <strong>   # role default
teamwork.py model set developer-1 --provider deepseek --model <cheap>   # instance override
teamwork.py model get developer-1
teamwork.py model list
```

- An **instance** setting wins over the **role** default; an unset agent uses the
  host's own default and records `unset`.
- Give the reasoning-heavy lanes the stronger model (Reviewer, Architect,
  Security Auditor) and the mechanical ones a cheaper or faster one (bulk edits,
  formatting, link checks). Cost and latency are a per-lane choice, not a global one.
- A model change is a recorded act (`Settings.json` + the ledger); the CEO sets the
  lanes at intake, and an agent never changes another agent's model.
- Model choice never changes the protocol: the evidence gates, the two-stage
  review and the ledger hold whatever model produced the work.

### Automatic cost-aware routing

```sh
teamwork.py model auto            # dry run: the plan, per lane
teamwork.py model auto --apply    # write it into Settings.json
teamwork.py model auto --json
```

`model auto` reads the *runtime environment* - which agent host is running (Pi,
Claude Code, opencode, Codex, Cursor, Gemini CLI) and which model that host already
exposes - and routes **the strongest available model to the lanes where a mistake
is expensive** (Reviewer, Architect, Security Auditor, CEO, CTO) and **the economy
model to the mechanical lanes** (developers, testers, writers, formatting, link
checks). Quality where it compounds, cheapness where it does not.

- It never invents a model id: `TEAMWORK_MODEL_STRONG` (or the host's own
  `ANTHROPIC_MODEL` / `PI_MODEL` / `OPENCODE_MODEL` / ...) supplies the strong tier,
  `TEAMWORK_MODEL_ECONOMY` the cheap one, and a lane with neither is reported as
  `unset` together with the variable to set.
- `--apply` is explicit: the plan is a dry run by default, and applying it is
  recorded in the ledger.
- Re-run it when the host or the budget changes; it is idempotent.
- `TEAMWORK_AGENT_HOST=claude|pi|opencode|codex|cursor|gemini` overrides
  detection when the markers are ambiguous (CI, wrapper scripts).
