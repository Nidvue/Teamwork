# Roles, handoffs and decision rights

Owner: CEO.

Reference for the /teamwork skill. Loaded on demand.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Testing](Testing.md) | [Audit](Audit.md) | [Coordination](Coordination.md)

## Roster

| Role | Instances | Owns | Reports to |
|---|---|---|---|
| CEO | leader session, never spawned | user interface, decomposition, assignment, arbitration, global memory, final report | user |
| CTO | `cto` | technology strategy, feasibility, stack, engineering standards, the build/release *policy*, and the engineering lanes | CEO |
| COO | `coo` | process, tooling, dependencies, risk register, planning and throughput | CEO |
| CFO | `cfo` | cost model, budget, unit economics, build-vs-buy, ROI | CEO |
| Product Manager | `product-manager` | competitor/state-of-the-art research, stories, requirements, acceptance criteria, traceability, and the product/documentation lanes | CEO |
| Reviewer | `reviewer` or `reviewer-1..N` | independent second review of **every** deliverable; **the only role that passes review and merges into `main`** | CEO |
| Security Auditor | `security-auditor` | security assessment, red lines, remediation verification; audits the whole team, CTO included | CEO |
| Architect | `architect` | system/module/API/data/deployment architecture, **frozen interfaces**, ADRs | CTO |
| Team Leader | `team-leader` or `team-leader-1..N` | **one feature** end to end (`F-nnnn`), its squad, its `feature` test layer, and the proof that the feature is independent of every other open feature | CTO |
| Developer | `developer-1..N` | production code, **its own unit tests**, inline docs, commits on its branch | CTO |
| Tester | `tester-1..N` | integration/system/E2E tests, running and monitoring them, defect routing, regression | CTO |
| Release Engineer | `release-engineer` | build/release pipeline, CI gates, packaging, rollback, observability, runbooks | CTO |
| Data Engineer *(conditional)* | `data-engineer` | schema, migrations, integrity, backup/restore drills, query health | CTO |
| Project Manager | `project-manager` | `Plan.md`, `Board.md`, task decomposition, dependency graph, duplicate detection, progress chasing | COO |
| Designer | `designer-1..N` | UX flows, accessibility, visual consistency, `Design.md` | Product Manager |
| Technical Writer | `technical-writer` | the committed documentation set, executed as written; release notes | Product Manager |

```text
CEO - user interface, arbitration, final acceptance
├── CTO - technology strategy, engineering standards
│   ├── Architect - frozen interfaces, ADRs
│   ├── Team Leader-1..N - one feature each, a squad, the slice's feature layer
│   ├── Developer-1..N - code + its own unit tests
│   ├── Tester-1..N - integration/E2E, local + CI
│   ├── Release Engineer - pipeline, packaging, repo/CI integrity
│   └── Data Engineer - schema, integrity, restore drills
├── COO - process, risk, throughput
│   └── Project Manager - plan, board, dependencies, chasing
├── Product Manager - research, requirements, acceptance criteria
│   ├── Designer - UX, accessibility, every visual asset
│   └── Technical Writer - documentation, release notes
├── CFO - cost, budget, unit economics
├── Reviewer-1..N - independent review, the only pass/merge right
└── Security Auditor - audits everyone, CTO included
```

**Why these three stay with the CEO.** The Reviewer passes and merges every
deliverable, so it cannot be managed by a lane whose work it reviews - that would
be review under a manager, not independent review. The Security Auditor audits the
CTO's own decisions. The CFO holds the cap that binds every other role. Everything
else hangs off the role that owns the standard it is judged by. `ROLE_PARENT` in
`src/teamwork/config.py` is the single source of truth: `teamwork.py map` renders
this tree and `tests/unit/test_reporting_hierarchy.py` fails if a doc drifts from it.

**Escalation walks the tree.** A blocked Developer tells the Architect, then the
CTO; a blocked Tester tells the CTO; a blocked Designer tells the Product Manager.
The CEO hears it only when the line cannot resolve it - or when it is a red line,
a goal change, or a decision that binds the whole team. This keeps the CEO out of
day-to-day arbitration without weakening a single gate: the two-stage review, the
ledger and the test matrix apply to every role wherever it sits.

### Roster tiers

