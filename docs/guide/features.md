# Features - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [Usage patterns](usage.md) · [Operations](operations.md) · [Alternatives](alternatives.md) · [Roadmap](roadmap.md) · [CLI reference](cli.md)

The full feature set behind the five-line pitch on the home page. Each row names
what the team actually does, not what it aspires to: if a claim here is not
exercised by a command or a gate, it does not belong on this page.

## 1. Why Teamwork

Three structural claims a competing orchestrator cannot copy cheaply. They are
the reason the protocol looks the way it does, and each one is measurable.

| # | Differentiator | What it means in practice |
|---|---|---|
| 1 | **Evidence or `UNVERIFIED`** | A task cannot reach `done` without a recorded `command @revision -> result`. Evidence is a packet - baseline, action, result, hashed artifact, replay - and a bug fix must prove the failure before the fix. `teamwork loop` refuses `STOP` while any criterion or required test layer is unverified. |
| 2 | **Role-shared memory** | Memory and the priority queue belong to the **role**, not the instance (`Roles/Developer/` is shared by `Developer-1..N`). Any role can run several instances, and **one instance at a time revises that role's memory** (`memory claim` / `memory release`), so peers never interleave edits; a lease that runs long is **contested by a peer and ruled by the CTO** (more time, or the lock removed). Agents reuse verified facts instead of re-asking, and the CEO pulse feeds every idle lane. |
| 3 | **Hash-chained audit trail** | Every mutation is appended to `Ledger.jsonl` with `by` / `src` / `rev` provenance. `ledger verify` detects tampering, `trace T-0007` follows a claim end to end, and `ledger export` writes a manifest anyone can check without trusting the team. |

## 2. Features

| Feature | What you get |
|---|---|
| Autonomous org | 16 role charters - the 15-role org (CEO, CTO, COO, CFO, Architect, Product Manager, Project Manager, Designer, Developer, Tester, Release Engineer, Technical Writer, Data Engineer, Reviewer, Security Auditor) plus a Team Leader per feature. The hierarchy is visible, not just enforced: `teamwork map` prints CEO -> CTO -> each leader with its `F-nnnn` and the squad under it, the unattached squad as the CTO's pool, and the independent lanes on their own line; `teamwork instance list` prints every instance's manager. A squad member escalates to its leader, the leader to the CTO. |
| Two-stage quality gate | The author self-checks with a real test, then a **different** role verifies the artifact against the requirement - what no independent lane verified at that revision - and cites the recorded results it does not repeat. Only the Reviewer may merge. |
| Review throughput | Risk-tiered review packets (`fast`/`standard`/`deep`) that list the records you may cite, `--credit` so a review does not re-run a gate another role already ran at the same revision, a delta re-review after a fail, a profile-aware claim lease (20/40/80 min, capped), `review --next` to claim and packet in one step, priority/age queue ordering, and capacity guidance so the Reviewer queue is not the bottleneck. |
| Parallel lanes | Freeze interfaces first, then developer, tester and designer lanes run concurrently against one frozen contract. |
| Own lane runtime | `teamwork swarm run` computes every wave from the board (ready tasks, unclaimed reviews, free provider slots, unfinished assignments), **sizes the wave from the measured weight of the work** (1 prose, 2 code, 3 deep, +1 bug -> `ceil(weight / 3)` lanes, re-measured every wave, bounded by `LaneMax`), starts one detached agent process per lane with a packet and a per-profile hard budget, and reconciles each lane from `Runtime/Lanes/<run>.json` plus its outcome file. A claim with no live lane is adopted, an assignment that leaves no self-check, PR or status change is retried within `LaneAttempts`, and `pulse --commit --spawn` runs the whole thing in one wake. `lane start|status|logs|wait|stop|reap` is the inspection surface; a host CLI is the only thing the engine needs from a host. |
| Layered tests | Each role designs, builds and runs its own test layer (`unit`, `integration`, `acceptance`, `ui`, `security`, ...); `tests plan` shows coverage and gaps. |
| Designed images | The Designer owns every visual asset, raster **and** vector, and decides what the deliverable needs: vector first (SVG, diagram-as-code), and for a raster `imaging probe` picks the best available text-to-image model (cloud first, else local, else SVG), then plan -> 4+ candidates -> visual review -> improve until it passes -> integrate, with privacy and licence rules. |
| Stop condition as a record | Acceptance criteria are machine records, not checkboxes. The loop stops only when they are all verified. |
| Role-shared state | One memory and one priority queue per role, shared by any number of its instances, with one revising instance at a time (`memory claim`); a private, disposable workspace per instance. |
| Learning loop | Every role keeps its own `Lessons.md` for mistakes it will not repeat, and the team keeps one `Knowledge.md`; a repeated failure can become a `tw-` mistake skill, and `load` surfaces open lessons and the top-ranked project knowledge. |
| Concurrency control | Provider slot leases respect per-provider caps, so N agents never overload a model endpoint. |
| Disputes and tribunal | A challenged design goes through evidence rounds; a 3-round deadlock is ruled on by the CEO + CTO + CFO and recorded. |
| Portable, dependency-free | CPython 3.11-3.13 on Linux, macOS and Windows. **Zero third-party runtime dependencies.** |
| Enforced standards | One canonical toolchain per language, run by the team: `ruff format` + `ruff check` gate CI, `mypy` runs as a non-blocking report (the engine is a tracked post-1.0 typing refactor); the full per-language table is in `references/Engineering.md`. |
| Automatic model routing | `teamwork model auto` detects the running agent host where the environment identifies it and routes the strongest available model to the decision lanes and the economy model to the mechanical lanes - best output where it compounds, lowest cost where it does not. Every lane's model is configurable independently (`model set <agent>`). |
| Clean, modular history | Work commits are rebased and squashed before review, each task then lands as one commit merged locally by the Reviewer (a merge commit on `main`, source branch deleted), and the naming policy (PascalCase directories, ecosystem-correct files) is written down rather than argued about. |
| Skill first, engine optional | The product is a skill: `SKILL.md`, role charters, references, templates and the stdlib-only engine in one directory. Any agent host that loads skills or reads `AGENTS.md` runs the same protocol (optional adapter mapping: `references/Adapters.md`); the Python package is only a convenience for driving the engine from a terminal. |
| Remote-agnostic integrity | Branch protection, required checks and protected `v*` tags are enforced on GitHub, GitLab, Bitbucket, Gitea/Forgejo or Azure DevOps alike; the one-commit-per-task merge is always done locally by the Reviewer, never with a host button. |

## 3. What the evidence gate really refuses

The first row above is the one readers test first, so it is worth being precise.
A record is accepted only when it names a command, a revision and an observed
result. `selfcheck` will not submit a task without one, `review` will not pass a
deliverable whose evidence is stale, and `loop` will not print `STOP` while an
acceptance criterion or a required test layer is unverified. A failed run is
useful evidence too: a `--bug` fix is refused until `tests repro` has recorded the
failing run before the passing one.

That is why the team can run unattended. The gate does not ask an agent whether
it is finished; it reads the records.

## 4. Where each feature lives

| You want | Read |
|---|---|
| the recurring jobs, as transcripts | [Usage patterns](usage.md) |
| provider slots, the memory pen, resuming after a crash | [Operations](operations.md) |
| the loop, the review gate and the workspace tree | [How it works](how-it-works.md) |
| package layout and resource resolution | [Architecture](architecture.md) |
| every command and flag | [CLI reference](cli.md) |
| how this compares with other orchestrators | [Alternatives](alternatives.md) |
