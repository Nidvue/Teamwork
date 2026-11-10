# Nidvue Teamwork

Owner: Technical Writer.

Related: [Installation](guide/install.md) · [Quickstart](guide/quickstart.md) · [CLI reference](guide/cli.md) · [Architecture](guide/architecture.md) · [CI pipeline](guide/ci.md)

Nidvue Teamwork turns one prompt into a self-organising team of AI agents that plans,
builds, tests and reviews a project until every acceptance criterion is verified.
It ships as a Pi skill, an installable Python package, and a workspace format.

- **Automatic model routing** - `teamwork model auto` detects the agent
  host and routes the strongest available model to the decision lanes and
  the economy one to the mechanical lanes: best output where it compounds,
  lowest cost where it does not.

## What it is

| Face | What it means |
|---|---|
| **Pi skill** | `SKILL.md`, `roles/`, `references/` and `templates/` at the repository root; loadable as `~/.pi/agent/skills/teamwork`. |
| **Python package** | `src/teamwork/`, installed as `teamwork-agents`, exposing the `teamwork` console script and `python -m teamwork`. No third-party runtime dependencies. |
| **Workspace format** | Markdown and JSON under `<project>/.pi/Teamwork/Teams/<Team>/`, hidden and local; project output is committed. |

One engine backs all three, with the original skill behaviour unchanged.

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

## 60-second quickstart

Requires Python 3.9 or newer; nothing else at runtime.

```console
$ mkdir demo && cd demo
$ teamwork init --agents ceo,architect,product-manager,project-manager,reviewer-1,developer-1,tester-1
$ teamwork map
$ teamwork criteria add --id AC-1 --text "CLI prints the version and exits 0" --owner developer --by ceo
$ teamwork loop
```

`init` creates the workspace and writes `AGENTS.md`. `map` prints the layout.
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
- Provider slot leases for concurrency caps.
- Portable runtime: CPython 3.9-3.13 on Linux, macOS and Windows.

## Documentation

| Page | Read it for |
|---|---|
| [Installation](guide/install.md) | pip, pipx, uvx, from source; verifying the install. |
| [Quickstart](guide/quickstart.md) | Bootstrap a team in an empty project and run the CEO loop. |
| [CLI reference](guide/cli.md) | Every command, subcommand, flag and exit code. |
| [Architecture](guide/architecture.md) | Package layout, resource resolution, workspace and ledger. |
| [CI pipeline](guide/ci.md) | Run the full lint/test/build/docs pipeline locally. |

## Repository

- Source and releases: [github.com/VisionPZ/Teamwork](https://github.com/VisionPZ/Teamwork)
- README and demo: [README.md](https://github.com/VisionPZ/Teamwork/blob/main/README.md)
- Contributions: [CONTRIBUTING.md](https://github.com/VisionPZ/Teamwork/blob/main/CONTRIBUTING.md)
- Security policy: [SECURITY.md](https://github.com/VisionPZ/Teamwork/blob/main/SECURITY.md)
- Changelog: [CHANGELOG.md](https://github.com/VisionPZ/Teamwork/blob/main/CHANGELOG.md)
- License: [AGPL-3.0](https://github.com/VisionPZ/Teamwork/blob/main/LICENSE)
