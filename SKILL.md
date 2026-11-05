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
11. **History is minimal and modular.** Commit while you work, then rebase and squash before review: one coherent change-set, `wip`/`fixup` squashed, rebased onto the default branch, one commit per task before the merge. The Reviewer merges locally (`git merge --no-ff`); `pr merge --squash` is the one-commit path. Never rebase or force-push shared history.
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
| `slim` (default) | 7 | 387 kB |
| `standard` | 10 | 538 kB |
| `full` | 17 | 882 kB |

Startup read = every instance's `AGENTS.md` plus its own role charter, summed -
the text a full roster pays for before any work starts, and 2.3x what `slim` costs.

A role earns a seat only if it owns a deliverable, a test layer and a decision
right no other role holds. Everything else is a **lane, not a role**: it costs no
charter, no queue and no memory set.

| Dropped from `slim` | Where the work goes |
|---|---|
| Product Manager | requirements and acceptance criteria ride with the CEO; `Research.md` becomes a task |
| Project Manager | `Plan.md`/`Board.md` ride with the CEO; `pulse` already does the chasing |
| CTO / COO | stack and risk are recorded in `Decisions.md`/`Risks.md` by whoever owns the change |
| CFO | `Costs.md` only when the work has a real cost dimension |
| Designer | `ui` layer unstaffed - add the role when the deliverable has a UI |
| Technical Writer | `docs` layer unstaffed - authors write their own docs, the Reviewer verifies |
| Data Engineer | `data` layer unstaffed - only a project owning persistent state needs it |
| Security Auditor | `security` layer unstaffed - add it when the brief has a compliance or threat surface |
| Release Engineer | the CEO pushes after review until shipping becomes a schedule of its own |

Two rules keep a slim roster honest, and both are enforced:

- `tests plan` only requires the layers of **staffed** roles, so a slim tier does
  not print gaps for work nobody owns.
- In either tier the tribunal never falls below two members: with no CTO/CFO
  staffed the Reviewer takes the neutral seat (`TRIBUNAL_MIN_SIGNERS`), and **a
  party to a dispute can never rule it**.
- **A vacant manager escalates to the CEO.** With no CTO staffed, the engineering
  lanes report straight to the CEO for the duration; dropping a manager never
  leaves a lane with nobody to escalate to, and it never quietly hands that lane to
  the Product Manager or the COO. An explicit `--agents` list is the one
  exception: staff fewer than two independent roles and `dispute resolve` prints a
  `1-member panel` warning, so the reduced panel is visible rather than silent.

`init` prints the folded lanes and warns when a gate-critical role is missing.
Scale writers with the critical path: add `developer-N`/`tester-N` before adding a
coordination role. **The Reviewer is not optional**, and two Reviewer lanes are the
minimum: the review queue fans one deliverable per lane, a re-submitted fix is
re-reviewed as a delta (the lane that raised the finding), and a second lane gives
a sampled or high-risk deliverable an independent verdict. A pass merges - the lane
that verified the revision lands it.

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

One iteration is: re-plan -> dispatch -> work in parallel -> independent review -> rework -> integrate. Repeat until `teamwork.py loop` reports STOP.