`init --roster <tier>` expands a tier into instances; `--agents` overrides it.

| Tier | Instances | Startup read |
|---|---|---|
| `slim` (default) | 7 | 388 kB |
| `standard` | 10 | 540 kB |
| `full` | 17 | 885 kB |

Startup read = every instance's `AGENTS.md` plus its own role charter, summed
(`engine.expand_roster(tier)` over `roles/*.md` and `templates/AGENTS.md`). A tier is a recipe, not a rule: add any role the brief
justifies, and prefer an extra `developer-N`/`tester-N` over a coordination role.

**Any role scales after the roster is written.** `teamwork.py instance add <role>
--count N` adds instances of a role at any point - `architect-2`, `cto-2`, a second
Product Manager - against the role's existing `Roles/<Role>/` memory and queue,
and `instance retire` takes an idle one back out without touching that memory. The
instances of a role are peers on one queue, and **only one of them revises the
role's memory at a time** (`memory claim <role> --by <instance>`, `release` when
the update is complete) - so a lane never has to reason about a file a peer was
half-way through editing.

A tier drops **lanes**, not gates:

| Dropped from `slim` | Where the work goes |
|---|---|
| product-manager | requirements, acceptance criteria and `Research.md` ride with the CEO |
| project-manager | `Plan.md`/`Board.md` ride with the CEO; `pulse` does the chasing |
| cto / coo | stack and process facts go in `Decisions.md`/`Risks.md` |
| cfo | `Costs.md` only when the work has a real cost dimension |
| designer | `ui` layer unstaffed |
| technical-writer | `docs` layer unstaffed; authors write their own docs |
| data-engineer | `data` layer unstaffed |
| release-engineer | the CEO pushes after review |
| security-auditor | `security` layer unstaffed |

Two invariants hold at every tier, and both are tested:

- `staffed_layers` only requires a layer whose owning role has an instance, so
  `tests plan` never reports a gap for work nobody owns.
- `required_tribunal` never drops below `TRIBUNAL_MIN_SIGNERS`: with no CTO/CFO,
  the Reviewer is the neutral seat, and a party to a dispute can never rule it.

The party rule is per **instance**, not per role: a dispute names the two agents
between it, so an instance is a party when it is named in `raised_by`/`against`.
A role leaves the panel only when EVERY one of its instances is a party, so the
uninvolved third Reviewer can seat a Reviewer-vs-Reviewer dispute - that
instance is the neutral seat the invariant above promises. A party may never sign
or resolve, and `--force` waives the signature requirement, never the party rule.

`init` prints the folded lanes and warns when `ceo`, `developer`, `tester` or
`reviewer` is missing (`ROSTER_REQUIRED`).

### Roles we deliberately do not add

