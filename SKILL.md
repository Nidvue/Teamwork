---
name: teamwork
description: "Run a user prompt to completion with an autonomous multi-agent company: CEO, CTO, COO, CFO, Architect, Product Manager, Project Manager, Designer, Release Engineer, Technical Writer, Data Engineer, Developer(s), Tester(s), Reviewer and Security Auditor. Use when the user invokes /teamwork, asks for a team of sub-agents with roles, wants an org chart of agents that plans, builds, tests and iterates until the goal is met, or wants long-running parallel work with per-agent memory. The user talks only to the CEO; every other agent communicates internally."
---

# /teamwork - autonomous project team

Turn one prompt into a functioning, self-organising team that keeps working until
the goal is verified. The user talks **only to the CEO**. The CEO decomposes the
goal, spawns the roles, and keeps developer/tester/designer lanes running in
parallel. Nothing is ever declared done on an unverified claim.

## Usage

```
/teamwork <prompt>                     # staff and run the project described by <prompt>
/teamwork --team <Name>                # use a specific per-team tree
```

Anything else after the prompt is an instruction to the CEO in plain language
("resume the existing team", "only staff developer and reviewer", "four
developers"): the CEO honours it when writing the roster and `Plan.md`. Only
`--project` and `--team` are CLI flags.

The prompt is the product brief. If it is genuinely ambiguous in a way that
changes what gets built, the CEO asks **one** consolidated round of questions and
then proceeds on recorded assumptions.

The skill is **agent-agnostic and remote-agnostic**: it runs on Pi, Claude Code,
opencode, Codex, Cursor, Windsurf, Gemini CLI or any host that can run
`teamwork.py` and read `AGENTS.md`, and against GitHub, GitLab, Bitbucket,
Gitea/Forgejo, Azure DevOps or a bare server. The protocol is identical; only the
six host operations and the integrity settings are adapted
(`references/Adapters.md`, `references/Remotes.md`).

## Non-negotiable contract

1. **One voice to the user.** Only the CEO reports, asks, and accepts. No other
   agent ever contacts the user.
2. **Run to completion.** Work ends only when every acceptance criterion is
   verified by executed evidence. Blocked is not done; idle with executable work
   left is a bug.
3. **Evidence or `UNVERIFIED`.** No claim about code, tests, CI, or the world
   without a path/command/revision/result. This is enforced: a task cannot be
   marked `done` without recorded evidence.
4. **Independent parallel lanes.** Freeze interfaces first, then developer, tester
   and designer lanes run concurrently against the same contract. Agents do not
   wait for each other.
5. **Code, then tests, then docs.** Documentation never blocks code or tests.
6. **Role-shared state, private workspace.** Memory and the task queue belong to
   the ROLE and are shared by all its instances; only the charter copy, worklog,
   inbox, artifacts, reports and scratch are private to an instance.
7. **Red lines are absolute.** Unsafe, illegal, irreversible or fabrication
   actions stop the lane and escalate to the CEO (see RED LINES).
8. **Nothing unnecessary is kept.** No duplicate docs, no scratch, no build
   output, no secrets in the repository.
9. **Style is automated.** Every role uses the language's canonical formatter,
   linter and type checker (Python: `ruff format` + `ruff check` + `mypy`); the
   fixer runs before the commit and the checker gates the merge. No hand
   formatting, no competing config, no rule weakened to pass. The per-language
   toolchain is in `references/Engineering.md`.
10. **Names are deliberate.** Team directories are PascalCase; file names follow
    the ecosystem, and PascalCase/camelCase are allowed wherever it permits them
    (docs `Architecture.md`, components `ButtonGroup.tsx`). Python modules stay
    `lower_snake_case` because the name is the import path, and tool-mandated
    files are never renamed.
11. **History is minimal and modular.** Commit while you work, then rebase and
    squash before the review: one coherent change-set per commit, `wip`/`fixup`
    commits squashed, rebased onto the latest default branch, one commit per task
    after the squash-merge. Never rebase or force-push a shared branch, or
    anything already on the default branch.

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

Minimum viable roster: `ceo, architect, product-manager, project-manager,
reviewer, developer-1, tester-1`. Add `release-engineer` as soon as anything must
ship, `technical-writer` when someone other than the author must read the output,
and `data-engineer` only when the project owns persistent state. Add CTO/COO/CFO/designer/security-auditor and
extra developer/tester instances when the brief justifies it. Scale writers with
the critical path, not with ceremony. `roles/` paths are relative to this skill
directory. **The Reviewer is not optional**: it is the independent second-review
gate for every deliverable.

## Workspace layout

Two separate worlds: the team's own tree is **hidden** and local; project output
is committed. All team-created names are **PascalCase**.

```text
<project>/
├── AGENTS.md                        # team constitution (auto-loaded, managed block)
├── .agents/skills/<Name>/SKILL.md   # team skills extracted from repeated flows
├── docs/Team/                       # committed project output
│   ├── Project.md  Plan.md  Board.md  Archive.md  Decisions.md
│   ├── Architecture.md  Research.md  Design.md  Risks.md  Costs.md  Release.md
│   └── AuditManifest.json  AuditManifest.md      # written by `ledger export`
├── <code/> <tests/>                 # committed project output
└── .pi/Teamwork/Teams/<Team>/       # the team's own tree (hidden, gitignored)
    ├── TeamMap.md                   # workspace map
    ├── Settings.json                # provider caps + pulse interval
    ├── Criteria.md                  # acceptance criteria + verification evidence
    ├── Tests.md  TestPlan.md        # layered test records + required layers
    ├── Reviews.md                   # PRs and review verdicts
    ├── Disputes.md                  # design/decision challenges
    ├── Skills.md                    # team-skill registry
    ├── Ledger.jsonl                 # append-only, hash-chained audit trail
    ├── Global/                      # CEO-owned shared memory (+ its .gitignore)
    │   ├── GlobalMemory.md
    │   └── GlobalMemoryArchive.md   (created on the first eviction)
    ├── Roles/<Role>/                # SHARED by every instance of the role
    │   ├── ShortTermMemory.md  LongTermMemory.md  ArchivedMemory.md
    │   ├── Role.md                  # charter copy
    │   └── TaskQueue.md
    ├── Agents/<Instance>/           # private to one instance
    │   ├── StartHere.md  WorkLog.md  Inbox.md
    │   └── Artifacts/  Reports/  Scratch/
    └── Runtime/                     # ephemeral
        ├── LedgerHead.json          # fast-path checkpoint for the chain
        ├── Locks/                   # per-file and per-role locks
        ├── Worktrees/<Instance>/    # created by `branch start --worktree`
        └── Slots/<Provider>/<Agent>.slot
```

Each team gets its own `<Team>` tree, named after the project, or `--team Name` / `TEAMWORK_TEAM=Name`,
so several teams in one repository never collide.

**Memory and the task queue belong to the ROLE, not the instance.** `Developer-1`
and `Developer-2` read and write one `Roles/Developer/` memory and claim from one
`Roles/Developer/TaskQueue.md`. `Role.md` is per role; only `StartHere.md`, `WorkLog.md`, `Inbox.md`,
`Artifacts/`, `Reports/` and `Scratch/` are private to an instance.

## Bootstrap procedure (CEO)

Run these in order. Use `SKILL` for this skill's directory.

### 1. Intake

- Restate the prompt as objective + non-goals + constraints in
  `docs/Team/Project.md`.
- Record every acceptance criterion as a machine-checkable record: `criteria add
  --id AC-1 --text '<verifiable statement>' --owner <role>`. `loop` cannot report
  STOP while a criterion is unverified, so this is what "done" actually means.
- Ask the user at most one consolidated question set for genuinely blocking
  ambiguity; otherwise decide, record the assumption, and continue.
- Name the evidence for each criterion (command, test, artifact). An independent
  role verifies it: `criteria verify AC-1 --by <other-role> --evidence '<cmd @rev -> result>'`.
- Declare required test layers per area:
  `tests require --area <a> --layers unit,integration --by <instance> --reason <why>`
  (Architect or CEO). The default is the proportionate core set
  (`unit`, `integration`, `acceptance`) restricted to staffed roles. Each layer is
  designed, built and run by its owner (see `references/Testing.md`).
- **Visual assets are the Designer's call.** The Designer decides what images,
  icons, banners and diagrams a deliverable needs - unasked - then produces and
  improves them. Everything the Designer touches is **user first**: layout,
  typography, fonts and images are judged by the user's task, and the standing
  criteria are simplicity, efficiency, usability and a great experience (real
  text never text-as-image, >= 4.5:1 contrast, >= 16 px body, explicit font
  fallback chain, no external font dependency in an SVG). Vector first
  (SVG / diagram-as-code); for a raster, `imaging probe` picks the best available
  text-to-image model (cloud first, else local, else SVG). The full process - one
  prompt per asset, four-plus candidates off one seed base, a visual review of
  every candidate, improvement rounds until it passes, integration and evidence -
  plus the privacy and licence red lines live in `roles/designer.md`; the asset
  record lives in `docs/Team/Design.md`. Never send private data to a cloud image
  model, never ship an asset nobody reviewed, and never lower a criterion to make
  an asset pass.

### 2. Workspace, repository, constitution

```sh
python3 "$SKILL/scripts/teamwork.py" init --agents ceo,cto,coo,cfo,architect,\
product-manager,project-manager,designer-1,developer-1,developer-2,tester-1,reviewer
python3 "$SKILL/scripts/teamwork.py" agents-md          # write/patch <project>/AGENTS.md
python3 "$SKILL/scripts/teamwork.py" map                # confirm layout + repo structure
```

`init` creates the git repository if the project has none, writes a `.gitignore`
that keeps `.pi/`, secrets, caches and build output out of the repository, and
makes the initial commit. If no git identity is configured it warns instead of
inventing one - resolve that with the user before the first commit. Commit
`AGENTS.md` and the project documents as the first real commit, once a task
scaffold exists.

Then seed global memory with the facts every agent will otherwise re-ask:

```sh
python3 "$SKILL/scripts/teamwork.py" global "Objective: <one line>" --key objective --importance 5 --pin
python3 "$SKILL/scripts/teamwork.py" global "Stack: <lang/framework>; build: <cmd>; test: <cmd>" --key build
python3 "$SKILL/scripts/teamwork.py" global "Repo layout: <src/ tests/ docs/>" --key layout
```

### 3. Plan and freeze interfaces (the parallelism gate)

Dispatch in parallel, before any implementation:

- **Product Manager** - `Research.md`: competitors, state of the art, popular
  solutions, comparison table, gap analysis, recommendation (sources + dates).
- **Architect** - `Architecture.md` with **frozen interface contracts** plus test
  seams; `Decisions.md` for irreversible choices.
- **CTO** - stack, build/test/release commands, feasibility, dependency review.
- **COO** - `Risks.md`, process, blockers, duplicate-work risks.
- **CFO** - `Costs.md` if the work has a real cost dimension.
- **Project Manager** - `Plan.md`: milestones -> dependency-ordered tasks with
  role, priority, artifacts, evidence, and the parallel lanes.

(All of the above live in `docs/Team/`.)

Everything else waits only on the interface freeze, not on each other.

### 4. Staff and dispatch

Spawn long-lived teammates with the `teams` tool (shared task list, mailbox,
auto-claim of unblocked tasks) and give each one its brief:

```text
teams({ action: "delegate", tasks: [
  { text: "architect: ...", assignee: "architect" },
  { text: "developer-1: ...", assignee: "developer-1" },
  { text: "tester-1: ...", assignee: "tester-1" }
]})
```

Each dispatched task packet must contain: task id, objective, the frozen
interface to build against, file/component boundary, acceptance evidence, the
artifact path, dependencies, and the stop/ask condition. Point every teammate at
its startup routine:

```text
You are <name>. Read .pi/Teamwork/Teams/<Team>/Roles/<Role>/Role.md and
.pi/Teamwork/Teams/<Team>/Agents/<Instance>/StartHere.md, then run:
  teamwork.py load <name>
  teamwork.py task next <name>
Start that task immediately. Work only in your lane. Report evidence, then take
the next executable task yourself.
```

For bounded one-shot work (a review, a research brief, a verification pass), use
`subagent` with a matching role agent instead of a long-lived teammate.

### 5. Run the loop

One iteration is: re-plan -> dispatch -> work in parallel -> independent review ->
rework -> integrate. The loop repeats automatically until `teamwork.py loop`
reports STOP.

- Teammates auto-claim the highest-priority unblocked task; when one finishes it
  submits for review and takes the next one.
- **Every deliverable is second-reviewed by the Reviewer**, independently: code,
  unit tests, integration/E2E tests, docs, design specs, plans, research, cost
  models and risk registers. A fail goes straight back to the owner with findings,
  the owner fixes it, and it is re-reviewed. Review failures are counted: at
  3 the Reviewer must open a dispute so the tribunal rules (see
  `references/Dissent.md`), and `loop` blocks STOP until it does.
- **Every agent tests its own layer, comprehensively and in parallel**: `goal`
  CEO · `requirements` Product Manager · `plan` Project Manager · `tech` CTO ·
  `release` Release Engineer · `data` Data Engineer · `process` COO · `cost` CFO ·
  `system` Architect · `ui` Designer · `docs` Technical Writer · `unit` Developer ·
  `integration` Tester · `acceptance` Reviewer · `security` Security Auditor. Each role designs, implements and executes its own tests and
  evidences the run. `tests plan` shows the matrix, role coverage and gaps;
  `loop` blocks STOP while a required layer is missing/failing or a role has
  designed no tests at all.
- **Review is a parallel lane.** `reviewer-1..N` claim *different* deliverables
  from the shared review queue at the same time (`review --queue`); one claim per
  deliverable, the merger is always a different Reviewer from the one who
  approved, high-risk work gets two Reviewers on purpose, nobody reviews their own
  contribution, and findings union - a deliverable passes only when no open
  finding remains on the revision.
- The CEO keeps the interface contract stable, arbitrates conflicts, resolves
  duplicate work, and updates global memory.
- The Project Manager chases stalled tasks and duplicates and refreshes
  `Plan.md`/`Board.md`; the COO keeps `Risks.md` honest; the Product Manager
  keeps `Research.md` current.
- The team is self-managing: the CEO resolves internal conflicts and disputes
  (tribunal for escalations) without involving the user. The user is contacted
  only for an authorization, a goal/scope/budget change, a blocking ambiguity,
  or the final report.
- Periodically:

```sh
python3 "$SKILL/scripts/teamwork.py" criteria list    # are the goals actually met?
python3 "$SKILL/scripts/teamwork.py" tests plan       # layered test coverage and gaps
python3 "$SKILL/scripts/teamwork.py" board
python3 "$SKILL/scripts/teamwork.py" review --queue   # Reviewer's work list
python3 "$SKILL/scripts/teamwork.py" audit            # fabricated completions, stale work, duplicates, link health
python3 "$SKILL/scripts/teamwork.py" links            # markdown links, URLs, back-links
python3 "$SKILL/scripts/teamwork.py" pulse --commit   # idle lanes -> assignment
python3 "$SKILL/scripts/teamwork.py" parallel         # free slots vs ready work
python3 "$SKILL/scripts/teamwork.py" loop             # may we stop yet?
python3 "$SKILL/scripts/teamwork.py" clean            # remove temp files
```

- Report to the user at milestones: what changed, evidence, blockers, next. Never
  report progress that is not backed by evidence.

### 5b. Keep the lanes full: the CEO pulse

After dispatching, the CEO **re-wakes on an interval**, looks for idle lanes, and
hands them runnable work immediately. This is not optional and not manual: arm a
recurring wake-up once, and act on every wake.

```sh
python3 "$SKILL/scripts/teamwork.py" pulse --commit --interval 5
```

`pulse` prints idle lanes, ready work per role, and a dispatch plan; `--commit`
applies the assignments (claiming the task and recording which instance owns it).
Exit code 3 means "nothing to dispatch" - then check blocked tasks and disputes.

An instance counts as **busy** when it holds a provider slot or has a task in
`doing`/`selfcheck` claimed by it. Everything else is idle and must be fed.

Arm the recurring wake-up from the leader session:

```text
schedule_prompt({
  action: "add",
  name: "teamwork-pulse",
  type: "cron",
  schedule: "*/5 * * * *",
  prompt: "Teamwork pulse. Run `python3 <SKILL>/scripts/teamwork.py pulse --commit`. \
           Then: (1) for every assignment it reports, message that agent to start it now; \
           (2) for every idle lane it reports with no matching work, assign the highest-\
           priority unblocked task of its role, or fold the lane; (3) unblock anything \
           stuck; (4) if the Reviewer has deliverables waiting, tell it to review them. \
           Report one short line. Never stop the team while `loop` says CONTINUE."
})
```

- Interval: `PulseMinutes` in `Settings.json`, default **5** minutes. Use a longer
  interval for long-running lanes, a shorter one near the end of a milestone.
- The pulse must never be the only thing keeping the team alive: instances
  self-serve with `task next` between pulses.
- Disarm it when the team closes:
  `schedule_prompt({action: "remove", jobId: "<id>"})` (list with
  `schedule_prompt({action: "list"})`).
- If a wake reports idle lanes *and* ready work and nothing moves, that is a
  process defect: fix the assignment path, do not let the lane sit.

### 5c. Push in stages, and certify both signals

Two duties that keep the remote and the confidence level honest:

- **Release Engineer - push after review, per milestone.** The Release Engineer is
  the role that pushes commits to the shared remote, and only once the Reviewer
  has passed that revision with no open finding. Push after each reviewed +
  merged deliverable rather than batching everything to the end, so the remote
  never drifts far from local `main`. Locally, before the push: build, tests,
  `privacy_scan.py --tree --history` and the link check must be green on exactly
  that revision. After the push, watch CI and confirm it is green **on that SHA**.
  A red run is routed to its owner from the log (code -> Developer, test ->
  Tester, contract -> Architect, workflow/packaging/flake -> Release Engineer,
  scope -> CEO) and re-run after the fix. Force-push and published-history
  rewrites need the CEO's explicit authorization; tags and public releases are
  the CEO's step, prepared and verified by the Release Engineer.
- **Tester - certify local *and* CI.** The Tester runs the layers locally and then
  confirms the same result in CI on the pushed revision, job by job across the OS
  and Python matrix. A green local run with a red CI run is a failure, and so is
  the reverse. Any failure - local or CI - is filed to the owning agent with the
  exact command, expected vs actual, log excerpt, SHA and run id, and nobody
  reports a suite as passing while the matching CI run is red.
- **CI triggers are path-filtered: code in, prose and media out.** Documentation,
  images and other non-code edits must not run the code matrix; they get a cheap
  docs workflow instead (link health, privacy scan, `mkdocs build --strict`).
  Anything that ships - `src/`, `scripts/`, `tests/`, packaging, workflows,
  `roles/`, `references/`, `templates/` - always runs the full matrix. Never
  ignore a path that ships, and keep the two path lists in sync.

- **Everyone keeps the tree clean.** No comment the code already gives you, no
  commented-out code, no `TODO`/`FIXME` without a tracked task id; delete temp and
  stale files in the same task (`teamwork.py clean` plus the rest by hand); keep
  one canonical home per file and an obvious structure, and leave the working tree
  cleaner than you found it. A reviewer who cannot tell deliverable from debris
  fails the task.

Both duties are evidence, not ceremony: `tests plan` and the task record must name
the local result **and** the CI run (id + conclusion) for the certified revision.

### 5d. Any agent host, any git host

- **Agent host.** The engine, the workspace format, the criteria records, the
  two-stage gate, the ledger and the test matrix are host-independent. Only six
  operations need a host mechanism - spawn a teammate, delegate one-shot work,
  message an agent, inspect state, re-wake on a schedule, close the team. Name the
  operation, then use the adapter in `references/Adapters.md` (Pi `teams`/`subagent`/
  `schedule_prompt`, Claude Code agents + host cron, opencode agents, a host CLI in
  a `bash` job, or the files themselves). Never hard-code a host tool in a
  normative step, and never fake a tool the host lacks: record the degraded mode.
  The protocol must still complete with no scheduler and no teammate tool at all -
  one agent wearing the hats sequentially, with the same gates.
- **Git host.** The Release Engineer guarantees repository and CI integrity on
  whatever host is in use: protected default branch, **no force-push**, no
  deletion, required status checks on the exact revision, at least one non-author
  approval, squash-only merges with the source branch deleted, protected `v*`
  tags created only by the CEO, and least-privilege CI with no secret in the tree.
  Policy and the per-host mapping are in `references/Remotes.md`. Record the actual
  settings from the host API as evidence and re-read them to detect drift; an
  unprotected setting is a defect on par with a red build.

### 6. Close

Completion gate - all of:

- [ ] Every acceptance criterion in `docs/Team/Project.md` has evidence from a
      revision.
- [ ] Every deliverable passed its own self-check and an independent Reviewer
      verdict with reproducible evidence (code, tests, docs, design, plans,
      research), and appears in `docs/Team/Archive.md`.
- [ ] Every required test layer for every area passes, each run by its owning
      role (`tests plan` reports no gaps).
- [ ] No open high-severity security finding; no unresolved red-line escalation.
- [ ] Every task branch has been reviewed and merged into `main` by the
      Reviewer, and the merged branch is deleted; no work remains only on a branch.
- [ ] Every staffed role has designed, implemented and run its own test layer,
      and every area's required layers pass (`tests plan` reports no gaps).
- [ ] `ledger verify` reports an intact chain, `audit` reports no provenance gaps,
      and the final `ledger export` manifest is committed with the milestone.
- [ ] `teamwork.py loop` reports STOP and `teamwork.py audit` reports zero
      problems.
- [ ] Docs match merged code; no scratch or temp files left; nothing unnecessary
      committed.
- [ ] Final user report: deliverable, how to run it, evidence table, known
      limitations, follow-ups.

Then stop the team (`teams({action:"team_done"})`) and deliver the report.

## Reference files (read on demand)

`SKILL.md` is the operating procedure. The policy detail lives in `references/`;
read the one you need instead of the whole skill.

| File | Read it for |
|---|---|
| `references/Evidence.md` | evidence shape, claim discipline, red lines, what to escalate |
| `references/Dissent.md` | independent decisions, challenging a design, the 3-round cap, the CEO+CTO+CFO tribunal |
| `references/State.md` | role-shared memory (short/long/global) and the priority task queue |
| `references/Concurrency.md` | provider caps, slot leases, parallelism plan, reuse |
| `references/Docs.md` | markdown structure, concision rules, bidirectional links |
| `references/Engineering.md` | commit identity, commit style, Git LFS, branch/PR/merge, worktrees, build economy |
| `references/Roles.md` | the full roster, handoffs, decision rights and boundaries |
| `references/Testing.md` | the 15 role-owned test layers, how each is designed/run, dedupe and required coverage |
| `references/Audit.md` | what is recorded, provenance, the hash-chained ledger, internal and external audit |
| `references/Adapters.md` | running the team on any agent host: the six operations, the Pi / Claude Code / opencode / Codex / Cursor / generic mapping, installation and degraded modes |
| `references/Remotes.md` | repository and CI integrity on any git host: branch protection, required checks, merge strategy, protected tags, least privilege, and the GitHub / GitLab / Bitbucket / Gitea / Azure mapping |

Team skills: when a flow is repetitive, widely reused and must stay consistent,
the owning role extracts it into `<project>/.agents/skills/<name>/SKILL.md` and
shares it with its peers (`skill create`, `skill share`, `skill candidates`). The
file is project output: it goes through the normal branch, commit, PR and review.

Recording and audit: every mutation appends to the hash-chained `Ledger.jsonl`
(`ledger verify`, `ledger show`, `trace <id>`), and `ledger export` writes
`docs/Team/AuditManifest.json` for verification by anyone. A broken chain blocks STOP.

Stop condition: acceptance criteria are records, not checkboxes -
`criteria add|verify|list`, `loop`. Reclaim stuck work with
`task reclaim <role> <T-id> --as <Instance> --reason "..."`.

## Two-stage quality gate

Every deliverable passes **two** gates, in this order, before it counts as done:

1. **Self-check (the author).** After finishing the work, the owner reviews their
   own diff and *runs* a self-test, then records the result. This is mandatory -
   you cannot submit work you have not checked yourself.
2. **Independent review (the Reviewer).** The Reviewer verifies the submitted
   result from scratch and either passes it (task becomes `done`, result is
   archived) or fails it (task returns to the owner with findings).

Task lifecycle for a deliverable:

```text
todo -> doing -> selfcheck -> review -> done (merged into main by the Reviewer)
         |        ^            |
   branch start   |            v  (fail)
                  +-------- doing
```

```sh
# 1) owner finishes the work and starts their own check
teamwork.py task set developer-1 T-0007 --status selfcheck
# 2a) self-check found a problem -> back to doing
teamwork.py selfcheck developer-1 T-0007 --by developer-1 --result fail \
    --note "off-by-one at the empty-input boundary" \
    --test "go test -run TestBoundary @abc123 -> FAIL"
# 2b) self-check passed -> records the check AND submits for review
teamwork.py selfcheck developer-1 T-0007 --by developer-1 \
    --note "re-read the diff: boundary, error paths, docs updated" \
    --test "go test ./internal/x @def456 -> ok 12 tests"
# 3a) Reviewer fails it -> task returns to the owner as `doing`, findings recorded
teamwork.py review developer-1 T-0007 --by reviewer --result fail \
    --findings "missing empty-input test; go test -run TestEmpty -> FAIL @abc123"
# 3b) Reviewer passes it -> task becomes `done` and is archived
teamwork.py review developer-1 T-0007 --by reviewer --result pass \
    --evidence "go test ./... @def456 -> ok 42 tests"
```

Mechanical enforcement:

- `task set --status review` is refused until `self_check: passed`; a passing
  self-check requires a `--test` line - reading your own diff is not a test.
- only the owner may self-check their own task (`--by <owner>`), and only the
  Reviewer may review it; an author can never close a `review=required` task.
- a `review --result pass` appends the accepted result to
  `docs/Team/Archive.md` (what, who, verified how, which revision) - the team's
  evidence ledger. Read it with `teamwork.py archive [--agent X]`.
- a re-submitted fix is reviewed from scratch; there is no round limit, but at
  fail, fix, re-check, re-submit, re-review until it passes.
- if a finding turns into a design disagreement, use the dispute protocol.

This applies to code, unit tests, integration/E2E tests, documentation, design
specifications, plans, research briefs, architecture contracts, cost models and
risk registers.

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

# bootstrap (staff two Reviewers when you can)
python3 $S init --agents ceo,architect,product-manager,project-manager,reviewer-1,reviewer-2,\
developer-1,developer-2,tester-1
python3 $S agents-md && python3 $S repo && python3 $S map

# plan and shared state
python3 $S criteria add --id AC-1 --text "<verifiable statement>" --owner developer --by ceo
python3 $S tests require --area auth --layers unit,integration,acceptance --by ceo --reason "core"
python3 $S tests add --layer unit --area auth --command "go test ./internal/auth"
python3 $S tests run TS-0001 --by developer-1 --result pass --evidence "<cmd> @<rev> -> <result>"
python3 $S global "<shared fact>" --key k --importance 4
python3 $S remember developer-1 "<fact>" --key k --importance 4 --by developer-1 --src T-0007 --rev <sha>
python3 $S task add developer "<task>" --priority P0 --deps architect:T-0002

# work: own branch -> commit -> self-check -> PR -> review -> Reviewer merge
python3 $S task next developer-1
python3 $S branch start --agent developer-1 --task T-0007 [--worktree]
python3 $S commit --role developer --type feat --task T-0007 --area auth \
    --goal "..." --deliverable "..." --why "..." --status "..." --result "<cmd> @<rev> -> result" --all
python3 $S selfcheck developer T-0007 --by developer-1 --note "<what you re-read>" \
    --test "<cmd> @<rev> -> <result>"
python3 $S pr open --agent developer-1 --task T-0007
python3 $S review developer T-0007 --by reviewer-1 --result pass --evidence "<verify cmd @<rev> -> result>"
python3 $S pr merge --pr P-0001 --by reviewer-2          # a DIFFERENT Reviewer merges

# reuse: extract a repeated flow and share it with same-role peers
python3 $S skill candidates
python3 $S skill create --name <kebab-name> --role developer --by developer-1 --for "<when to use>"
python3 $S skill share <kebab-name> --by developer-1

# keep the lanes full and the trail honest
python3 $S board && python3 $S pulse --commit && python3 $S parallel
python3 $S ledger show --tail 20 && python3 $S ledger verify && python3 $S ledger export
python3 $S trace T-0007
python3 $S task reclaim developer T-0007 --as Developer-2 --reason "owner went silent"
python3 $S tests plan && python3 $S audit && python3 $S links && python3 $S loop
python3 $S dispute open --by developer-1 --against architect --topic "..." --evidence "..."
python3 $S slot acquire --agent developer-3 --provider deepseek --task T-0012
python3 $S slot renew --agent developer-3 && python3 $S slot release --agent developer-3
python3 $S clean
```

Team lifecycle: `teams({action:"delegate", tasks:[...]})` to staff,
`teams({action:"message_dm"/"message_broadcast"})` to coordinate,
`teams({action:"board"})`-equivalent via the script to inspect, and
`teams({action:"team_done"})` to close.
