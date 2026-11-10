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
| `slim` (default) | 6 | 256 kB |
| `standard` | 9 | 374 kB |
| `full` | 16 | 641 kB |

Startup read = every instance's `AGENTS.md` plus its own role charter, summed
(`engine.expand_roster(tier)` over `roles/*.md` and `templates/AGENTS.md`). A tier is a recipe, not a rule: add any role the brief
justifies, and prefer an extra `developer-N`/`tester-N` over a coordination role.

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