A role earns a place only if it owns a distinct deliverable, a distinct test layer
and a distinct decision right. On that bar these stay out, and their work is folded
in as a lane rather than a role: marketing/sales (out of scope for an engineering
team; the CEO can staff them if a project ships commercially), a separate QA lead
(test strategy is the Tester's, test seams the Architect's), an accessibility
specialist (Designer owns `ui`, Reviewer verifies), and a dedicated performance
engineer (perf and load live in the Release Engineer's `release` layer and the
Tester's `integration` layer). Adding these would add ceremony without adding a
gate. **Staff two Reviewers** (`reviewer-1`,
`reviewer-2`): a passing review merges its own PR, so the second lane exists to
fan the *review* queue out, not to land what the first lane passed. Without a `reviewer` the team cannot pass review
or merge; without an `architect` nothing freezes interfaces. `init` warns when
either is missing.

## Throughput contract

Owner: CEO. Ten rules that remove duplicated, redundant and unnecessary work.
They bind every lane on any roster; the feature-team structure below is the shape
they are designed for.

1. **One parent, one board.** A role has exactly one line manager. Where a
   supervision body exists (CEO + CTO + CFO), it holds **decision rights**, never a
   second reporting line: the board decides, the manager manages. A role with two
   managers answers to neither.
2. **One feature, one team.** One open feature per Team Leader. A second
   concurrent feature means the org is short a leader, not that a lane serialises.
3. **One owner per artifact, one writer per file.** `Architecture.md`, `Board.md`,
   `Plan.md`, `Decisions.md`, the test records and every source file have one writer
   at a time; a second lane waits or is re-scoped. Two open features never share a
   writable path.
4. **One verification per fact per revision.** A passing result another role
   recorded at the revision under review is cited (`review --credit`), not re-run.
5. **One gate, one place.** CI owns the matrix. The author proves the same checks
   locally through `preflight`; the Reviewer reads the result instead of executing
   it again.
6. **Definition of ready.** Before a squad starts: interface frozen by the
   Architect, writable paths exclusive, no dependency on another feature's
   in-flight work, and the slice verifiable on its own. Failing one sends the
   feature back to the Architect, not to the calendar.
7. **Definition of done.** `preflight` green at the revision, an independent
   Reviewer pass, archived, merged. Nothing else counts; a status the board does
   not show does not exist.
8. **Generated artifacts render at the merge** *(T-0043)*.
   `Board.md` and the archive belong to the base branch and are written by the
   merging Reviewer, so a branch does not carry a board render: the merge
   re-renders it as its **last** act, after the merge commit and its records
   commit, because a render riding a feature branch conflicts with the next merge
   by construction.
9. **Right-sized roster.** One Developer and one Tester per feature team; a second
   Developer only for a genuinely parallel slice; specialists join the squad only
   for the features that need their layer; Reviewer lanes sized to the queue, not
   to habit. Every extra lane is a model bill and one more claim to coordinate.
10. **Small slices, short leases.** A task must fit one review **lease** -
    20 / 40 / 80 minutes for the fast / standard / deep profile - inside which the
    reviewer's own **budget** is 10 / 20 / 40 minutes. A slice that needs a deep
    review is split, not scheduled. A fix after a fail is re-reviewed as a delta by
    the lane that raised the finding.

### M18: the measured rules

The M18 cut adds four rules that follow from the measured trail (`teamwork.py
throughput` re-reads it):

- **Scale on demand, retire move-only.** `slim` is the default; add an instance
  only for a named deliverable (`parallel` and `instance list` read the demand).
  `instance retire` moves the idle directory to `Runtime/Retired/<Instance>/` and
  never deletes artifacts, reports or the worklog. A cut first verifies
  `git rev-parse HEAD` is at or after the move-only revision (`b9e5135`); the one
  cut from a stale checkout lost 102 artifact paths (`L-0001`).
- **Read by id.** `archive --task <T-id>`, `decision list`, `board` and `trace`
  answer a question; a whole `Archive.md` read is ~0.63M tokens against a
  ~0.11-0.15M startup. Never read all of `Archive.md`, `Decisions.md`, `Plan.md`
  or a `TaskQueue.md`.
- **Tester before Reviewer.** The author's self-check answers the first-pass
  contract (boundary/second-call, contract surface, concurrency, scope); the
  Reviewer judges the requirement and acceptance layer; the Tester records the
  full suite once and the Reviewer credits it (`--credit`), so the suite is paid
  once.
- **Token-true budget and right-sized slices.** `harness budget` measures
  startup; `--recallable` reports long/archive memory and fixed/superseded
  records. The cap is `AlwaysOnBudgetKb` (122880 B); trim what `load` prints,
  never raise it. `preflight` warns past 6/300, 12/600 or 24/1,200 files/lines;
  split or say why it is one contract - the warning is not a failure.

### Feature teams (merged; engine `teamwork.py feature`, contract in Architecture.md 13)

```text
CEO
├── CTO ─┬── Architect            (shared service: interface + file-ownership map)
│        ├── Team Leader A ── Developer, Tester [+ Designer/Data/Writer when the feature needs the layer]
│        ├── Team Leader B ── Developer, Tester
│        └── Release Engineer
├── Product Manager ── Designer, Technical Writer   (pooled, assigned per feature)
├── Security Auditor              (shared, independent - audits every team and the CTO)
├── Reviewer-1..N                (independent - the only pass/merge right)
└── COO ── Project Manager       (shared service: one graph, one board)
```

A Team Leader owns one feature record, cuts it into tasks that name the feature,
spawns the squad with `instance add <role> --under <leader>`, and is accountable
for the vertical slice. **Escalation is one hop:** a squad member escalates to its
Team Leader, the Team Leader escalates to the CTO, and a squad member takes no
CTO, CEO or CFO line of its own. `teamwork.py map` prints that live team - the
leader's `F-nnnn` and the instances under it - and `instance list` prints each
instance's manager (`under:<leader>` or `reports:<parent>`), so the one-manager
fact is visible rather than asserted. A specialist (Designer, Data Engineer,
Technical Writer) belongs to the shared pool and **reports to one manager at a
time**: the Team Leader for the duration of an assignment, and their discipline
head outside it - never both. The Security Auditor is the exception: it is never
attached to a team, because it audits the lane above and the team it would join
(D-20261029-Architect-2). That keeps **one line manager per
role at any moment**, which is why a supervision board can sit above a leader
without breaking the invariant.

## The intern protocol

Owner: CEO. Six rules for onboarding and running an agent like an intern, not a
search box. They are the adopted form of Lauren Tan's Grok Bot team guide (see
[RESEARCH](../docs/Team/Research.md) 11); the top comment's least-privilege
correction is part of rule 3.

