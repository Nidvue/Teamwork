# Nidvue Teamwork

Owner: Technical Writer.

Related: [Installation](guide/install.md) · [Quickstart](guide/quickstart.md) · [CLI reference](guide/cli.md) · [Architecture](guide/architecture.md) · [CI pipeline](guide/ci.md) · [Releases](releases.md)

Nidvue Teamwork turns one prompt into a self-organising team of AI agents that plans,
builds, tests and reviews a project until every acceptance criterion is verified.
It is a **skill for your coding agent** - not a standalone app and not a hosted
service. The stdlib-only engine and the workspace format ship inside the skill;
installing the engine as a Python package is optional.

- **Automatic model routing** - `teamwork model auto` detects the agent
  host and routes the strongest available model to the decision lanes and
  the economy one to the mechanical lanes: best output where it compounds,
  lowest cost where it does not.

## What it is

| Face | What it means |
|---|---|
| **Skill** (the product) | `SKILL.md`, `roles/`, `references/`, `templates/` and the engine in one directory, cloned into the skills directory an agent host scans (project `.agents/skills/teamwork/` or user `~/.agents/skills/teamwork/`). Hosts without a skill loader use the same protocol through `AGENTS.md`. Invoked by naming the skill in the request. |
| **Engine** (optional CLI) | `src/teamwork/`, exposing the `teamwork` console script and `python -m teamwork`. No third-party runtime dependencies. The skill runs the same engine from its own directory. It ships through three package channels - npm (`@nidvue/teamwork`), the GitHub-release wheel, and source - and the `teamwork-agents` distribution name exists but is **not yet on PyPI**, so index commands do not resolve. [Releases](releases.md) says what each channel carries. |
| **Workspace format** | Markdown and JSON under `<project>/.pi/Teamwork/Teams/<Team>/`, hidden and local; project output is committed. |

One engine backs all three; the skill is how people install and use it.

## Why

- **Run to completion.** Work ends only when every acceptance criterion has
  executed evidence, not when an agent says it is done.
- **Evidence over claims.** A task cannot reach `done` without a recorded
  command, revision and observed result.
- **Independent review.** A different role reviews every deliverable before it is
  merged; only the Reviewer may merge.
- **Parallel lanes.** Interfaces are frozen first, then developer, tester and
  designer work concurrently against the same contract.
- **Auditable by design.** Every mutation is appended to a hash-chained ledger
  (`Ledger.jsonl`) you can verify without trusting the team.

## 30-second quickstart

```console
$ mkdir -p .agents/skills && git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork && rm -rf .agents/skills/teamwork/.git
$ cd my-project
> use the teamwork skill: build a URL shortener with a CLI, tests and docs
```

One clone installs the skill; the prompt starts the company. The CEO writes
`AGENTS.md`, staffs the roster and opens the lanes, and `init` creates the
workspace under `.pi/Teamwork/Teams/<Team>/` without touching your tree. When you
want to see or steer the engine yourself:

```console
$ teamwork map
$ teamwork criteria add --id AC-1 --text "CLI prints the version and exits 0" --owner developer --by ceo
$ teamwork loop
```

`criteria add` records what "done" means; `loop` is the mechanical stop check and
reports `CONTINUE` until every criterion and test layer passes. Full walkthrough:
[Quickstart](guide/quickstart.md).

## Features

- 15 role charters (CEO, CTO, COO, CFO, Architect, Product Manager, Project
  Manager, Designer, Developer, Tester, Release Engineer, Technical Writer, Data
  Engineer, Reviewer, Security Auditor).
- Role-shared memory and task queues; private per-instance workspaces.
- Two-stage quality gate: author self-check, then independent Reviewer verdict.
- Layered tests, one owner per layer, tracked in `tests plan`.
- Hash-chained ledger with `ledger verify`, `ledger export` and `trace`.
- Coordination health with `coordination --strict`: duplicate work, echoed
  review evidence, reviewer monoculture, merge collapse and slot starvation.
- Risk-tiered review packets, a profile-aware review lease (20/40/80 min, capped)
  and `review --next` keep the Reviewer queue moving without lowering the
  evidence bar.
- Provider slot leases for concurrency caps.
- Portable runtime: CPython 3.9-3.13 on Linux, macOS and Windows.

## Documentation

| Page | Read it for |
|---|---|
| [Installation](guide/install.md) | Install the skill into the directory your agent host scans; optional engine package. |
| [Quickstart](guide/quickstart.md) | Bootstrap a team in an empty project and run the CEO loop. |
| [CLI reference](guide/cli.md) | Every command, subcommand, flag and exit code. |
| [Architecture](guide/architecture.md) | Package layout, resource resolution, workspace and ledger. |
| [CI pipeline](guide/ci.md) | Run the full lint/test/build/docs pipeline locally. |
| [Releases](releases.md) | What a release publishes (GitHub Release, npm package, site), how to read the current version, and what it does not publish. |

## Repository

- Source and releases: [github.com/Nidvue/Teamwork](https://github.com/Nidvue/Teamwork)
- npm package: [@nidvue/teamwork](https://www.npmjs.com/package/@nidvue/teamwork) - accessed 2026-10-28
- README and demo: [README.md](https://github.com/Nidvue/Teamwork/blob/main/README.md)
- Contributions: [CONTRIBUTING.md](https://github.com/Nidvue/Teamwork/blob/main/CONTRIBUTING.md)
- Security policy: [SECURITY.md](https://github.com/Nidvue/Teamwork/blob/main/SECURITY.md)
- Changelog: [CHANGELOG.md](https://github.com/Nidvue/Teamwork/blob/main/CHANGELOG.md)
- License: [AGPL-3.0](https://github.com/Nidvue/Teamwork/blob/main/LICENSE)