- Teammates auto-claim the highest-priority unblocked task; when one finishes it submits for review and takes the next.
- **Every deliverable is second-reviewed by the Reviewer**, independently: code, unit tests, integration/E2E tests, docs, design specs, plans, research, cost models and risk registers. A fail returns it to the owner with findings; the owner fixes, re-checks and re-submits. Review failures are counted: at 3 the Reviewer must open a dispute so the tribunal rules (`references/Dissent.md`), and `loop` blocks STOP until it does.
- **Every agent tests its own layer**: `goal` CEO, `requirements` Product Manager, `plan` Project Manager, `tech` CTO, `release` Release Engineer, `data` Data Engineer, `process` COO, `cost` CFO, `system` Architect, `ui` Designer, `docs` Technical Writer, `unit` Developer, `integration` Tester, `acceptance` Reviewer, `security` Security Auditor. `tests plan` shows the matrix and gaps; `loop` blocks STOP while a required layer is missing/failing.
- **Review is a parallel lane.** `reviewer-1..N` claim different deliverables from the shared queue (`review --queue`); one claim per deliverable, high-risk work gets two Reviewers, nobody reviews their own work, findings union, and a pass is the merge.
- The CEO keeps the interface contract stable and arbitrates; the Project Manager chases stalled tasks and refreshes `Plan.md`/`Board.md`; the COO keeps `Risks.md` honest; the Product Manager keeps `Research.md` current.
- The team is self-managing: the CEO resolves internal conflicts and disputes without involving the user, who hears only an authorization, a goal/scope/budget change, a blocking ambiguity, or the final report.

Periodically, and before every close:

```sh
python3 "$SKILL/scripts/teamwork.py" criteria list && python3 "$SKILL/scripts/teamwork.py" tests plan
python3 "$SKILL/scripts/teamwork.py" board && python3 "$SKILL/scripts/teamwork.py" review --queue
python3 "$SKILL/scripts/teamwork.py" coordination --strict && python3 "$SKILL/scripts/teamwork.py" audit
python3 "$SKILL/scripts/teamwork.py" links && python3 "$SKILL/scripts/teamwork.py" pulse --commit
python3 "$SKILL/scripts/teamwork.py" parallel && python3 "$SKILL/scripts/teamwork.py" loop
```

Report to the user at milestones: what changed, evidence, blockers, next - never progress without evidence.
### 5a. Parallelism is the default, not the reward

A team that runs one lane at a time is a slow single agent with extra records. Four rules keep every lane busy without inventing work:

| Rule | Mechanism | Why |
|---|---|---|
| A lane holds more than one unit | `LANE_WIP` (2): one deliverable in review plus the next in progress | a lane waiting for its own review is idle capacity |
| `pulse` fills capacity, not idle lanes | it assigns `LANE_WIP - held` per lane | the old one-task-per-idle-lane rule capped the team |
| A dependency can release early | `deps: role:T-id@review` or `@started` | the downstream lane needs a frozen interface, not a merge |
| Reviews are the exception | one claim per Reviewer lane; run several lanes | a deep review is not divisible |

Capacity is bounded by the provider caps in `Settings.json`, never by the lane count: `pulse` defers assignments beyond the free-slot count and prints the shortfall. Detail and the measured anti-patterns: `references/Concurrency.md`.
### 5b. Keep the lanes full: the CEO pulse

After dispatching, the CEO **re-wakes on an interval**, finds idle lanes, and hands them runnable work. Arm a recurring wake-up once and act on every wake:

```sh
python3 "$SKILL/scripts/teamwork.py" pulse --commit --interval 5
```

`pulse` prints idle lanes, ready work and a dispatch plan; `--commit` applies it and pins review claims so lanes never review the same deliverable. Exit 3 means "nothing to dispatch" - then check blocked tasks and disputes. A review claim is a renewable profile lease (`ReviewLeaseMinutes`, default 20; x1 fast, x2 standard, x4 deep), separate from the 90-minute provider-slot TTL: verdict with `--result`, extend with `--renew`, or `--release`.

An instance is **busy** only while it holds a slot, a `doing`/`selfcheck` task, or a live review claim; everything else is idle and must be fed. Interval: `PulseMinutes` (default 5). Instances also self-serve with `task next` between pulses. Disarm the schedule when the team closes. The scheduler adapter per host, and the pulse prompt, are in `references/Adapters.md`.
### 5c. Push in stages, and certify both signals