1. **No human relay.** A fact the user must copy from one agent to another, or
   re-state from a file the repository already holds, is a tooling defect. Record
   it (`attention add --kind tooling`), automate the shortest path, and never
   present the manual step as the workflow.
2. **Teach once, encode it.** An instruction that defines a repeatable flow is
   turned into a team skill in the same task (`skill create`, `skill share`), not
   left in the conversation. Long context is not a storage medium; the skill file
   is. `skill candidates` is the audit.
3. **Least privilege, one job, one proof.** A lane gets only the tools, paths and
   accounts its deliverable needs. Every deliverable names its verifier and the
   command or artifact that proves it. "Give every bot every tool" is rejected;
   the adopted form is the smallest set that completes the job, with a proof per
   seat. Never give a bot its own email or external account: that is an external,
   irreversible action and a red line (AGENTS.md).
4. **Onboard, then restate.** Before planning, a new agent or task restates the
   goal, acceptance criteria and non-goals in its own words. The CEO confirms it,
   or the task packet carries the restatement. This is the voice-mode "restate
   this in your own words" check applied to the brief; a restatement that changes
   the scope is a requirement change, not a misunderstanding.
5. **Proactivity is a record.** An idle lane proposes one automation or risk it
   can remove (`attention add`, or a task with `--mandate inferred --basis`); the
   pulse routes it. Silent autonomy is not proactivity: a proposal is recorded,
   approved and measured.
6. **Routine hygiene.** Every periodic task names its trigger, its budget and its
   stop condition, and a heavy routine runs in its own lane instead of carrying
   the main context. Audit the cost with `harness budget`; a routine that cannot
   state those three is not created.

The `tw-team-designer` team skill runs the interview and the audit: roster (each seat
names a deliverable, a test layer and a decision right), skills, permissions and
verification, proactivity and routines. Its output is a one-page design with
adopt/adapt/reject rows and tasks - not a new bot by default.

## Handoff chain

```text
user -> CEO -> Architect (freeze interfaces) -> Project Manager (task graph)
                        |                              |
                        v                              v
        Developer / Tester / Designer lanes  <--  dispatch (pulse)
                        |                              |
                        v                              v
                  SelfCheck (owner)  ->  PR  ->  Review (Reviewer)  ->  merge into main
                        |                              |
                        v                              v
                  Product Manager (traceability)   Archive.md (evidence ledger)
```

Every handoff is a record, not a conversation: task state, PR record, review
verdict, archive entry. A peer message is only a pointer to the record.

## Decision rights

