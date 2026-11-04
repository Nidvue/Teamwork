# Bootstrap - the one-time flows

Owner: CEO.

Reference for the /teamwork skill. Loaded on demand: `SKILL.md` carries the
always-on contract and the run loop; this file carries the steps a project
needs once - intake, the workspace, the plan, staffing - and the close.

Related: [SKILL.md](../SKILL.md)

## Steps 1-4: intake, workspace, plan, staffing

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
python3 "$SKILL/scripts/teamwork.py" init --roster slim   # ceo, architect, developer,\
tester, reviewer-1, reviewer-2 - or --roster standard|full, or --agents for an exact list
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

The host may offer a long-lived teammate tool or none at all; either way each lane is a bounded `subagent`-style run that
reads the role charter and the queue and takes its own work, so the fan-out is
one call per lane and the CEO stays free while they run:

```text
<teammate tool>(agent: "architect", task: "<packet>", background: true)
<teammate tool>(agent: "developer", task: "<packet>", background: true)
<teammate tool>(agent: "tester",    task: "<packet>", background: true)
```

The concrete name per host - `subagent`, `Task`, a CLI job - is the adapter table
in `references/Adapters.md`; the packet and the queue are the same everywhere.

A dependent multi-step batch is one workflow call: the workflow owns the fan-out,
each child gets its own task text and the parent gets every child's output back
(`runs.all([...])` on hosts that offer workflows). Use worktree isolation only on
a clean tree; otherwise run the lanes in the shared checkout and require
`commit --paths` so no lane sweeps a peer's uncommitted work.

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

## Step 5 stays in SKILL.md

The run loop (`### 5. Run the loop` and `5a`-`5j`) is the daily operating
procedure, so it stays always-on in `SKILL.md` and is not repeated here.

## Step 6: close

When the queue is empty and `loop` is about to report STOP, load the `ceo-audit-close`
skill and follow it exactly: freeze the revision, verify the chain before the gates,
check the archive against the tree, export the manifest last, and report from records.
A trigger line is what makes an on-demand skill exist - an unnamed skill is dead text
nobody is told to load, and `teamwork.py harness lint` fails a tree that has one.

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

Then stop the team: end every live lane with the host's stop action, confirm
`loop` still reports STOP on the final head, and deliver the report.