- **Release Engineer - push after review, stage by stage.** Only the Release Engineer pushes, and only after the Reviewer passed that revision with no open finding. **A stage ends with a push, not with a merge**: push each reviewed and merged stage instead of batching, so the remote never drifts far from local `main`. Before the push, build, tests, `privacy_scan.py --tree --history` and the link check are green on exactly that revision; after it, watch CI and confirm it is green **on that SHA**. A red run is routed from the log (code -> Developer, test -> Tester, contract -> Architect, workflow/packaging/flake -> Release Engineer, scope -> CEO) and re-run after the fix. A code-scanning alert is the same gate: `teamwork code-scanning` reads the open alerts, an `error`/`critical`/`high` one is red on the shipped revision, and `--commit` files a `P0` task with the file's owner. Force-push and published-history rewrites need the CEO's authorization; tags and releases are the CEO's step, prepared by the Release Engineer.
- **Tester - certify local *and* CI.** Run the layers locally, then confirm the same result in CI on the pushed revision, job by job across the OS and Python matrix. A green local run with a red CI run is a failure, and so is the reverse; file every failure to its owner with the command, expected vs actual, log, SHA and run id.
- **CI triggers are path-filtered: code in, prose and media out.** Docs and images get a cheap docs workflow (link health, privacy scan, `mkdocs build --strict`); anything that ships - `src/`, `scripts/`, `tests/`, packaging, workflows, `roles/`, `references/`, `templates/` - always runs the full matrix. Never ignore a path that ships, and keep the two lists in sync.
- **Everyone keeps the tree clean.** No explanatory comment (`scripts/check_comments.py` fails the gate), no commented-out code, no `TODO` without a tracked task; delete temp and stale files in the same task (`clean` for your lane, `--all` for its `Scratch/`); one canonical home per file, cleaner than you found it.

Both duties are evidence: `tests plan` and the task record name the local result **and** the CI run (id + conclusion) for the certified revision. Detail: `references/Engineering.md`.
### 5d. Any agent host, any git host

- **Agent host.** The engine, workspace, criteria, two-stage gate, ledger and test matrix are host-independent. Only six
  operations need a host mechanism - spawn a teammate, delegate one-shot work, message an agent, inspect state, re-wake on a schedule, close the team. Name the operation, then use the adapter in `references/Adapters.md` (a teammate tool, a host CLI in a `bash` job, or the files themselves). Never hard-code a host tool in a normative step and never fake one the host lacks: record the degraded mode. With no scheduler or teammate tool the protocol still completes - one agent wearing the hats sequentially, with the same gates.
- **Git host.** The Release Engineer guarantees repository and CI integrity on any host: a protected default branch, **no force-push**, no deletion, required status checks on the exact revision, at least one non-author approval, the host merge button off - the Reviewer merges locally and the source branch is deleted (`pr merge --squash` is the one-commit path) - protected `v*` tags created only by the CEO, and least-privilege CI with no secret in the tree. Record the actual settings from the host API and re-read them to detect drift; an unprotected setting is a defect on par with a red build. Per-host mapping: `references/Remotes.md`.
### 5e. Keep the installed skill on the remote's `main`

The host loads a **copy** of the skill, so a copy that drifts from `origin/main` silently keeps reading an old protocol. `teamwork.py refresh` fast-forwards a checkout source and mirrors the bundle into the skills directory; `--check` reports drift and exits 1 when stale, `--dry-run` prints the plan. A dirty checkout is mirrored, never reset. Run it at startup and after every push, and reload the skill afterwards. Full behaviour: `references/Adapters.md`.
### 5f. Keep lanes decorrelated

Identical lanes make identical mistakes: same model, same context, same queue.

- `model auto --apply` with `TEAMWORK_MODEL_ALT` when two Reviewer, Tester or Security Auditor lanes are staffed; `coordination` reports `C-DIV-MODEL` when every verification lane shares one model.
- `coordination --strict` is the milestone gate: duplicate branch/task, echoed evidence, reviewer monoculture, abandoned PRs, a merge fraction below 0.5, slot starvation. `--commit` records it; exit 1 means a high finding is open.
- A conflict is resolved by a measurable contest or the CEO, never by denying a peer a resource. `reclaim` refuses a live lane; `--force <reason>` is only for a confirmed dead one.
- The Reviewer reads the artifact before the author's summary and records its own run; identical evidence is `C-TRUST-ECHO`.
- A user-facing deliverable is **shown** at the milestone - a build, screenshot or recording - because taste is not emergent.

