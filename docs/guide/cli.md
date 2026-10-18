# CLI reference - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Installation](install.md) · [Quickstart](quickstart.md) · [Architecture](architecture.md) · [CI pipeline](ci.md)

Complete reference for the `teamwork` command-line interface. Every option below
was produced from `teamwork <cmd> --help`.

## Invocation

Three forms are equivalent:

```console
$ teamwork <command> ...            # console script (pip install)
$ python -m teamwork <command> ...  # module
$ python3 scripts/teamwork.py <command> ...   # checkout compatibility shim
```

## Global options

| Option | Meaning |
|---|---|
| `--project PROJECT` | Project directory (default: current directory). |
| `--team TEAM` | Team name (default: the project directory name). |
| `--version` | Print `teamwork <version>` and exit 0. |
| `-h`, `--help` | Show help for the command or subcommand. |

`--project` and `--team` are accepted by every subcommand so each command can
target a specific workspace.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `1` | Generic error, or a gate refusal (e.g. `loop` says CONTINUE). |
| `3` | Nothing to dispatch (`pulse`). |
| `4` | Lock timeout. |
| `5` | Evidence/gate refusal. |

## Setup and workspace

### `init`

```text
teamwork init [--agents AGENTS] [--force] [--no-git]
```

Create the team workspace and memory files; creates the git repository unless
`--no-git`.

| Option | Meaning |
|---|---|
| `--agents` | Comma-separated instance names, e.g. `ceo,architect,developer-1,tester-1`. |
| `--force` | Overwrite existing files. |
| `--no-git` | Do not create or check the git repository. |

### `repo`

```text
teamwork repo [--no-commit]
```

Ensure a git repository exists and report its status. `--no-commit` skips the
initial commit.

### `map`

```text
teamwork map
```

Print the workspace map and the detected repository layout.

### `agents-md`

```text
teamwork agents-md
```

Create or update the managed teamwork block in `<project>/AGENTS.md`.

### `clean`

```text
teamwork clean [--all] [--dry-run] [--limit LIMIT]
```

Remove scratch/temp files; never touches tracked files.

| Option | Meaning |
|---|---|
| `--all` | Empty `Scratch/` entirely, not only temp patterns. |
| `--dry-run` | Show what would be removed. |
| `--limit` | Cap the number of files removed. |

### `agents`

```text
teamwork agents
```

List agent directories in the workspace.

## Tasks, board and scheduling

### `task`

```text
teamwork task {add,list,next,set,reclaim,rm} ...
```

Manage a role's shared priority queue.

#### `task add`

```text
teamwork task add AGENT TITLE [--priority {P0,P1,P2,P3}]
    [--status {todo,doing,blocked}] [--deps DEPS] [--shared SHARED]
    [--tags TAGS] [--body BODY] [--evidence EVIDENCE]
    [--claimed-by CLAIMED_BY] [--no-review]
```

| Option | Meaning |
|---|---|
| `--deps` | Comma list of dependencies; cross-role as `role:T-0001`. |
| `--shared` | Shared board / issue / PR reference. |
| `--body` | Acceptance criteria / notes. |
| `--claimed-by` | Assign to a specific instance (default: role pool). |
| `--no-review` | Mark a chore that does not need Reviewer sign-off. |

New tasks cannot start as `review` or `done`; the gates own those states.

#### `task list`

```text
teamwork task list [AGENT] [--all] [--status {todo,doing,selfcheck,review,blocked,done,dropped}]
```

List tasks, priority ordered.

#### `task next`

```text
teamwork task next AGENT [--peek]
```

Atomically claim the highest-priority executable task of the role. `--peek` does
not claim it.

#### `task set`

```text
teamwork task set AGENT HANDLE [--claimed-by CLAIMED_BY]
    [--status {todo,doing,selfcheck,review,blocked,done,dropped}]
    [--priority {P0,P1,P2,P3}] [--deps DEPS] [--title TITLE]
    [--evidence EVIDENCE] [--force REASON]
```

Update status, priority or dependencies. `--force` overrides evidence/self-check
/review gates, requires a reason, and is recorded and audited.

#### `task reclaim`

```text
teamwork task reclaim AGENT HANDLE --as BY --reason REASON
```

Take back a task whose owner went silent.

#### `task rm`

```text
teamwork task rm AGENT HANDLE --by BY [--force REASON]
```

Remove a task (own role only).

### `board`

```text
teamwork board
```

Cross-agent board with counts and each role's next task.

### `parallel`

```text
teamwork parallel
```

Show free concurrency slots, ready work, and how many lanes to start.

### `pulse`

```text
teamwork pulse [--commit] [--interval INTERVAL]
```

