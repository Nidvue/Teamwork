---
name: teamwork
description: "Nidvue Teamwork - run a user prompt to completion with an autonomous multi-agent company: CEO, CTO, COO, CFO, Architect, Product Manager, Project Manager, Designer, Release Engineer, Technical Writer, Data Engineer, Developer(s), Tester(s), Reviewer and Security Auditor. Use when the user invokes /teamwork, asks for a team of sub-agents with roles, wants an org chart of agents that plans, builds, tests and iterates until the goal is met, or wants long-running parallel work with per-agent memory. The user talks only to the CEO; every other agent communicates internally."
compatibility: "python3 3.11 or newer on PATH - the engine is stdlib-only, so there is no pip install and no venv; git is required for every branch, commit and PR operation."
---

# Nidvue Teamwork - `teamwork` skill

> **Nidvue Teamwork** is the product brand; `teamwork` is the command, package and
> workspace identifier. This is a **skill**, not a standalone application: the
> engine is a stdlib-only tool the skill calls, and every agent runs through the
> host's own LLM API with a model configured per agent (`references/Concurrency.md`).

Turn one prompt into a functioning, self-organising team that keeps working until
the goal is verified. The user talks **only to the CEO**. The CEO decomposes the
goal, spawns the roles, and keeps developer/tester/designer lanes running in
parallel. Nothing is ever declared done on an unverified claim.

## Usage

```
use the teamwork skill: <prompt>       # any host: the skill is loaded by its description
/teamwork <prompt>                     # where the host maps skills to commands
/teamwork --team <Name>                # use a specific per-team tree
```