Mechanisms and the de-escalation ladder: `references/Coordination.md`.
### 5g. Keep reviews fast

The Reviewer is the gate every lane waits on; its queue, not its depth, is the throughput limit.

- `review --queue` sorts by priority then age and prints the profile, claim state and capacity. Add a Reviewer lane when the unclaimed queue is deeper than twice the lanes; a deep review is not divisible.
- `review <role> <T-id> --packet` gives the profile, changed files, self-check, gates and checklist in one screen; start there.
- The profile is inferred from the diff: `fast` for prose (link check, docs/contract tests, privacy scan), `standard` for code (suite, lint, type-check; a green CI run may be cited), `deep` for security/release/data/workflow (also privacy history and the security scan). `task add --review-profile` overrides it.
- A claim is a **profile-aware renewable lease** (`ReviewLeaseMinutes`, default 20; x1/x2/x4 fast/standard/deep), not the slot TTL. `review --next --by <lane>` claims and prints the packet in one step; `--renew` extends a long review; do not hold a claim while writing prose. `coordination` reports claim-to-verdict p50/p90 and expired claims.
### 5h. Verify once, credit the rest

The Reviewer is the lane every other lane waits on, and most of a slow review repeats work another role already did at the same revision. Independence is about the **author**, not about repeating a peer: a recorded result from another role at the revision under review is a fact to cite, and `review --packet` lists it.

| Rule | What it means in the loop |
|---|---|
| one run per fact per revision | a recorded result (`tests run --rev`, a CI run on the pushed SHA) is not run again; cite it with `--credit` |
| the irreducible core | the reviewer runs requirement conformance, its own `acceptance` layer, every `uncovered` criterion, and **one sampled credit** |
| creditable | a `passing` record at this revision, by a role other than the author's, with the command written down |
| recorded, not implied | `review ... --result pass --credit TS-0006` writes `credited: ...`; a stale, failing, author-role or unknown record is refused with the reason |
| read the machine verdict | lint, format, type-check, suite, links, privacy and security scan are read once; re-running a green record is `C-REVIEW-DUP` |
| a fix is a delta review | a fail stores the revision; re-review the delta, the failed criterion and one fresh sampled credit |
| full re-review only on a contract change | a new deliverable, a frozen interface, a security/release/data/workflow path, or a diff larger than the original |
| budget | fast 10 / standard 20 / deep 40 minutes; when spent and unverifiable, fail naming the missing evidence |
| batch the context | same author + area + profile may be one sitting - one claim and one verdict each |

`coordination` reports the credit ratio, delta re-reviews, `C-REVIEW-DUP` and `C-REVIEW-NOCREDIT`. Every author records a run with `--rev <sha>` and `--artifact`: an unrecorded run is a run the Reviewer has to repeat.
### 5i. The throughput contract

Speed is a property of the structure, not of working harder. Measured on this project's own trail at **one** ledger cut, `n=1615` (append-only ids make the cut reproducible; never mix cuts): **44** review failures over **66** review targets (one role + task), 26 targets needing more than one verdict and 11 needing three or more; verdict distribution 40/15/6/4/1. Two independent readings put failures a local check could have caught at **16-24 of 44**, but the split is **contested**, so the contract does not rest on it: every fail now records whether the author had a green `preflight` at that revision (`mechanical: no|unknown|n/a`), measuring it prospectively. `teamwork.py throughput` re-reads the current cut.