CEO wake-up: print idle lanes, ready work and a dispatch plan. `--commit` applies
the assignments now. `--interval` stores the pulse interval in minutes. Exit code
`3` means nothing to dispatch.

### `slot`

```text
teamwork slot {acquire,release,list,renew,reap} ...
```

Reserve/release provider concurrency slots (respect the caps in
`Settings.json`).

#### `slot acquire`

```text
teamwork slot acquire --agent AGENT [--provider PROVIDER] [--task TASK] [--wait WAIT]
```

Take a slot; `--wait` seconds waits for a free one.

#### `slot release`

```text
teamwork slot release --agent AGENT [--provider PROVIDER] [--by BY] [--force REASON]
```

Give a slot back.

#### `slot list`

```text
teamwork slot list [--provider PROVIDER]
```

Show slots per provider.

#### `slot renew`

```text
teamwork slot renew --agent AGENT [--provider PROVIDER]
```

Extend the lease while still working.

#### `slot reap`

```text
teamwork slot reap [--provider PROVIDER]
```

Drop dead or stale slots.

## Memory

### `load`

```text
teamwork load AGENT [--limit LIMIT]
```

Print the ROLE's short-term memory (startup context).

### `remember`

```text
teamwork remember AGENT TEXT [--by BY] [--src SRC] [--rev REV]
    [--layer {short,long}] [--key KEY] [--importance IMPORTANCE]
    [--tags TAGS] [--pin]
```

Add or update an entry in the ROLE's shared memory.

### `global`

```text
teamwork global TEXT [--key KEY] [--importance IMPORTANCE] [--tags TAGS] [--pin]
```

Add or update an entry in global shared memory (CEO-owned).

### `recall`

```text
teamwork recall [QUERY] [--agent AGENT] [--all] [--global]
    [--layer {both,short,long}]
```

Search memory.

### `touch`

```text
teamwork touch AGENT HANDLE [--layer {short,long}]
```

Mark an entry as used; `HANDLE` is an `M-0003` id, a key, or a substring.

### `forget`

```text
teamwork forget AGENT HANDLE [--layer {short,long}]
```

Delete an entry.

### `consolidate`

```text
teamwork consolidate [--agent AGENT] [--all] [--dry-run]
```

Promote stale short-term entries and evict long-term overflow.

### `stats`

```text
teamwork stats [--agent AGENT] [--all]
```

Show memory sizes and cap violations.

## Criteria and tests

### `criteria`

```text
teamwork criteria {add,verify,reopen,rm,list} ...
```

Acceptance criteria as records; they are the STOP condition.

#### `criteria add`

```text
teamwork criteria add --id ID --text TEXT --owner OWNER --by BY
```

Record a verifiable statement (`AC-1`, `AC-login`, ...) and who records it.

#### `criteria verify`

```text
teamwork criteria verify ID --by BY [--evidence EVIDENCE] [--test TEST] [--rev REV]
```

Mark verified with independent evidence. `--by` must not be the owner.

#### `criteria reopen`

```text
teamwork criteria reopen ID --by BY [--reason REASON]
```

Clear a verification.

#### `criteria rm`

```text
teamwork criteria rm ID --by BY [--force REASON]
```

Remove a criterion (CEO only).

#### `criteria list`

```text
teamwork criteria list
```

Show criteria and status.

### `tests`

```text
teamwork tests {add,run,require,rm,plan,list} ...
```

Layered tests, each owned and run by its own role.

#### `tests add`

```text
teamwork tests add --layer LAYER [--area AREA] [--owner OWNER]
    [--task TASK] [--command COMMAND] [--no-owner-check] [--force REASON]
```

`--layer` is one of `goal,requirements,plan,tech,release,data,process,cost,system,ui,docs,unit,integration,acceptance,security`.

#### `tests run`

```text
teamwork tests run ID --by BY --result {pass,fail} --evidence EVIDENCE
    [--rev REV] [--command COMMAND] [--force REASON]
```

Record a layer run.

#### `tests require`

```text
teamwork tests require --area AREA --layers LAYERS --by BY
    [--reason REASON] [--force REASON]
```

Declare which layers an area must cover.

#### `tests rm`

```text
teamwork tests rm ID --by BY [--force REASON]
```

Remove a test record.

#### `tests plan`

```text
teamwork tests plan
```

Coverage matrix, role coverage and gaps.

#### `tests list`

```text
teamwork tests list [--layer LAYER]
```

List test records.

## Review and archive

### `review`

```text
teamwork review [AGENT] [HANDLE] [--queue] [--by BY]
    [--result {pass,fail}] [--evidence EVIDENCE] [--findings FINDINGS]
    [--force REASON]
```

Reviewer: independent second review of a deliverable. `--queue` lists everything
awaiting review. A pass archives the result; a fail returns the task to its
owner. `--force` overrides the review gates and requires a recorded reason.

