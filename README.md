<div align="center">
  <img src="assets/banner.svg" alt="Teamwork banner: three connected nodes and the pitch 'One prompt in. A whole company of agents out.'" width="1280" height="360" style="max-width:100%;height:auto">
  <img src="docs/assets/nidvue-icon.svg" alt="Nidvue" width="88" height="88">
  <h1>Nidvue Teamwork</h1>
  <p><strong>One prompt in. A whole company of agents out.</strong></p>
  <p>An autonomous, self-organising multi-agent company for coding agents:<br>
  evidence-gated, role-shared, and auditable by design.</p>
  <p>
    <a href="https://github.com/Nidvue/Teamwork/actions/workflows/ci.yml"><img alt="CI status" src="https://img.shields.io/github/actions/workflow/status/Nidvue/Teamwork/ci.yml?branch=main&amp;label=CI&amp;logo=github" height="20"></a>
    <a href="LICENSE"><img alt="License: AGPL-3.0-or-later" src="https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg" width="160" height="20"></a>
    <a href="docs/guide/architecture.md"><img alt="Python 3.11 to 3.13" src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue" width="176" height="20"></a>
    <a href="docs/guide/install.md"><img alt="Skill: one clone to install" src="https://img.shields.io/badge/skill-install%20in%20one%20clone-8957e5" width="144" height="20"></a>
    <a href="CONTRIBUTING.md"><img alt="PRs welcome" src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" width="90" height="20"></a>
    <a href="https://github.com/Nidvue/Teamwork/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/Nidvue/Teamwork?style=social" height="20"></a>
  </p>
</div>

<p align="center">
  <img src="assets/demo.svg" alt="Animated terminal: one git clone installs the skill, one request that names the skill starts the company, and the loop gate reports CONTINUE until every acceptance criterion is verified." width="820" height="478" style="max-width:100%;height:auto">
</p>

Nidvue Teamwork is **a skill for your coding agent** - not a standalone
application. Install it like any other skill (one clone, no package manager), then
ask your agent for the team:

```text
> use the teamwork skill: Build a URL shortener with a CLI, tests and docs
```

That prompt becomes a team of AI agents that plans, builds, tests and
**independently reviews its own work until every acceptance criterion has
executed evidence**. The agent host supplies the LLM API, and **every agent's model
is configured independently** (`teamwork model set <agent>`): a strong model for
the Reviewer, a cheap one for the mechanical lanes. The engine (`teamwork.py`, stdlib only) ships inside the skill; installing it as a package is optional.

- **Developed by AI agents, for AI agents.** This repository is built by its own
  team: reviewed tasks in [Archive](docs/Team/Archive.md), the learning loop in
  [Evolution](docs/Team/Evolution.md), and all but two commits (a merge and a
  dependabot bump) by a role mailbox.