| Rule | What it forbids |
|---|---|
| one parent, one board | a second reporting line; three managers for one role |
| one feature, one team | a Team Leader owning two open features, or two teams on one slice |
| one owner per artifact, one writer per file | two lanes editing the same contract, board, charter or source file |
| one verification per fact per revision | re-running a gate another role recorded green at that revision (5h) |
| one gate, one place | CI and docs running the same check; the Reviewer repeating `preflight` |
| definition of ready | starting on a moving interface, a shared path, or an in-flight dependency |
| definition of done | a done that is not preflight-green + independent pass + archived + merged |
| generated artifacts render at the merge | a `Board.md`/`Archive.md` render riding a feature branch |
| right-sized roster | one lane per task; a second Developer for a slice one can carry |
| small slices, short leases | a task that cannot be verdict-ed inside one lease - split it |

`preflight <role> <T-id>` turns rules 6-8 into one fail-closed command: identity, commit count, every `@<sha>` in the evidence exists, `merge-tree` against the base is clean, board drift is charged only to a board edit, and the project gate runs from `Settings.json` -> `PreflightCommand` (`--run`). A fail records `mechanical`, so the table stays measurable.

**Feature teams are live** (structure in `references/Roles.md`, engine `teamwork.py feature add|set|list|check`, contract in `Architecture.md` 13): a Team Leader owns one open feature per leader and its squad, teams run in parallel, and the Architect and Project Manager are shared services. `feature check` applies five rules - shared writable path, in-flight dependency, one open feature per leader, owned-path shape, duplicate id - and a feature cannot leave `proposed` without a frozen interface, refused by `feature set <F-nnnn> --state ready`. `preflight`, a review pass and the merge all run it.
### 5j. Learning is part of the work

A failure you do not record is one the team pays for twice.

- **A lesson (`L-`)** after your own self-check or a review fails, and after any mistake worth not repeating: the observable failure, cause, the rule you now follow, and the evidence that proved it. `lesson add` requires all four and `load` shows open lessons at every startup. Record it before re-submitting; `lesson fix` closes it when the re-run proves the rule.
- **A `tw-` mistake skill** when the fix is a flow: `skill create --kind mistake --from-lesson L-nnnn` marks the lesson fixed, links both records and names the failure it prevents. A recurring finding with no skill behind it is a defect.
- **A knowledge record (`K-`)** for a durable fact, command or gotcha: statement, evidence, tags, importance 1-5 and a kind (`fact`, `experience`, `preference`, `gotcha`, `rule`). Search before asking, `touch` what you used, and supersede an old fact with `knowledge add --supersedes K-0002`. Never store a secret or personal data.

```sh
python3 "$SKILL/scripts/teamwork.py" lesson add --by <you> --mistake '<failure>' \
    --cause '<why>' --rule '<what changes>' --evidence '<cmd @rev -> result>'
python3 "$SKILL/scripts/teamwork.py" skill create --name tw-<slug> --role <role> \
    --by <you> --kind mistake --from-lesson L-0001 --for '<when>'
python3 "$SKILL/scripts/teamwork.py" knowledge add --by <you> --topic '<topic>' \
    --statement '<one fact>' --evidence '<cmd @rev -> result>' --tags '<tag,tag>' --importance 4
```

`load` prints the first 10 open lessons and the top 10 active knowledge records. Both stores are team-local, never committed, and written only through the commands: `Roles/<Role>/Lessons.md` is role-shared; `Knowledge.md` is team-wide. Classify a finding before recording it - tool defect, process, doc drift, governance or knowledge - and run `tw-self-evolve` at every milestone close. A tool defect takes a code task with a failing reproduction, never a lesson. Detail: `references/State.md`, `docs/Team/Evolution.md`.
### 5k. The context tree

`ctx://` is one read-only view over memory, lessons, knowledge, skills, docs and tasks; every node resolves to an existing file or record and no sidecar is written. L0 is the one-line summary, L1 the record fields or child list, L2 the full record. Use `context ls`, `tree`, `read <uri>`, `find "<query>" [--scope <uri>]`, `stats`, `digest <T-id>`. Retrieve by id, never by whole file: start with `context find` or `context ls`, then read the level you need. `context digest` proposes a lesson or knowledge block and writes nothing. `context` never replaces `load`, the gates or the evidence rule. Detail: `references/State.md`.
### 5l. Throughput and the token budget