### `selfcheck`

```text
teamwork selfcheck AGENT HANDLE [--by BY] [--result {pass,fail}]
    [--note NOTE] [--test TEST] [--force REASON]
```

Author's own review and test before submitting for review. A passing self-check
requires a `--test` line; `--note` records what was re-read.

### `archive`

```text
teamwork archive [--agent AGENT]
```

Show the reviewed-result archive (the team's evidence ledger).

## Decisions, disputes and governance

### `decision`

```text
teamwork decision {add,list} ...
```

#### `decision add`

```text
teamwork decision add --by BY [--kind KIND] [--title TITLE] --decision DECISION
    [--why WHY] [--evidence EVIDENCE] [--context CONTEXT] [--options OPTIONS]
    [--falsify FALSIFY] [--consequences CONSEQUENCES] [--task TASK] [--rev REV]
    [--status {proposed,accepted,superseded,rejected}] [--force REASON]
```

`--kind` is one of `technical,governance,redline,tribunal,scope,cost,process`.
A decision without evidence is refused.

#### `decision list`

```text
teamwork decision list [--kind KIND]
```

List recorded decisions.

### `dispute`

```text
teamwork dispute {open,round,escalate,sign,resolve,list} ...
```

Challenge a design or decision with counter-evidence.

#### `dispute open`

```text
teamwork dispute open --by BY --against AGAINST --topic TOPIC
    [--evidence EVIDENCE] [--position POSITION] [--task TASK]
```

#### `dispute round`

```text
teamwork dispute round ID --by BY --message MESSAGE
```

Add a rebuttal round (capped at three, then the tribunal).

#### `dispute escalate`

```text
teamwork dispute escalate ID --by BY
```

Send an unresolved dispute to CEO + CTO + CFO.

#### `dispute sign`

```text
teamwork dispute sign ID --by BY
```

A tribunal member signs the ruling.

#### `dispute resolve`

```text
teamwork dispute resolve ID --by BY --decision DECISION [--force REASON]
```

Record the binding ruling.

#### `dispute list`

```text
teamwork dispute list [--open]
```

### `redline`

```text
teamwork redline {record,close} ...
```

#### `redline record`

```text
teamwork redline record --by BY --action ACTION --why WHY
    [--alternative ALTERNATIVE] [--authorized AUTHORIZED]
```

Record a refused red-line action. Never crossed silently.

#### `redline close`

```text
teamwork redline close ID --by BY [--reason REASON] [--force REASON]
```

Close a resolved red line.

### `skill`

```text
teamwork skill {create,share,candidates,rm,list} ...
```

Team skills: extract repeated flows into `<project>/.agents/skills/<name>/SKILL.md`.

#### `skill create`

```text
teamwork skill create --name NAME [--role ROLE] --for DESCRIPTION --by BY
    [--body BODY] [--body-file BODY_FILE] [--force] [--allow-main]
```

#### `skill share`

```text
teamwork skill share NAME --by BY [--to TO]
```

Notify same-role peers so they reuse it. `--to` is a comma list of roles,
defaulting to the owner role.

#### `skill candidates`

```text
teamwork skill candidates [--min-tasks MIN_TASKS]
```

Find flows worth extracting.

#### `skill rm`

```text
teamwork skill rm NAME --by BY
```

#### `skill list`

```text
teamwork skill list
```

## Git workflow

### `branch`

```text
teamwork branch {start,list} ...
```

#### `branch start`

```text
teamwork branch start --agent AGENT --task TASK [--base BASE] [--worktree]
```

Create and switch to the task branch. `--worktree` uses a separate worktree
under `Runtime/Worktrees/`.

#### `branch list`

```text
teamwork branch list
```

Branches with PR and merge state.

### `pr`

```text
teamwork pr {open,list,merge} ...
```

#### `pr open`

```text
teamwork pr open --agent AGENT --task TASK [--title TITLE]
    [--summary SUMMARY] [--base BASE] [--push]
```

Submit a PR to the Reviewer. `--push` pushes the branch if a remote exists.

#### `pr list`

```text
teamwork pr list [--open]
```

The Reviewer's PR inbox.

#### `pr merge`

```text
teamwork pr merge --pr PR [--by BY] [--squash] [--keep-branch]
    [--delete-branch] [--force REASON]
```

Reviewer: merge an approved PR. The merged branch is deleted unless
`--keep-branch` is given. `--force` overrides the review gate and requires a
recorded reason.

### `commit`

```text
teamwork commit [--role ROLE]
    [--type {feat,fix,test,docs,design,research,refactor,perf,build,ci,chore,revert}]
    [--area AREA] [--task TASK] [--producers PRODUCERS] [--goal GOAL]
    [--deliverable DELIVERABLE] [--why WHY] [--status STATUS] [--result RESULT]
    [--docs DOCS] [--refs REFS] [--paths PATHS] [--all] [--allow-main]
    [--dry-run] [--no-check-lfs] [--lfs-threshold LFS_THRESHOLD]
```

Commit a change-set with the fixed style and the role commit identity.

| Option | Meaning |
|---|---|
| `--paths` | Comma-separated paths to stage. |
| `--all` | Stage every change. |
| `--allow-main` | Override the main-branch protection (rare; explain why). |
| `--no-check-lfs` | Skip the large-file LFS check (enforced by default). |

### `identity`

```text
teamwork identity [--role ROLE]
```

Show the role commit identity, e.g. `Developer <developer@agents.nidvue.com>`.

## Audit and control

### `ledger`

```text
teamwork ledger {show,verify,repair,export} ...
```

The append-only, hash-chained audit trail.

#### `ledger show`

```text
teamwork ledger show [--tail TAIL] [--action ACTION] [--actor ACTOR] [--target TARGET]
```

Inspect the trail.

#### `ledger verify`

```text
teamwork ledger verify [--reconcile]
```

Recompute the hash chain. `--reconcile` repairs a head cache left by a crash.

#### `ledger repair`

```text
teamwork ledger repair --by BY --reason REASON [--force REASON]
```

Drop a torn tail and record the repair.

#### `ledger export`

```text
teamwork ledger export [--dry-run] [--by BY]
```

Write an externally verifiable audit manifest (`docs/Team/AuditManifest.json`).

### `trace`

```text
teamwork trace HANDLE
```

Follow one task, criterion, test or PR through every record.

### `links`

```text
teamwork links [--no-reciprocity]
```

Check markdown cross-links, external URLs and back-links. `--no-reciprocity`
skips the bidirectional back-link requirement. Exit code `1` when issues exist.

### `audit`

```text
teamwork audit [--stale-days STALE_DAYS]
```

Find fabricated completions, stale work, duplicates, LFS problems and link
health.

### `loop`

```text
teamwork loop
```

Stop-condition check: may the team stop? Prints `STOP` or `CONTINUE` with
reasons.

### `version`

```text
teamwork version
```

Print the version and exit (same as `--version`).

### `selftest`

```text
teamwork selftest
```

Offline smoke test of the install; no network, no workspace required.

### `model` - per-agent configuration and automatic routing

```text
teamwork model set <role|instance> --provider P --model M
teamwork model get <role|instance>
teamwork model list
teamwork model auto [--apply] [--json]
```

The skill ships no model and calls no LLM API: every agent runs through the host's
own API, so the model is a property of the **agent**, not of the project.

- `set` writes a role default, or an instance override when the name carries an
  instance suffix (`developer-1`). The instance wins over the role.
- `get` prints the effective model and where it came from (`agent`, `role` or
  `unset`); `list` prints the whole roster.
- `auto` reads the **runtime environment** - the running agent host and the model
  it exposes - and routes the strongest available model to the decision lanes
  (Reviewer, Architect,
  Security Auditor, CEO, CTO) and the economy model to the mechanical lanes
  (developers, testers, writers, formatting, link checks). It is a dry run by
  default; `--apply` writes it and records `model.auto` in the ledger. It never
  invents a model id: a lane with nothing available is reported `unset` together
  with the variable to set (`TEAMWORK_MODEL_STRONG`, `TEAMWORK_MODEL_ECONOMY`).
  `TEAMWORK_AGENT_HOST` pins host detection when the markers are ambiguous.

Automatic routing policy: [references/Concurrency.md](https://github.com/Nidvue/Teamwork/blob/main/references/Concurrency.md).

### `imaging probe`

```text
teamwork imaging probe [--json]
```

The Designer's capability probe for **generated raster assets**. It is offline by
design: it reads environment variables and `PATH` only, never the network, so it
cannot leak a prompt or hang.

Resolution order: `TEAMWORK_IMAGE_MODEL` (explicit override) ->
`TEAMWORK_IMAGE_PROVIDER` -> the first ambient provider with a ranked image
model, in the order openai, google, black-forest-labs, stability, replicate,
local, ollama-cloud. "Best quality" is the first generally available model of the
detected provider, ranked in `teamwork.engine.IMAGE_MODEL_RANKING`.

When no model is detected it prints the fallback ladder instead of failing:
local model, then a hand-authored SVG. The full process - plan one prompt per
asset in `docs/Team/Design.md`, generate at least four candidates off one seed
base, review every candidate visually, improve the winner until it passes,
integrate, record evidence - plus the privacy and licence red lines, is the
Designer's own policy in
[`roles/designer.md`](https://github.com/Nidvue/Teamwork/blob/main/roles/designer.md).