- **One prompt in, a whole company out.** [The 30-second quickstart](#30-second-quickstart)
  is the whole install.
- **It improves from its own failures.** A failure becomes a lesson, a lesson
  becomes a skill, and a skill reaches the core only after two cuts; its own
  verdict is `confounded`, because the first adoption changed the metrics and the
  classifier together ([Evolution](docs/Team/Evolution.md) 9.2).
## What makes it different

| Differentiator | What it is | Proof |
|---|---|---|
| **Skill-first** | One clone into the directory your agent scans; no package manager. | [Installation](docs/guide/install.md) |
| **One parent, one board** | One manager and one queue per role; any role scales. | [How it works](docs/guide/how-it-works.md) |
| **Evidence or `UNVERIFIED`** | `done` needs a recorded `command @revision -> result`. | [Operations](docs/guide/operations.md) |
| **Reviewer-only merge** | The author self-checks, a different role reviews, a pass lands. | [How it works](docs/guide/how-it-works.md) |
| **Layered tests** | Each role designs, builds and runs its own layer. | [Features](docs/guide/features.md) |
| **Tamper-evident ledger** | Every mutation is hash-chained and exportable. | [Operations](docs/guide/operations.md) |

Five more ship inside the skill - engine commands, no plugin, no daemon:

| Capability | What you get | Command |
|---|---|---|
| Memory that persists | Captured at each lane exit, promoted to long-term, shared per role, verified against cited revisions. | `teamwork memory` |
| Live agent state | Every instance's state, task, time and progress, plus recent lanes; a stable `--json` feed the bundled widget renders. | `teamwork status` |
| Real parallel lanes | `swarm run` sizes the wave from the work and detaches one budgeted process per lane. | `teamwork swarm run` |
| Agents that talk | A prioritised mailbox in the next packet; `urgent` preempts it and pauses its task. | `teamwork message send` |
| Token economy | A measured startup read against a 120 KiB cap, a memory index and read-by-id commands. | `teamwork harness budget` |

### Built by itself

The team is the skill's first user: it decomposes, dispatches to sub-agents that
fan out further, reviews every deliverable and merges it - this repository is that
output. The learning loop is recursive too: a failure becomes a lesson, a lesson a
skill, a skill reaches the core after two cuts
([Evolution](docs/Team/Evolution.md) 9.2).

The sourced comparison is in [Alternatives](docs/guide/alternatives.md).

## Install the skill

Clone the skill into the directory your agent host scans - no daemon, no hosted
service, nothing to build:

```bash
# project-local: plain files in your repository, not a nested git repo
mkdir -p .agents/skills
git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork
rm -rf .agents/skills/teamwork/.git
```

Prefer a user-level install (`~/.agents/skills/teamwork`), a package manager
(`npm install @nidvue/teamwork`) or the optional engine wheel? [Installation](docs/guide/install.md)
compares all four channels, their commands and their requirements. Dropping the
nested `.git` is deliberate: the skill must be committed as plain files, not a
gitlink.

## 30-second quickstart

```bash
# 1. create the project and install the skill into it (one clone, nothing to
#    build; drop the nested .git so the skill is committed as plain files, not a
#    submodule)
$ mkdir my-project && cd my-project
$ mkdir -p .agents/skills && git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork && rm -rf .agents/skills/teamwork/.git

# 2. ask your agent for the team, from the project root
> use the teamwork skill: Build a URL shortener with a CLI, tests and docs
```

The CEO writes `AGENTS.md`, staffs the roster, freezes the interfaces, records
the acceptance criteria and opens the lanes. The hidden, gitignored workspace
appears at `.pi/Teamwork/Teams/<Team>/`; project output is committed. Read the full walkthrough in [Quickstart](docs/guide/quickstart.md).

## What you get

- **16 role charters** - the 15-role org plus a Team Leader per feature, each
  with its own memory and queue.
- **A two-stage quality gate** - author self-check, then independent review; only
  the Reviewer merges.
- **Parallel lanes, no plugin** - `swarm run` sizes each wave from the work.
- **Built-in memory and a mailbox** - role-shared memory, a `ctx://` tree and a
  prioritised agent-to-agent queue.
- **Live state** - `status` and its JSON feed, plus the bundled status widget.
- **Layered tests** - one owner per layer, gaps shown by `tests plan`.
- **Token-true budget** - `harness budget` measures the startup read; trim it,
  never raise the cap.
- **Automatic model routing** - `teamwork model auto` puts the strong model on
the decision lanes and the economy one on the mechanical lanes.
- **Portable** - CPython 3.11-3.13 on Linux, macOS and Windows; stdlib only.

## Documentation

| Page | Read it for |
|---|---|
| [Documentation home](docs/index.md) | The docs site index. |
| [Installation](docs/guide/install.md) | Install channels, requirements, uninstall. |
| [Quickstart](docs/guide/quickstart.md) | Bootstrap a team and run the CEO loop. |
| [For agents](docs/guide/for-agents.md) | The install-and-drive routine. |
| [Usage patterns](docs/guide/usage.md) | The recurring jobs, as transcripts. |
| [Operations](docs/guide/operations.md) | Slots, memory, live state, the mailbox, the ledger. |
| [How it works](docs/guide/how-it-works.md) | The loop, the gate, the workspace tree. |
| [Features](docs/guide/features.md) | Every capability, and what the gate refuses. |
| [Architecture](docs/guide/architecture.md) | Package layout, resource resolution, workspace format. |
| [CLI reference](docs/guide/cli.md) | Every command and flag, in [records](docs/guide/cli-records.md), [review](docs/guide/cli-review.md), [workflow](docs/guide/cli-workflow.md) and [audit](docs/guide/cli-audit.md). |
| [Alternatives](docs/guide/alternatives.md) | How this compares with others. |
| [Roadmap](docs/guide/roadmap.md) | What is shipped, current, and not planned. |
| [Releases](docs/releases.md) | What a release publishes. |
| [CI pipeline](docs/guide/ci.md) | Run the pipeline locally. |

## Contributing, security and license

- **Contributing** - work on your own branch, run `pytest -q` and `ruff check`,
  open a PR; a Reviewer - never the author - merges it. Read
  [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md).
- **Security** - report privately via
  [GitHub security advisories](https://github.com/Nidvue/Teamwork/security/advisories/new);
  see [SECURITY.md](SECURITY.md).
- **License** - [AGPL-3.0-or-later](LICENSE), copyright (C) 2026 **Nidvue**
  ([NOTICE](NOTICE)). The strong copyleft is deliberate: the audit guarantees
  should survive modification.
- **No personal data, no local leakage** - `scripts/privacy_scan.py` fails the
  build on names, emails, home paths, credentials or agent-host state.

<p align="center">
  <a href="https://star-history.com/#Nidvue/Teamwork&amp;Date"><img src="https://api.star-history.com/svg?repos=Nidvue/Teamwork&amp;type=Date" alt="Star history chart for Teamwork" width="720"></a>
</p>