- **Right-size the roster.** `slim` is the default; add an instance for a named deliverable or a queue deeper than its lanes (`parallel`, `instance list`), and retire an idle one. Retirement is **move-only** to `Runtime/Retired/<Instance>/`; verify `git rev-parse HEAD` is at or after the move-only revision (`b9e5135`) first - a stale cut lost 102 artifact paths (`L-0001`).
- **Read by id, never by history.** `archive --task <T-id>`, `decision list`, `board`, `trace <id>` answer a question; a whole `Archive.md` is ~0.63M tokens against a ~0.11-0.15M startup, and `Decisions.md`, `Plan.md` and a `TaskQueue.md` are the same trap.
- **Make the first pass review-ready.** The self-check note answers the boundary and empty/duplicate/second-call case, the contract surface, concurrency/shared writes, and the exact scope, each with a test or a reason. On a code task the Tester records the full suite first and the Reviewer cites it (`--credit`), so it is paid once.
- **Keep the budget token-true.** `harness budget` measures what `load` prints; `--recallable` reports long-term/archived memory and fixed lessons that `load` never prints. The cap is `AlwaysOnBudgetKb` (122880 B default); when a row is over, trim what `load` prints and record why - never raise the cap.
- **Split at the slice warning.** `preflight` warns past 6 files/300 lines (`fast`), 12/600 (`standard`), 24/1200 (`deep`); split, or say in the self-check why it is one contract.

`teamwork.py throughput` is the measured reader for latency, pass/fail, rework, queue depth and surface bytes. Detail: `references/State.md`.
### 5m. The intern protocol

The model is an intern: introduce the work, give it one job, prove the job, and remove every manual relay. Full text: `references/Roles.md`; the audit is the `tw-team-designer` team skill.

| Rule | What it forbids |
|---|---|
| no human relay | the user copying a fact between agents or re-stating repository state; record it (`attention add`) and automate it |
| teach once, encode it | a repeatable method living only in the conversation; `skill create`/`skill share` in the same task |
| least privilege, one job, one proof | granting every connector; every deliverable names its verifier and proof |
| onboard, then restate | planning before the agent restated goal, acceptance and non-goals |
| proactivity is a record | silent autonomy; an idle lane proposes one automation/risk via `attention add` or a task |
| routine hygiene | a schedule with no trigger, budget and stop condition |

Do not give a bot its own email or external accounts: that is external and irreversible. Adopt the smallest team that reliably does the work, with a proof per seat.
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

Then end every live lane with the host's stop action, confirm `loop` still reports STOP on the final head, and deliver the report.
## Reference files (read on demand)

`SKILL.md` is the operating procedure; policy detail lives in `references/`. Read the one you need instead of the whole skill.

| File | Read it for |
|---|---|
| `references/Bootstrap.md` | the one-time flows: intake, workspace, plan, staffing, close |
| `references/Evidence.md` | evidence shape, claim discipline, red lines, escalation |
| `references/Dissent.md` | independent decisions, challenges, the 3-round cap, the tribunal |
| `references/State.md` | memory, lessons, knowledge, the context tree, the task queue |
| `references/Concurrency.md` | provider caps, slot leases, parallelism, reuse, model routing |
| `references/Coordination.md` | multi-agent failure modes and their mechanisms |
| `references/Docs.md` | markdown structure, concision, bidirectional links |
| `references/Engineering.md` | identity, commit style, LFS, branches/PRs/merges, worktrees |
| `references/Roles.md` | the full roster, handoffs, decision rights, the intern protocol |
| `references/Testing.md` | the role-owned test layers, dedupe, required coverage |
| `references/Audit.md` | provenance, the hash-chained ledger, internal and external audit |
| `references/Adapters.md` | host operations, installation, refresh, degraded modes |
| `references/Remotes.md` | git-host integrity: protection, checks, merge, tags, least privilege |

