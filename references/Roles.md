# Roles, handoffs and decision rights

Reference for the /teamwork skill. Loaded on demand.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Testing](Testing.md) | [Audit](Audit.md)

## Roster

| Role | Instances | Owns | Reports to |
|---|---|---|---|
| CEO | leader session, never spawned | user interface, decomposition, assignment, arbitration, global memory, final report | user |
| CTO | `cto` | technology strategy, feasibility, stack, engineering standards and the build/release *policy* | CEO |
| COO | `coo` | process, tooling, dependencies, risk register, throughput | CEO |
| CFO | `cfo` | cost model, budget, unit economics, build-vs-buy, ROI | CEO |
| Architect | `architect` | system/module/API/data/deployment architecture, **frozen interfaces**, ADRs | CEO, CTO |
| Product Manager | `product-manager` | competitor/state-of-the-art research, stories, requirements, acceptance criteria, traceability | CEO |
| Project Manager | `project-manager` | `Plan.md`, `Board.md`, task decomposition, dependency graph, duplicate detection, progress chasing | CEO, COO |
| Designer | `designer-1..N` | UX flows, accessibility, visual consistency, `Design.md` | CEO, Product Manager |
| Developer | `developer-1..N` | production code, **its own unit tests**, inline docs, commits on its branch | CEO, Architect |
| Tester | `tester-1..N` | integration/system/E2E tests, running and monitoring them, defect routing, regression | CEO |
| Release Engineer | `release-engineer` | build/release pipeline, CI gates, packaging, rollback, observability, runbooks | CEO, CTO |
| Technical Writer | `technical-writer` | the committed documentation set, executed as written; release notes | CEO, Product Manager |
| Data Engineer *(conditional)* | `data-engineer` | schema, migrations, integrity, backup/restore drills, query health | CEO, Architect |
| Reviewer | `reviewer` or `reviewer-1..N` | independent second review of **every** deliverable; **the only role that passes review and merges into `main`** | CEO |
| Security Auditor | `security-auditor` | security assessment, red lines, remediation verification | CEO, CTO |

### Roster tiers

| Tier | Roles | Use it for |
|---|---|---|
| Core 6 | `ceo, product-manager, architect, developer-1..N, tester-1..N, reviewer-1..N` | a library or an internal tool; `plan` and `process` ride with the Product Manager/CEO, `tech` with the Architect |
| Shipping 8 | Core + `release-engineer, technical-writer` | anything that must be built, shipped, rolled back and read by someone else |
| Data 9 | Shipping + `data-engineer` | a project that owns persistent state |
| Full 15 | Data + `cto, coo, cfo, designer, security-auditor` | real budget, a UI, or a compliance obligation |

Staff two Reviewers whenever you can: one verifies, another merges.

Minimum viable roster: `ceo, architect, product-manager, project-manager,
reviewer, developer-1, tester-1`. Add `release-engineer` the moment the project
has to ship anywhere, `technical-writer` when a human other than the author must
read the docs, and `data-engineer` only when the project owns persistent state.

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
`reviewer-2`) whenever you can: one verifies, another merges. With a single
Reviewer the same instance must do both, which is allowed but recorded as an
exception (`review.merge_self`) and reported by `audit`. Without a `reviewer` the team cannot pass review
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
| Merge into `main` | a **different** Reviewer than the one who passed it | merge commit, `Archive.md` |
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
teamwork.py pr merge --pr <P-id> --by <another-Reviewer> [--delete-branch]
```

Charters do not restate this; they state what the role produces and decides.

## Boundaries that apply to every role

- Never contact the user; escalate to the CEO and keep working.
- Never approve or merge your own work; only the Reviewer merges.
- Never commit on `main`; work on your own branch.
- Never fake evidence, weaken tests, or claim an unexecuted result.
- Stop at a red line: record it, escalate, do other work meanwhile.
