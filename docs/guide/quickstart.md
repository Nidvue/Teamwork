# Quickstart

Owner: Technical Writer.

Related: [Home](../index.md) · [Installation](install.md) · [CLI reference](cli.md) · [Architecture](architecture.md)

Start a team in an empty project in about a minute. Step 1 installs the skill in
one clone, step 2 is a single prompt to your agent host. The later steps show the
engine commands the skill runs, so you can inspect or steer the machine yourself.
The example uses `demo/` as the project directory; paths in the output are elided
for readability.

## 1. Install the skill

```console
$ mkdir -p .agents/skills
$ git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork
$ rm -rf .agents/skills/teamwork/.git
```

Dropping the nested `.git` keeps the skill as plain tracked files instead of an
empty submodule in a fresh clone. Re-scan or reload skills in the host. A
user-level clone (`~/.agents/skills/teamwork`, keep `.git` to pull updates) works
the same way; if the host names its own skills directory, clone there instead.
Python 3.9+ runs the bundled engine; there are no dependencies to install.
Details: [Installation](install.md).

## 2. Ask for the team

```text
$ mkdir -p demo && cd demo
> use the teamwork skill: build a small URL shortener with a CLI, tests and docs
```

The CEO reads the skill, then staffs the roster, records the acceptance criteria,
writes `AGENTS.md` and `docs/Team/`, freezes the interfaces and opens the lanes.
Ambiguity is resolved in one consolidated round of questions; everything else is a
recorded decision.

Behind that prompt the skill runs the engine. These are the commands you can type
yourself to see the same workspace it created:

```console
$ teamwork init --agents ceo,architect,product-manager,project-manager,reviewer-1,developer-1,tester-1
teamwork: workspace ready at .pi/Teamwork/Teams/Demo
teamwork: global memory .pi/Teamwork/Teams/Demo/Global/GlobalMemory.md
teamwork: memory + task lists are per ROLE (shared by its instances)
  - ceo              shared: .pi/Teamwork/Teams/Demo/Roles/CEO  instances: CEO
  - architect        shared: .pi/Teamwork/Teams/Demo/Roles/Architect  instances: Architect
  - product-manager  shared: .pi/Teamwork/Teams/Demo/Roles/ProductManager  instances: ProductManager
  - project-manager  shared: .pi/Teamwork/Teams/Demo/Roles/ProjectManager  instances: ProjectManager
  - reviewer         shared: .pi/Teamwork/Teams/Demo/Roles/Reviewer  instances: Reviewer-1
  - developer        shared: .pi/Teamwork/Teams/Demo/Roles/Developer  instances: Developer-1
  - tester           shared: .pi/Teamwork/Teams/Demo/Roles/Tester  instances: Tester-1

teamwork: created AGENTS.md
```

Add a second Reviewer (`reviewer-2`) whenever you want one Reviewer to verify and
a different one to merge; with a single Reviewer the tool records the combined
duty as an explicit exception.

`teamwork agents-md` writes or patches the constitution in an existing project, so
a team can join a repository that already has an `AGENTS.md`.

## 3. Check the layout

```console
$ teamwork map
# Team map  (.pi/Teamwork/Teams/Demo)
project docs (committed, one owner each, no duplicates)
  [x] Project.md           owner=CEO
  [x] Plan.md              owner=ProjectManager
  ...
roles (shared memory + queue) and their instances (private scratch)
  architect        open= 0 mem(short/long)=0/0  instances=1 [Architect]
  ...
```

## 4. Record what "done" means

Acceptance criteria are machine records, not checkboxes. `loop` cannot report
`STOP` while one is unverified.

```console
$ teamwork criteria add --id AC-1 --text "CLI prints the version and exits 0" --owner developer --by ceo
# added AC-1: CLI prints the version and exits 0
$ teamwork criteria add --id AC-2 --text "pytest passes on the test matrix" --owner tester --by ceo
```

## 5. Add work to a role queue

Tasks belong to a ROLE and are shared by every instance of that role.

```console
$ teamwork task add developer "Implement the feature" --priority P0 --body "Ship it with unit tests"
teamwork: developer queue + T-0001 [P0] Implement the feature
```

## 6. Run the CEO loop

One iteration is: re-plan, dispatch, work in parallel, independent review,
rework, integrate. `loop` is the mechanical stop check:

```console
$ teamwork loop
# Loop status (.pi/Teamwork/Teams/Demo)

## acceptance criteria (machine records)
- [ ] AC-1 CLI prints the version and exits 0 (status=open)
- [ ] AC-2 pytest passes on the test matrix (status=open)

## work in flight
- todo: 1
-     developer T-0001 [P0] Implement the feature

> CONTINUE
  ! 2 acceptance criteria unverified
  ! no layered test records
  ! 1 task(s) not finished
```

Keep the lanes full with the CEO pulse and check parallelism:

```console
$ teamwork pulse --commit --interval 5
$ teamwork parallel
$ teamwork board
```

Stop only when `loop` prints `STOP`, every criterion is verified, and `audit`
reports no problems.

## What appears under `.pi/Teamwork`

Everything the team generates lives in a hidden, gitignored tree; only project
output is committed.

```text
<project>/
├── AGENTS.md                        # team constitution (auto-loaded)
├── docs/Team/                       # committed project output
└── .pi/Teamwork/Teams/<Team>/       # the team's own tree (hidden, gitignored)
    ├── TeamMap.md  Settings.json
    ├── Criteria.md                  # acceptance criteria + evidence
    ├── Tests.md  TestPlan.md         # layered test records
    ├── Reviews.md  Disputes.md  Skills.md
    ├── Ledger.jsonl                 # append-only, hash-chained audit trail
    ├── Global/                      # CEO-owned shared memory
    ├── Roles/<Role>/                # shared by every instance of the role
    │   ├── ShortTermMemory.md  LongTermMemory.md
    │   ├── Role.md  TaskQueue.md
    ├── Agents/<Instance>/           # private to one instance
    │   ├── StartHere.md  WorkLog.md  Inbox.md
    │   └── Artifacts/  Reports/  Scratch/
    └── Runtime/                     # ephemeral locks, slots, worktrees
```

Each team gets its own `<Team>` tree (named after the project, or `--team Name`,
or `TEAMWORK_TEAM=Name`), so several teams can share one repository without
colliding.

## Next steps

- Hand each teammate its startup routine: `teamwork task next <instance>`.
- Freeze interfaces in `docs/Team/Architecture.md` before parallel work starts.
- Read the [CLI reference](cli.md) for the full command surface.