Team skills are named `tw-<kebab-name>` in `.agents/skills/tw-<name>/SKILL.md` and the front matter; `skill create` refuses any other name and `harness lint` reports `PREFIX`. Two kinds: `workflow` (the one way to do a recurring job) and `mistake` (from a lesson with `--from-lesson L-nnnn`, which marks it fixed and links both). A skill is project output, goes through the normal branch/PR/review, and never replaces this file, a red line or a gate.

Every mutation appends to the hash-chained `Ledger.jsonl` (`ledger verify`, `ledger show`, `trace <id>`); `ledger export` writes `docs/Team/AuditManifest.json`. A broken chain blocks STOP. Criteria are records, not checkboxes (`criteria add|verify|list`); reclaim stuck work with `task reclaim <role> <T-id> --as <Instance> --reason "..."`.
## Two-stage quality gate

Every deliverable passes **two** gates, in order:

1. **Self-check (the author).** Re-read the diff, *run* a self-test and record the result. You cannot submit work you have not checked.
2. **Independent review (the Reviewer).** The Reviewer judges the result against the requirement and either passes it (task `done`, result archived) or fails it (returns to the owner with findings). It verifies what no independent lane verified at that revision - requirement conformance, its own `acceptance` layer, the uncovered criteria and one sampled credit - and cites the rest (5h).

```text
todo -> doing -> selfcheck -> review -> done (merged into main by the Reviewer)
         |        ^            |
   branch start   |            v  (fail)
                  +-------- doing
```

Mechanical enforcement:

- `task set --status review` is refused until `self_check: passed`, and a passing self-check needs a `--test` line - reading your own diff is not a test.
- Evidence is a packet: `--baseline`, `--artifact` (hashed into the ledger) and `--replay` travel with the claim, on self-check and review as well as `tests run`.
- A `--bug` task cannot pass without a `tests repro <T-id>` record showing the failing run before the passing one (`--force` with a reason only when it genuinely cannot be reproduced).
- Only the owner may self-check, and only the Reviewer may review it; an author never closes a `review=required` task.
- A review claim belongs to one lane: another Reviewer is refused while the lease is live, only the holder renews (`--renew`) or releases (`--release`, or `--force <reason>` for a dead holder), and a verdict clears it. With several lanes name the instance (`reviewer-1`).
- A pass appends the accepted result to `docs/Team/Archive.md`; read it by id with `archive --task <T-id>`.
- A re-submitted fix is a **delta**: its findings, the changed files, the failed criterion re-run, one fresh credit. Failures are counted, so at 3 the Reviewer opens a dispute and the tribunal rules.
- A design disagreement goes through the dispute protocol.

This applies to code, unit tests, integration/E2E tests, documentation, design specs, plans, research, architecture contracts, cost models and risk registers. Full command sequence: `references/Roles.md` (Submission).

**The Reviewer judges the artefact, not the author.** The verdict walks six ordered criteria - delivery and conformance, fidelity, internal consistency, operational fitness, finish, evidence reproduces - and stops at the first failure (the full rubric is the `## Ordered criteria` section of `roles/reviewer.md`). Length and polish are not merits; a shorter exact answer beats a longer one with a gap; "this needs no change" is a real verdict; weigh the downside as heavily as the upside.
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

# close and audit
python3 $S board && python3 $S pulse --commit && python3 $S parallel
python3 $S coordination --strict && python3 $S audit && python3 $S links && python3 $S loop
python3 $S ledger verify && python3 $S ledger export && python3 $S trace T-0007
```

Team lifecycle: the teammate tool to staff a lane, the reply/steer channel to coordinate, the status view to inspect, the scheduler for the pulse and the stop action to close. Per-host names: `references/Adapters.md`.