| Decision | Who decides | Where it is recorded |
|---|---|---|
| What to build, priority, scope | CEO (Product Manager proposes) | `docs/Team/Project.md`, `Plan.md` |
| Interfaces, architecture, ADRs | Architect (CTO consults) | `Architecture.md`, `Decisions.md` |
| Stack, feasibility, build/release policy | CTO | `Decisions.md` |
| Pipeline, packaging, rollback, observability | Release Engineer | `Release.md`, runbooks |
| Documentation set and release notes | Technical Writer | the committed docs |
| Schema, migrations, backup/restore | Data Engineer | migrations, data dictionary |
| Cost, budget, build-vs-buy | CFO | `Costs.md` |
| Process, risk register | COO | `Risks.md` |
| Acceptance criteria and their verification | CEO writes; an independent role verifies | `Criteria.md` |
| Review verdict | the Reviewer that verified it | task `review_status`, `Reviews.md` |
| Merge into `main` | the pass itself, recorded by the Reviewer who verified it; the author is refused | merge commit, `Archive.md` |
| Test layer ownership and required coverage | each layer's own role; the Architect declares the required layers | `Tests.md`, `TestPlan.md` |
| Contested design/decision | tribunal: CEO + CTO + CFO, after 3 rounds | `Disputes.md` + `Decisions.md` |
| Red-line refusal | blocked until the CEO relays explicit user authorization | `Global/GlobalMemory.md`, `Decisions.md` |
| Final completion report | CEO to the user | user message + `Archive.md` |

## Test layers (independent, parallel)

Every role owns exactly one layer (see `Testing.md` for what each must verify):
`goal` CEO · `requirements` Product Manager · `plan` Project Manager · `tech` CTO ·
`release` Release Engineer · `data` Data Engineer · `process` COO · `cost` CFO ·
`system` Architect · `ui` Designer · `docs` Technical Writer · `unit` Developer ·
`integration` Tester · `acceptance` Reviewer · `security` Security Auditor.

Default required coverage per area is the proportionate core set
(`unit`, `integration`, `acceptance`); `tests require --area <a> --layers ... --by
<instance> --reason <why>` widens or narrows it on the record. Every staffed role
must design and run at least one test of its own layer.

Each layer is designed, implemented and run by its owner; one record per
(layer, area) prevents duplicate testing. Details: `{references}/Testing.md`.

## Submission (the single canonical path)

Every role that produces work uses this path; nothing else closes a task.

```sh
teamwork.py branch start --agent <you> --task <T-id> [--worktree]
teamwork.py commit --role <role> --type <feat|fix|test|docs|design|research|refactor|chore> \
    --task <T-id> --area <area> \
    --goal "<what was asked>" --deliverable "<what you produced>" \
    --why "<why this change>" --status "<actual state, truthfully>" \
    --result "<command @rev -> observed result>" --all
teamwork.py task set <role> <T-id> --status selfcheck
teamwork.py selfcheck <role> <T-id> --by <Instance> --note "<what you re-read>" \
    --test "<self-test command @rev -> observed result>"
teamwork.py pr open --agent <Instance> --task <T-id>
# Reviewer:
teamwork.py review <role> <T-id> --by <Reviewer> --result pass --evidence "<verify cmd @rev -> result>"
teamwork.py pr merge --pr <P-id> --by <reviewer>  # a pass already merged it;
#                            use this only to land a --no-merge pass
```

A pass merges the deliverable at once and deletes its branch, so there is no
second Reviewer step: the engine refuses an author merging their own work and
records the pass-without-merge only when `--no-merge` is given.

Charters do not restate this; they state what the role produces and decides.

## Boundaries that apply to every role

- Never contact the user; escalate to the CEO and keep working.
- Never approve or merge your own work; only the Reviewer merges.
- Never commit on `main`; work on your own branch.
- Never fake evidence, weaken tests, or claim an unexecuted result.
- Stop at a red line: record it, escalate, do other work meanwhile.

## Learning loop

Every role records its own experience; it is not the CEO's or the writer's job to
remember it for them.

- A self-check or review failure becomes a lesson in the role's `Lessons.md`
  (`lesson add`), with the failure, the cause, the new rule and the evidence.
  When the fix is a flow, the role creates a `tw-` mistake skill from it
  (`--kind mistake --from-lesson L-nnnn`) so the lesson is closed by the change
  that prevents it.
- A durable project fact becomes a `K-` record in the team `Knowledge.md`
  (`knowledge add`) with its evidence, tags and importance; every role reads the
  top-ranked records at startup, searches before asking, and `touch`es a record
  it used.
- The Reviewer records a lesson when the same finding class recurs - across
  authors or rounds - and checks that a repeated finding has a lesson or a `tw-`
  skill behind it.
- The CEO reports the growth at close-out: active knowledge records, fixed
  lessons and the `tw-` skills they produced. A project whose agents never add or
  use a record is not accumulating experience, whatever its archive says.