Anything else after the prompt is an instruction to the CEO in plain language
("resume the existing team", "only staff developer and reviewer", "four
developers"): the CEO honours it when writing the roster and `Plan.md`. Only
`--project` and `--team` are CLI flags.

The prompt is the product brief. If it is genuinely ambiguous in a way that
changes what gets built, the CEO asks **one** consolidated round of questions and
then proceeds on recorded assumptions.

The skill is **agent-agnostic and remote-agnostic**: it runs on any agent host
that loads a skill directory, or that can run `teamwork.py` and read `AGENTS.md`,
and against GitHub, GitLab, Bitbucket, Gitea/Forgejo, Azure DevOps or a bare
server. The protocol is identical; only the six host operations and the integrity
settings are adapted (`references/Adapters.md`, `references/Remotes.md`).

## Non-negotiable contract

1. **One voice to the user.** Only the CEO reports, asks, and accepts. No other agent contacts the user.
2. **Run to completion.** Work ends only when every acceptance criterion is verified by executed evidence. Blocked is not done; idle with executable work left is a bug.
3. **Evidence or `UNVERIFIED`.** No claim about code, tests, CI, or the world without a path/command/revision/result. The engine refuses `done` without recorded evidence.
4. **Independent parallel lanes.** Freeze interfaces first, then developer, tester and designer lanes run concurrently against the same contract.
5. **Code, then tests, then docs.** Documentation never blocks code or tests.
6. **Role-shared state, private workspace.** Memory and the task queue belong to the ROLE and are shared by its instances; only charter, worklog, inbox, artifacts, reports and scratch are private.
7. **Red lines are absolute.** Unsafe, illegal, irreversible or fabrication actions stop the lane and escalate to the CEO (`references/Evidence.md`).
8. **Nothing unnecessary is kept.** No duplicate docs, scratch, build output or secrets in the repository.
9. **Style is automated.** Each role runs the language's canonical formatter, linter and type checker (Python: `ruff format` + `ruff check` + `mypy`); the fixer runs before the commit and the checker gates the merge. Never hand-format, never add a competing config, never weaken a rule to pass (`references/Engineering.md`).
10. **Names are deliberate.** Team directories are PascalCase; file names follow the ecosystem (docs `Architecture.md`, components `ButtonGroup.tsx`); Python modules stay `lower_snake_case`; tool-mandated files are never renamed.
11. **History is minimal and modular.** Every commit message is **exactly one line** - `<type>(<area>): <summary>`, compact but informative, no body or trailers; the task, goal and evidence live in the task record and the ledger. Commit while you work, then rebase and squash before review: one coherent change-set, `wip`/`fixup` squashed, rebased onto the default branch, one commit per task before the merge. The Reviewer merges locally (`git merge --no-ff`); `pr merge --squash` is the one-commit path. Never rebase or force-push shared history.
12. **Each agent's model is its own.** The skill ships no model and calls no LLM API; the engine configures a model per role and instance (`model set|get|list`). `model auto --apply` reads the host's model and applies cost-aware routing: strongest on decision lanes, economy on mechanical lanes; set `TEAMWORK_MODEL_ALT` when two verification lanes are staffed. Model choice never changes the protocol, the gates, the review or the ledger (`references/Concurrency.md`).
13. **Warnings are errors.** The toolchain fails on them by configuration, the cause is fixed, and a third-party warning is suppressed narrowly with a reason. CI annotations count as warnings.
14. **Independence is structural.** Verification lanes do not share a model when a second is available; a Reviewer records its own run, never the author's line; one task owns one branch; duplicate work is a defect.
15. **No lane wars.** Never deny a peer a resource - no killing its process, deleting its worktree, starving its lease or overwriting its files. Resolve a conflict by a measurable contest or the CEO; `reclaim` refuses a live lane.
16. **Consensus is not evidence.** A single source is provisional, a unanimous zero-finding run is sampled, and lowering a gate to agree is collusion (`references/Coordination.md`).
## The org

| Role | Instance names | Charter |
|---|---|---|
| CEO | leader session (not spawned) | `roles/ceo.md` |
| CTO | `cto` | `roles/cto.md` |
| COO | `coo` | `roles/coo.md` |
| CFO | `cfo` | `roles/cfo.md` |
| Architect | `architect` | `roles/architect.md` |
| Product Manager | `product-manager` | `roles/product-manager.md` |
| Project Manager | `project-manager` | `roles/project-manager.md` |
| Designer | `designer-1..N` | `roles/designer.md` - also owns every visual asset, raster **and** vector (recorded in `Design.md`), and decides what is needed |
| Developer | `developer-1..N` | `roles/developer.md` |
| Tester | `tester-1..N` | `roles/tester.md` |
| Release Engineer | `release-engineer` | `roles/release-engineer.md` - also owns repository and CI integrity: branch protection, required checks, merge strategy and protected tags, on any git host |
| Technical Writer | `technical-writer` | `roles/technical-writer.md` |
| Data Engineer (conditional) | `data-engineer` | `roles/data-engineer.md` |
| Reviewer | `reviewer-1..N` (several may run **in parallel**) | `roles/reviewer.md` - deep independent second review of every deliverable from one shared queue; one claim per deliverable; only a Reviewer may pass/merge, and never the author |
| Security Auditor | `security-auditor` | `roles/security-auditor.md` |

### Who reports to whom

```text
CEO - user interface, arbitration, final acceptance
|- CTO - technology strategy, engineering standards, the build/release policy
|  |- Architect, Developer-1..N, Tester-1..N, Release Engineer, Data Engineer
|- COO - process, risk, throughput
|  |- Project Manager
|- Product Manager - research, requirements, acceptance criteria
|  |- Designer, Technical Writer
|- CFO - cost, budget, unit economics
|- Reviewer-1..N - independent review, the only pass/merge right
`- Security Auditor - audits everyone, CTO included
```

One parent per role, and the parent owns the standard the child is judged by.
**Escalate up your own line first** (`Architect` -> `CTO` -> `CEO`); go sideways
only for a fact or artifact a peer holds. Three roles stay directly under the CEO
because their job is to disagree with everyone else: the Reviewer merges the work
it reviews, so no reviewed lane can manage it; the Security Auditor audits the
CTO; the CFO holds the cap that binds the team. `ROLE_PARENT` in
`src/teamwork/config.py` is the single source of truth - `teamwork.py map` renders
the tree and `tests/unit/test_reporting_hierarchy.py` fails when a doc drifts.

### Staff the smallest roster that still closes the gates

Start from a tier instead of listing fifteen roles. `init --roster slim` is the
default; `--agents` overrides it for a roster you name exactly.

| Tier | Instances | Startup read |
|---|---|---|
| `slim` (default) | 7 | 300 kB |
| `standard` | 10 | 412 kB |
| `full` | 17 | 667 kB |

Startup read = every instance's `AGENTS.md` plus its own role charter, summed -
2.2x what `slim` costs. A role earns a seat only if it owns a deliverable, a test
layer and a decision right no other role holds; everything else is a **lane, not a
role** (no charter, no queue, no memory set). Which role a slim tier drops and where
that work goes: `references/Roles.md`.

Two rules keep a slim roster honest:

- `tests plan` only requires the layers of **staffed** roles.
- The tribunal never falls below two members: with no CTO/CFO staffed the Reviewer
  takes the neutral seat (`TRIBUNAL_MIN_SIGNERS`), and **a party to a dispute can
  never rule it**. A vacant manager escalates to the CEO for the duration.

`init` warns when a gate-critical role is missing. **The Reviewer is not optional**,
and two Reviewer lanes are the minimum: the queue fans one deliverable per lane, a
re-submitted fix is re-reviewed as a delta, and a second lane gives a sampled or
high-risk deliverable an independent verdict. A pass merges - the lane that verified
the revision lands it.

## Workspace layout

Two separate worlds: the team's own tree is **hidden** and local; project output is committed. All team-created names are **PascalCase**.

```text
<project>/
├── AGENTS.md                         # team constitution (managed block, auto-loaded)
├── .agents/skills/tw-<name>/SKILL.md # team skills
├── docs/Team/                        # Project, Plan, Board, Archive, Decisions,
│                                     # Architecture, Research, Design, Risks,
│                                     # Costs, Release, AuditManifest.json/.md
├── <code/> <tests/>                  # committed project output
└── .pi/Teamwork/Teams/<Team>/        # hidden, gitignored team tree
    ├── TeamMap.md  Settings.json  Criteria.md  Tests.md  TestPlan.md
    ├── Reviews.md  Disputes.md  Skills.md  Knowledge.md  Ledger.jsonl
    ├── Global/                       # CEO-owned GlobalMemory.md (+ Archive)
    ├── Roles/<Role>/                 # SHARED: Short/Long/Archived memory,
    │                                 # Role.md, Lessons.md, TaskQueue.md
    ├── Agents/<Instance>/            # private: StartHere, WorkLog, Inbox,
    │                                 # Artifacts/, Reports/, Scratch/
    └── Runtime/                      # LedgerHead.json, Locks/, Worktrees/, Slots/
```

Every team gets its own `<Team>` tree, named after the project or by `--team`/`TEAMWORK_TEAM`, so several teams in one repository never collide. Memory and the queue belong to the ROLE: `Developer-1` and `Developer-2` share `Roles/Developer/` and claim from one queue.

Any role scales with `instance add <role> --count N`. Only one instance of a role revises its memory at a time: `memory claim <role> --by <instance>` takes the pen, `memory release` returns it, and a single `remember` holds it only for its own duration. A long lease is contested, not waited out: a peer runs `memory contest <role> --by <instance> --reason '<why>'` and the **CTO** rules with `memory extend` or `memory revoke`. Detail: `references/State.md`.
## Bootstrap procedure (CEO)

Run these in order. Use `SKILL` for this skill's directory.

### 1-4. Intake, workspace, plan and staffing

These run once per project, so their detail is on demand: read
[references/Bootstrap.md](references/Bootstrap.md) before you create a
workspace, freeze interfaces or restaff. The order is fixed:

1. **Intake** - the brief restated as objective, non-goals and constraints, and
   every acceptance criterion as a record.
2. **Workspace, repository, constitution** - the tree, the managed block, the
   team settings.
3. **Plan and freeze interfaces** - the parallelism gate; no squad starts on a
   moving interface.
4. **Staff and dispatch** - the smallest roster that closes every gate.

Then run the loop (section 5) and close (section 6).

### 5. Run the loop

One iteration is: re-plan -> dispatch -> work in parallel -> independent review ->
rework -> integrate. Repeat until `teamwork.py loop` reports STOP.

- Teammates auto-claim the highest-priority unblocked task; when one finishes it
  submits for review and takes the next.
- **Every deliverable is second-reviewed by the Reviewer**, independently: code,
  tests, docs, design, research, cost models, risk registers. A fail returns it to
  the owner with findings; the owner fixes, re-checks and re-submits. Failures are
  counted: at 3 the Reviewer must open a dispute so the tribunal rules
  (`references/Dissent.md`), and `loop` blocks STOP until it does.
- **Every agent tests its own layer** (`goal` CEO, `requirements` Product Manager,
  `plan` Project Manager, `tech` CTO, `release` Release Engineer, `data` Data
  Engineer, `process` COO, `cost` CFO, `system` Architect, `ui` Designer, `docs`
  Technical Writer, `unit` Developer, `integration` Tester, `acceptance` Reviewer,
  `security` Security Auditor). `tests plan` shows the matrix and gaps; `loop`
  blocks STOP while a required layer is missing or failing.
- **Review is a parallel lane.** `reviewer-1..N` claim different deliverables from
  the shared queue; one claim per deliverable, high-risk work gets two Reviewers,
  nobody reviews their own work, findings union, and a pass is the merge.
- The CEO keeps the interface contract stable and arbitrates; the Project Manager
  chases stalled tasks and refreshes `Plan.md`/`Board.md`; the COO keeps `Risks.md`
  honest; the Product Manager keeps `Research.md` current.
- The team is self-managing: the CEO resolves internal conflicts and disputes
  without the user, who hears only an authorization, a goal/scope/budget change, a
  blocking ambiguity, or the final report.

Before every close:

```sh
python3 "$SKILL/scripts/teamwork.py" criteria list && python3 "$SKILL/scripts/teamwork.py" tests plan
python3 "$SKILL/scripts/teamwork.py" board && python3 "$SKILL/scripts/teamwork.py" review --queue
python3 "$SKILL/scripts/teamwork.py" coordination --strict && python3 "$SKILL/scripts/teamwork.py" audit
python3 "$SKILL/scripts/teamwork.py" links && python3 "$SKILL/scripts/teamwork.py" pulse --commit
python3 "$SKILL/scripts/teamwork.py" parallel && python3 "$SKILL/scripts/teamwork.py" loop
```

Report to the user at milestones: what changed, evidence, blockers, next.

### 5a. Parallelism is the default, not the reward

A team that runs one lane at a time is a slow single agent with extra records.

| Rule | Mechanism | Why |
|---|---|---|
| A lane holds more than one unit | `LANE_WIP` (2): one deliverable in review plus the next in progress | a lane waiting for its own review is idle capacity |
| `pulse` fills capacity, not idle lanes | it assigns `LANE_WIP - held` per lane | one-task-per-idle-lane capped the team |
| A dependency can release early | `deps: role:T-id@review` or `@started` | the downstream lane needs a frozen interface |
| Reviews are the exception | one claim per Reviewer lane; run several lanes | a deep review is not divisible |

**Delegation is recursive, and the CEO does not do a lane's work.** The CEO's output
is the decomposition, the dispatch, the arbitration and the final claim; every unit
goes to a lane. A Team Leader lane spawns its squad, and a lane whose slice will not
fit its budget splits it into sub-tasks and dispatches them. The chain ends at a
small task one lane can finish and get verdict-ed inside its budget, and at an
independent verifier: no lane reviews, tests or merges its own work, and every
deliverable gets its author's self-check, a different role's review and its test
layer run by the owning role.

**The roster follows the work, so no single lane is the bottleneck.** `pulse
--commit` (and `swarm run`) plans instances from the ready work - one lane carries
`LANE_WIP` units and one Reviewer takes one deliverable - bounded by
`SCALE_PER_ROLE_CAP` (4) per role, `SCALE_MAX_ADDS` (6) per wake, `LaneMax` and the
free provider slots. `--no-scale` dispatches to the current roster; an
`observe`/`off` wake adds nothing. The other half is folding: an idle seat is
retired (`instance prune`) and restaffed on demand.

Capacity is bounded by the provider caps in `Settings.json`, never by the lane
count: Ollama Cloud 64, DeepSeek 2500, OpenAI 64, Anthropic 64 and 32 default
concurrent lanes. `pulse` defers assignments beyond the free-slot count and prints
the shortfall; the measured anti-patterns are in `references/Concurrency.md`.

### 5b. Keep the lanes full: the CEO pulse

After dispatching, the CEO **re-wakes on an interval**, finds idle lanes, and hands
them runnable work:

```sh
python3 "$SKILL/scripts/teamwork.py" pulse --commit --interval 5
```

`pulse` prints idle lanes, ready work and a dispatch plan; `--commit` applies it and
pins review claims so lanes never review the same deliverable. Exit 3 means
"nothing to dispatch". A review claim is a renewable profile lease
(`ReviewLeaseMinutes`, default 20; x1 fast, x2 standard, x4 deep), separate from
the 90-minute slot TTL: verdict with `--result`, extend with `--renew`, or
`--release`.

**The engine runs the lanes; no host plugin is needed, and the wave is sized by the
work.** `swarm run` measures what is in hand from the records - every ready task and
unclaimed review, weighted 1 prose / 2 code / 3 security-release-data, +1 for a bug
- and starts `ceil(weight / 3)` lanes, bounded by the free slots and `LaneMax`. It
re-measures every wave, and each lane's budget follows its unit: 10 tool calls/10
min prose, 16/25 code, 24/40 deep. An unfinished assignment gets a bounded retry, a
claim with no live lane is adopted, a deliverable in `review` becomes a Reviewer
lane, and `lane status|logs|stop|reap` is the inspection surface:

```sh
python3 "$SKILL/scripts/teamwork.py" swarm run --dry-run   # the measured policy, start nothing
python3 "$SKILL/scripts/teamwork.py" swarm run             # one async wave, then return (--wait drains)
python3 "$SKILL/scripts/teamwork.py" pulse --commit --spawn  # one async wake: dispatch and return
python3 "$SKILL/scripts/teamwork.py" lane status --live
```

**The default is async/streaming: `swarm run` dispatches the next wave and returns -
it never waits for a lane.** Each lane is a detached process; the next wake
reconciles the finished ones and refills, so the supervisor is never the bottleneck
and no lane waits on another. `--wait` is the batch mode (`--waves N` implies it);
use it for CI or a one-shot drain, not the live loop. `--lanes N` caps the policy,
`--fixed --lanes N` turns it off, and the `## complexity (score N -> band)` line
shows the factors.

An instance is **busy** only while it holds a slot, a `doing`/`selfcheck` task or a
live review claim; everything else is idle and must be fed. An idle seat with
nothing to feed it is folded: `pulse --commit` retires the surplus, and
`instance prune` folds every idle instance in one move-only pass
(`Runtime/Retired/`, role memory and queue stay). The CEO is never folded;
`--keep-required` keeps one instance of each gate role. Interval: `PulseMinutes`
(default 5). The runtime and its settings: `references/Concurrency.md` and
`references/Adapters.md`.

### 5c. Push in stages, and certify both signals

- **Release Engineer - push after review, stage by stage.** Only the Release
  Engineer pushes, and only a revision the Reviewer passed with no open finding.
  **A stage ends with a push, not with a merge**: push each reviewed stage so the
  remote never drifts. Before the push, build, tests, `privacy_scan.py --tree
  --history` and the link check are green on exactly that revision; after it, watch
  CI and confirm green **on that SHA**. A red run is routed from the log (code ->
  Developer, test -> Tester, contract -> Architect, workflow/packaging/flake ->
  Release Engineer, scope -> CEO) and re-run. A code-scanning `error`/`critical`/
  `high` alert is red; `teamwork code-scanning --commit` files a `P0` task with the
  file's owner. Force-push and published-history rewrites need the CEO's
  authorization; tags and releases are the CEO's step.
- **Tester - certify local *and* CI.** Run the layers locally, then confirm the same
  result in CI on the pushed revision, job by job across the OS and Python matrix. A
  green local run with a red CI run is a failure, and so is the reverse; file every
  failure to its owner with the command, expected vs actual, log, SHA and run id.
- **CI triggers are path-filtered: code in, prose and media out.** Docs and images
  get a cheap docs workflow (link health, privacy scan, `mkdocs build --strict`);
  anything that ships always runs the full matrix. Keep the two lists in sync.
- **Everyone keeps the tree clean.** No explanatory comment
  (`scripts/check_comments.py` fails the gate), no commented-out code, no `TODO`
  without a tracked task; delete temp and stale files in the same task (`clean` for
  your lane, `--all` for its `Scratch/`); one canonical home per file.

Both duties are evidence: `tests plan` and the task record name the local result
**and** the CI run (id + conclusion) for the certified revision. Detail:
`references/Engineering.md`.

### 5d. Any agent host, any git host

- **Agent host.** The engine, workspace, criteria, two-stage gate, ledger and test
  matrix are host-independent. Only six
  operations need a mechanism - spawn a teammate, delegate one-shot work, message
  an agent, inspect state, re-wake on a schedule, close the team - and the engine
  provides all six itself: `lane start|list|status|logs|wait|stop|reap`, the
  `Inbox.md` mailbox, and `swarm run`. A
  host is only the CLI that turns a packet into an agent run; the launcher table,
  the `LaneCommand` template and the degraded modes are in `references/Adapters.md`.
  Name the operation, never a host tool. With no launcher the protocol still
  completes - one agent wearing the hats sequentially, with the same gates.
- **Git host.** The Release Engineer guarantees repository and CI integrity on any
  host: a protected default branch, **no force-push**, no deletion, required status
  checks on the exact revision, at least one non-author approval, the host merge
  button off - the Reviewer merges locally and the source branch is deleted
  (`pr merge --squash` is the one-commit path) - protected `v*` tags created only by
  the CEO, and least-privilege CI with no secret in the tree. Record the host's
  actual settings and re-read them to detect drift. Per-host mapping:
  `references/Remotes.md`.

### 5e. Keep the installed skill on the remote's `main`

The host loads a **copy** of the skill, so a copy that drifts from `origin/main` silently keeps reading an old protocol. `teamwork.py refresh` fast-forwards a checkout source and mirrors the bundle into the skills directory; `--check` reports drift and exits 1 when stale, `--dry-run` prints the plan. A dirty checkout is mirrored, never reset. Run it at startup and after every push, and reload the skill afterwards. Full behaviour: `references/Adapters.md`.
### 5f. Keep lanes decorrelated

Identical lanes make identical mistakes: same model, same context, same queue.

- `model auto --apply` with `TEAMWORK_MODEL_ALT` when two Reviewer, Tester or
  Security Auditor lanes are staffed; `coordination` reports `C-DIV-MODEL` when every
  verification lane shares one model.
- `coordination --strict` is the milestone gate: duplicate branch/task, echoed
  evidence, reviewer monoculture, abandoned PRs, merge collapse, slot starvation.
  `--commit` records it; exit 1 means a high finding is open.
- A conflict is resolved by a measurable contest or the CEO, never by denying a peer
  a resource. `reclaim` refuses a live lane; `--force <reason>` is only for a
  confirmed dead one.
- The Reviewer reads the artifact before the author's summary and records its own
  run; identical evidence is `C-TRUST-ECHO`.
- A user-facing deliverable is **shown** at the milestone.

Mechanisms: `references/Coordination.md`.

### 5g. Keep reviews fast

The Reviewer is the gate every lane waits on; its queue, not its depth, is the
throughput limit.

- `review --queue` sorts by priority then age and prints the profile, claim state and
  capacity. Add a Reviewer lane when the unclaimed queue is deeper than twice the
  lanes; a deep review is not divisible.
- `review <role> <T-id> --packet` gives the profile, changed files, self-check, gates
  and checklist in one screen; start there.
- The profile is inferred from the diff: `fast` for prose (link check, docs/contract
  tests, privacy scan), `standard` for code (suite, lint, type-check), `deep` for
  security/release/data/workflow. `task add --review-profile` overrides it.
- A claim is a **profile-aware renewable lease** (`ReviewLeaseMinutes`, default 20;
  x1/x2/x4), not the slot TTL. `review --next --by <lane>` claims and packets in one
  step; `--renew` extends; do not hold a claim while writing prose. `coordination`
  reports claim-to-verdict p50/p90 and expired claims.

### 5h. Verify once, credit the rest

Most of a slow review repeats work another role already did at the same revision.
Independence is about the **author**, not about repeating a peer: a recorded result
from another role at the revision under review is a fact to cite, and
`review --packet` lists it.

| Rule | What it means |
|---|---|
| one run per fact per revision | a recorded `tests run --rev` or CI run on the pushed SHA is not re-run; cite it with `--credit` |
| the irreducible core | requirement conformance, the reviewer's own `acceptance` layer, every `uncovered` criterion, one sampled credit |
| creditable | a `passing` record at this revision, by a role other than the author's, with the command written down |
| recorded, not implied | `--credit TS-0006` writes `credited: ...`; a stale, failing, author-role or unknown record is refused with the reason |
| read the machine verdict | lint, format, type-check, suite, links, privacy, security scan are read once; re-running a green record is `C-REVIEW-DUP` |
| a fix is a delta review | a fail stores the revision; re-review the delta, the failed criterion and one fresh credit |
| full re-review only on a contract change | a new deliverable, a frozen interface, a security/release/data/workflow path, or a larger diff |
| budget | fast 10 / standard 20 / deep 40 minutes; when spent and unverifiable, fail naming the missing evidence |
| batch the context | same author + area + profile may be one sitting - one claim and one verdict each |

`coordination` reports the credit ratio, delta re-reviews, `C-REVIEW-DUP` and
`C-REVIEW-NOCREDIT`. Every author records `--rev <sha>` and `--artifact`: an
unrecorded run is a run the Reviewer has to repeat.

### 5i. The throughput contract

Speed is a property of the structure, not of working harder. Measured on this
project's own trail at **one** ledger cut, `n=1615`: **44** review failures over
**66** review targets (one role + task), 26 needing more than one verdict and 11
three or more; verdict distribution 40/15/6/4/1. Two independent readings put
failures a local check could have caught at **16-24 of 44**, but the split is
**contested**, so the contract does not rest on it: every fail records whether the
author had a green `preflight` at that revision (`mechanical: no|unknown|n/a`),
measuring it prospectively. `teamwork.py throughput` re-reads the current cut.

| Rule | It forbids |
|---|---|
| one parent, one board | a second reporting line; three managers for one role |
| one feature, one team | a Team Leader owning two open features; two teams on one slice |
| one owner per artifact, one writer per file | two lanes editing one contract, board, charter or file |
| one verification per fact per revision | re-running a gate another role recorded green (5h) |
| one gate, one place | CI and docs running one check; the Reviewer repeating `preflight` |
| definition of ready | starting on a moving interface, a shared path, an in-flight dependency |
| definition of done | a done that is not preflight-green + independent pass + archived + merged |
| generated artifacts render at the merge | a board/archive render riding a feature branch |
| right-sized roster | one lane per task; a second Developer for a slice one can carry |
| small slices, short leases | a task that cannot be verdict-ed inside one lease - split it |

`preflight <role> <T-id>` turns rules 6-8 into one fail-closed command: identity,
commit count, every `@<sha>` exists and is reachable, the evidence and the newest
note name the **branch head**, `merge-tree` against the base is clean, board drift is
charged only to a board edit, and the project gate runs from `Settings.json` ->
`PreflightCommand` (`--run`). A fail records `mechanical`.

**Feature teams are live** (`references/Roles.md`, `teamwork.py feature
add|set|list|check`, contract in `Architecture.md` 13): one open feature per leader
and its squad, teams run in parallel, Architect and Project Manager are shared
services. `feature check` applies five rules - shared writable path, in-flight
dependency, one open feature per leader, owned-path shape, duplicate id - and a
feature cannot leave `proposed` without a frozen interface (`feature set <F-nnnn>
--state ready` refuses one). `preflight`, a review pass and the merge all run it.
The structure and the five rules: `references/Roles.md`.

### 5j. Learning is part of the work

A failure you do not record is one the team pays for twice.

- **A lesson (`L-`)** after a failed self-check or review, and after any mistake
  worth not repeating: the failure, the cause, the rule you now follow, the evidence.
  `lesson add` requires all four; `load` shows open lessons at every startup. Close
  it with the cheapest rung that stops it recurring: `lesson fix --check '<cmd>'`
  runs the command that now catches it (it must exit 0) or `--no-check '<why>'`
  records that the class is gone by design; prose alone is refused.
- **A `tw-` mistake skill** when the fix is a flow: `skill create --kind mistake
  --from-lesson L-nnnn` marks the lesson fixed, links both records and names the
  failure it prevents. A recurring finding with no skill behind it is a defect.
- **The skill library is managed, not just grown.** Every agent creates, updates,
  enhances, improves and **removes** skills over time. Every skill is
  **feature-unique**: search the library before creating, consolidate or merge
  overlap instead of duplicating, and delete a skill that is superseded or unused.
  A redundant or stale skill is a defect.
- **A knowledge record (`K-`)** for a durable fact, command or gotcha: statement,
  evidence, tags, importance 1-5 and a kind (`fact`, `experience`, `preference`,
  `gotcha`, `rule`). Search before asking, `touch` what you used, supersede rather
  than contradict. Never store a secret or personal data.

Both stores are team-local, never committed, written only through the commands:
`Roles/<Role>/Lessons.md` is role-shared, `Knowledge.md` team-wide. Classify a
finding first - tool defect, process, doc drift, governance or knowledge - and run
`tw-self-evolve` at every milestone close. A tool defect takes a code task with a
failing reproduction, never a lesson. Detail: `references/State.md`,
`docs/Team/Evolution.md`.

### 5k. The context tree

`ctx://` is one read-only view over memory, lessons, knowledge, skills, docs and
tasks; every node resolves to an existing file or record and no sidecar is written.
L0 is the one-line summary, L1 the record fields or child list, L2 the full record.
Use `context ls`, `tree`, `read <uri>`, `find "<query>" [--scope <uri>]`, `stats`,
`digest <T-id>`. Retrieve by id, never by whole file. For one file the same
discipline is `tw read <path> --query '<needle>'`: under 4 KiB it returns the
whole file, above it only the matching line ranges with `path:line` provenance
inside a byte budget, and `--lines`/`--full` are the verify and native fallbacks.
`context` never replaces `load`, the gates or the evidence rule. Detail:
`references/State.md`.

### 5l. Throughput and the token budget

- **Right-size the roster.** `slim` is the default; add an instance for a named
  deliverable, retire an idle one. Retirement is **move-only** to
  `Runtime/Retired/<Instance>/`; verify `git rev-parse HEAD` is at or after the
  move-only revision (`b9e5135`) first - a stale cut lost 102 artifact paths
  (`L-0001`).
- **Read by id, never by history.** `archive --task <T-id>`, `decision list`,
  `board`, `trace <id>` answer a question; a whole `Archive.md` is ~0.63M tokens
  against a ~0.11-0.15M startup, and `Decisions.md`, `Plan.md` and a `TaskQueue.md`
  are the same trap.
- **Make the first pass review-ready.** The self-check note answers the boundary and
  empty/duplicate/second-call case, the contract surface, concurrency/shared writes
  and the exact scope, each with a test or a reason. On a code task the Tester
  records the full suite once and the Reviewer cites it (`--credit`).
- **Keep the budget token-true.** `harness budget` measures what `load` prints;
  `--recallable` reports what it never prints. The cap is `AlwaysOnBudgetKb`
  (122880 B default); when a row is over, trim the surface, never raise the cap.
- **Split at the slice warning.** `preflight` warns past 6 files/300 lines (`fast`),
  12/600 (`standard`), 24/1200 (`deep`); split, or say why it is one contract.

`teamwork.py throughput` is the measured reader for latency, pass/fail, rework,
queue depth and surface bytes. Detail: `references/State.md`.

### 5m. The intern protocol

The model is an intern: introduce the work, give it one job, prove the job, and
remove every manual relay. Full text: `references/Roles.md`; the audit is the
`tw-team-designer` team skill.

| Rule | It forbids |
|---|---|
| no human relay | the user copying a fact between agents or re-stating repository state; record it (`attention add`) and automate it |
| teach once, encode it | a repeatable method living only in the conversation; `skill create`/`skill share` in the same task |
| least privilege, one job, one proof | granting every connector; every deliverable names its verifier and proof |
| onboard, then restate | planning before the agent restated goal, acceptance and non-goals |
| proactivity is a record | silent autonomy; an idle lane proposes one automation/risk via `attention add` or a task |
| routine hygiene | a schedule with no trigger, budget and stop condition |

Do not give a bot its own email or external accounts: that is external and
irreversible. Adopt the smallest team that reliably does the work, with a proof per
seat.

### 5n. Agents talk to each other: the mailbox

An agent that needs another agent to do, check or answer something sends a
**message**; it does not open a task and does not shout into a worklog. Messages are
queued, prioritised and preemptible, so a request never costs the recipient its
current work.

```sh
python3 "$SKILL/scripts/teamwork.py" message send --from <you> --to <instance> \
    --priority urgent|high|normal|low --subject '<one line>' [--body '<detail>'] \
    [--task <T-id>] [--reply-to <M-id>]
python3 "$SKILL/scripts/teamwork.py" message inbox --for <instance> [--all] [--json]
python3 "$SKILL/scripts/teamwork.py" message take <M-id> --for <instance> --by <you>
python3 "$SKILL/scripts/teamwork.py" message done <M-id> --for <instance> --by <you> --result '<what you did + evidence>'
```

| Priority | What it means | What the recipient does |
|---|---|---|
| `urgent` | the current assignment is displaced | the supervisor stops the lane, marks the task `paused` with the message id, runs a mailbox lane; `lane resume <T-id>` puts it back |
| `high` | before the next new task | read at the next step |
| `normal` | the default | read in order |
| `low` | when idle | read in order |

- **The queue is in the packet.** Every lane packet opens with `## Messages for
  you` in priority order, so the recipient sees its mail without polling;
  `message inbox` is the same list on demand.
- **A message never interrupts a step, a priority does.** `urgent` is preemption
  through the supervisor - the only component that owns process lifecycle.
- **One taker.** `message take` makes exactly one lane process a message; `message
  done` closes it with the result the sender reads.
- **The task is paused, not lost.** Preemption records `paused` with the message id;
  a paused task blocks `loop` until it resumes.
- **The trail is the ledger.** `message.send|take|done` and `lane.preempt` are
  ledger actions; the message itself lives in `Runtime/Mailbox/<Instance>/`.

Use it for a review finding the author must act on now, a fact another role holds,
an interface change that invalidates a peer's work, a hand-off. Not to assign work
(`task add`), not to report progress (the worklog), never to ask the user. Detail:
`references/State.md` and `references/Coordination.md`.

### 5o. Loops inside a node, the graph between them

A loop makes one unit correct without you; the graph decides which units exist, in
what order, and where you sign off. Skip one and it returns as manual work: no loop,
you read every output; no graph, you approve every step. Detail: `references/Loops.md`.

| Question | Command |
|---|---|
| what runs in parallel, what gates the finish, what an arrow costs | `graph` |
| does cutting this dependency shorten the run | `graph --cut '<dep> <- <task>'` |
| is the graph even runnable (cycle, dangling dep, duplicate id) | `graph --check` |
| is an open-ended hunt done, and has it already thrown this away | `hunt '<topic>' --run '<cmd>'` |

- **Test every arrow by naming the payload.** `graph` lists edges whose ends share
  no feature, area or tag as *unproved*: name what travels along it or cut it.
- **A cycle needs five things**: a dry test, a round limit, a budget, memory of past
  attempts and a person paged on a stall. `hunt` owns all five and exits 1 when the
  loop is stalled rather than converged.
- **Send back the unit, not the batch.** `review --result fail --scope '<what the
  fix may touch>'`; the retried lane packet opens with the finding and the scope.
- **No model where code will do.** Classifying evidence, sorting, dedupe and the
  undo class are code (`grades.py`); a model there is slower and occasionally wrong.

### 6. Close

When the queue is empty and `loop` is about to report STOP, load `tw-ceo-audit-close` and follow it exactly: freeze the revision, verify the chain before the gates, check the archive against the tree, export the manifest last, and report from records. An unnamed skill is dead text nobody loads, and `harness lint` fails a tree that has one.

Completion gate - all of:

- [ ] Every acceptance criterion in `docs/Team/Project.md` has evidence from a revision.
- [ ] Every deliverable passed a self-check and an independent Reviewer verdict with reproducible evidence, and appears in `docs/Team/Archive.md`.
- [ ] Every required test layer passes, run by its owning role (`tests plan` reports no gaps).
- [ ] No open high-severity security finding; no unresolved red-line escalation.
- [ ] Every task branch is reviewed, merged into `main` and deleted.
- [ ] Every staffed role designed, implemented and ran its own test layer.
- [ ] `ledger verify` is intact, `audit` reports no provenance gap, and the `ledger export` manifest is committed.
- [ ] `loop` reports STOP and `audit` reports zero problems.
- [ ] Docs match merged code; no scratch or temp files; nothing unnecessary committed.
- [ ] Final report: deliverable, how to run it, evidence table, limitations, follow-ups.

Then end every live lane with `lane stop <run>` and run `lane reap`: it reconciles a lane that died without an outcome, frees its slot and recycles the seat of a finished lane under the roster policy - never the CEO, one instance of each gate role kept (move-only to `Runtime/Retired/`; `--keep` leaves the instances staffed). Confirm `loop` still reports STOP on the final head, and deliver the report.
## Reference files (read on demand)

`SKILL.md` is the operating procedure; policy detail lives in `references/`. Read
the one you need instead of the whole skill.

| File | Read it for |
|---|---|
| `references/Bootstrap.md` | intake, workspace, plan, staffing, close |
| `references/Evidence.md` | evidence shape, claim discipline, red lines, escalation |
| `references/Dissent.md` | independent decisions, the 3-round cap, the tribunal |
| `references/State.md` | memory, lessons, knowledge, context tree, queue, mailbox |
| `references/Concurrency.md` | caps, slot leases, lanes, scale, model routing |
| `references/Coordination.md` | multi-agent failure modes and their mechanisms |
| `references/Docs.md` | markdown structure, concision, bidirectional links |
| `references/Engineering.md` | identity, commit style, LFS, branches/PRs/merges, worktrees |
| `references/Roles.md` | the roster, handoffs, decision rights, the intern protocol |
| `references/Testing.md` | the role-owned test layers, dedupe, required coverage |
| `references/Audit.md` | provenance, the ledger, internal and external audit |
| `references/Adapters.md` | host operations, installation, refresh, degraded modes |
| `references/Remotes.md` | git-host integrity: protection, checks, merge, tags |
| `references/Loops.md` | loops, the task graph, failure routing, who signs off |

## Two-stage quality gate

Every deliverable passes **two** gates, in order:

1. **Self-check (the author).** Re-read the diff, *run* a self-test and record the
   result. You cannot submit work you have not checked.
2. **Independent review (the Reviewer).** The Reviewer judges the result against the
   requirement and either passes it (task `done`, result archived) or fails it
   (returns to the owner with findings). It verifies what no independent lane
   verified at that revision - requirement conformance, its own `acceptance` layer,
   the uncovered criteria and one sampled credit - and cites the rest (5h).

```text
todo -> doing -> selfcheck -> review -> done (merged into main by the Reviewer)
         |        ^            |
   branch start   |            v  (fail)
                  +-------- doing
```

**Evidence is graded, and a pass reads the grade.** `strong` is a result a program
produced (`-> 12 passed`, `exit 0`, `# issues: 0`, a digest); `medium` is a pointer
a reader can follow (`path:line`, `TS-0006 @rev`); `weak` is a command with no
result; `noise` is a self-assessment (`looks good`, `verified`, `no errors were
thrown`, `see the run`) and it is **refused** on a passing self-check and on a
passing verdict. An empty error log means nothing was reported, not that nothing
went wrong.

**A closed lane has no score to lower.** `preflight` sorts the diff by how hard it
is to undo. `closed` - a migration or schema path, a payment, a secret/auth/cert
path, a workflow that fires on merge, a release exception, or any deleted file -
fails until the CEO records the authorization: `task set <role> <T-id> --by ceo
--authorize '<who said yes + evidence>'`. `evidence` - the constitution, the frozen
contract, `config.py`/`records.py`, the build config - warns and asks for strong
evidence. A threshold is a number someone can lower on a busy Friday; a closed lane
has no number to lower.

- `task set --status review` is refused until `self_check: passed`, and a passing
  self-check needs a `--test` line - reading your own diff is not a test.
- Evidence is a packet: `--baseline`, `--artifact` (hashed into the ledger) and
  `--replay` travel with the claim, on self-check and review as well as `tests run`.
- A `--bug` task cannot pass without a `tests repro` record showing the failing run
  before the passing one.
- Only the owner may self-check, and only the Reviewer may review it; an author
  never closes a `review=required` task.
- A review claim belongs to one lane: another Reviewer is refused while the lease is
  live, only the holder renews or releases, and a verdict clears it.
- A pass appends the accepted result to `docs/Team/Archive.md`; read it by id with
  `archive --task <T-id>`.
- A re-submitted fix is a **delta**: its findings, the changed files, the failed
  criterion re-run, one fresh credit. At 3 failures the Reviewer opens a dispute.
- A design disagreement goes through the dispute protocol.

This applies to code, unit tests, integration/E2E tests, documentation, design
specs, plans, research, architecture contracts, cost models and risk registers. Full
sequence: `references/Roles.md` (Submission).

**The reviewer judges the artefact, not the author.** The verdict walks six ordered
criteria - delivery and conformance, fidelity, internal consistency, operational
fitness, finish, evidence reproduces - and stops at the first failure (the full
rubric is the `## Ordered criteria` section of `roles/reviewer.md`). Length and
polish are not merits; a shorter exact answer beats a longer one with a gap; "this
needs no change" is a real verdict; weigh the downside as heavily as the upside.

## Self-management charter

The team manages and corrects itself. The user is not part of the loop.

- The CEO resolves priority and scope conflicts, design disagreements, blocked
  tasks and duplicate work internally, records the decision, and moves on.
- Escalations go to the tribunal (CEO + CTO + CFO) after 3 rounds of dispute,
  never to the user mid-flight.
- The user is contacted **only** for: authorization of an irreversible/external
  or red-line action; a change to the goal, budget or non-negotiable constraints;
  a genuine ambiguity that changes what gets built and cannot be resolved from
  the repository, research or a recorded assumption; and the final report.
- Every other decision is made, recorded in `Decisions.md` / global memory, and
  implemented.

## Stop condition

`teamwork.py loop` is the mechanical stop check. It reports CONTINUE with reasons
while any of these hold, and STOP only when none do:

- an acceptance criterion record is missing, pending or unverified (`criteria`);
- a required test layer for an area is missing or not passing, or a staffed role
  has designed no test at all (`tests plan`);
- any task is `todo`, `doing`, `selfcheck`, `blocked` or `review`;
- any `review=required` deliverable is not `review_status: passed`;
- any task branch is not merged into `main`, or a merged branch still exists;
- a gate override is in force, or a memory entry has no `by` provenance;
- any dispute is unresolved (an escalated one needs its tribunal);
- the audit trail is missing, altered or truncated (`ledger verify`).

The human checkboxes in `Project.md`/`Plan.md` are advisory; the machine records
above are what actually gate completion. Run `audit` as well before reporting:
it covers the same ground plus links, LFS, duplicates and ownership sanity.

## Quick reference

```sh
S=<this skill dir>/scripts/teamwork.py

# bootstrap and shared state
python3 $S init --roster slim                      # --agents for an exact list
python3 $S agents-md && python3 $S repo && python3 $S map
python3 $S criteria add --id AC-1 --text "<verifiable statement>" --owner developer --by ceo
python3 $S tests require --area auth --layers unit,integration,acceptance --by ceo --reason "core"
python3 $S tests add --layer unit --area auth --command "go test ./internal/auth"
python3 $S tests run TS-0001 --by developer-1 --result pass --evidence "<cmd> @<rev> -> <result>"

# work: own branch -> commit -> self-check -> PR -> review -> Reviewer merge
python3 $S task next developer-1
python3 $S branch start --agent developer-1 --task T-0007 [--worktree]
python3 $S commit --role developer --type feat --task T-0007 --area auth \
    --goal "..." --deliverable "..." --why "..." --status "..." --result "<cmd> @<rev> -> result" --all
python3 $S selfcheck developer T-0007 --by developer-1 --note "<what you re-read>" \
    --test "<cmd> @<rev> -> <result>"
python3 $S pr open --agent developer-1 --task T-0007
python3 $S review developer T-0007 --by reviewer-1 --result pass --evidence "<verify cmd @<rev> -> result>"

# scale, coordinate and learn
python3 $S instance add architect --count 2 && python3 $S instance list
python3 $S memory claim architect --by Architect-2 --reason "rewrite the contract" \
    && python3 $S memory release architect --by Architect-2
python3 $S skill create --name tw-<kebab-name> --role developer --by developer-1 --for "<when to use>"
python3 $S skill share tw-<kebab-name> --by developer-1
python3 $S dispute open --by developer-1 --against architect --topic "..." --evidence "..."
python3 $S slot acquire --agent developer-3 --provider deepseek --task T-0012

# run the lanes and close
python3 $S swarm run --dry-run && python3 $S swarm run && python3 $S lane status --live
python3 $S lane stop L-0001 --reason "<why>" && python3 $S lane reap   # recycles the finished seats

# close and audit
python3 $S board && python3 $S pulse --commit && python3 $S parallel
python3 $S coordination --strict && python3 $S audit && python3 $S links && python3 $S loop
python3 $S ledger verify && python3 $S ledger export && python3 $S trace T-0007
```

Team lifecycle: `lane start` staffs a lane, `Inbox.md` coordinates it, `lane status|logs` inspects it, `swarm run` (or `pulse --commit` per wake) feeds idle lanes, and `lane stop` closes them. Per-host launchers and the `LaneCommand` template: `references/Adapters.md`.
