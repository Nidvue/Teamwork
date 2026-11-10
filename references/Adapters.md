# Adapters - running the team on any agent host

Owner: CEO.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Coordination](Coordination.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md) | [Remotes](Remotes.md)

The team is a **protocol**, not a product feature. Everything normative in this
skill - the workspace format, acceptance-criteria records, the two-stage gate,
the hash-chained ledger, the test-layer matrix, `AGENTS.md` - is host-independent
and lives in files the team owns. Only six operations need a host to provide a
mechanism, and this file maps each one to the concrete tool of a given host.

Never hard-code a host tool in a normative step. Name the operation, then use the
adapter. If a host cannot provide an operation, use its documented degraded mode -
the gates still hold, only the concurrency drops.

This file is the only **adoption surface** that names a concrete host. Every other surface
(`SKILL.md`, README, install guide, quickstart) describes one generic protocol and
points here, so a new host is a new column, never a rewrite of the instructions.

## The six operations

| # | Operation | What the team needs |
|---|---|---|
| 1 | **Spawn a teammate** | start a long-lived agent with a persona and its own context |
| 2 | **Delegate one-shot work** | run a bounded, isolated task and take its result |
| 3 | **Message an agent** | send a direct or broadcast instruction |
| 4 | **Inspect teammate state** | see who is idle, busy, stuck; read their last output |
| 5 | **Re-wake on a schedule** (pulse) | periodic trigger to feed idle lanes |
| 6 | **Close the team** | stop the teammates and release the lanes |

## Host mapping

| Operation | Pi | Claude Code | opencode | Codex / Cursor / Windsurf / Gemini CLI | Generic (no agent runtime) |
|---|---|---|---|---|---|
| 1 spawn | `subagent({agent, task})` - one call per lane, `async: true` keeps the CEO free while it runs; a *persistent* teammate needs a teams-style extension, the default host gives bounded runs | `Agent`/`Task` tool with a `.claude/agents/<name>.md` persona | `.opencode/agent/<name>.md` + the Task tool | run the CLI as a subprocess (`codex exec`, `cursor-agent`) | `bash` background process + a prompt file |
| 2 one-shot | `subagent({agent,task})` | `Task` tool, single agent | Task tool / a separate `opencode run` | `codex exec "<task>"` | one `bash` invocation, result to a file |
| 3 message | child to parent: `contact_supervisor` / `subagent_supervisor({action:"reply"})`; parent to child: `subagent({action:"steer"/"resume", id, message})` | `SendMessage` / prompt injection | agent-to-agent message | write to the agent's inbox file | append to `Agents/<Name>/Inbox.md` |
| 4 inspect | `subagent({action:"status", id})` and `subagent_supervisor({action:"list"/"pending"})` for the runs | agent status / task list | session list | process list + worklog | `teamwork.py board` + `pulse` + `WorkLog.md` |
| 5 pulse | `subagent({action:"schedule.create", options:{every:"5m"}})` | no built-in scheduler: `Bash` background loop, `/loop`, or host `cron` running `claude -p` | no scheduler: `cron`/systemd running `opencode run` | host `cron` / `watch` / CI schedule | `cron`, `systemd` timer, or a `while` loop running `teamwork.py pulse --commit` |
| 6 close | a bounded run ends with its own task; stop a live one with `subagent({action:"stop", id})` and list what still runs with `subagent_supervisor({action:"list"})` | stop the subagents / end the session | stop sessions | kill the processes | `pkill` the lanes, `teamwork.py clean --team-wide` |
| skill install | `~/.pi/agent/skills/<name>/SKILL.md` | `.claude/skills/<name>/SKILL.md` (Agent Skills format - this file already matches: `name` + `description` frontmatter) | `AGENTS.md` + `.opencode/command/<name>.md` | `AGENTS.md` (every one of these reads it) | `AGENTS.md` + this directory |

The Pi column was verified against the installed `pi-subagents` package on
2026-10-19 (pi 1.3.0): it exposes `subagent`, `subagents_enable`,
`subagent_supervisor`, `contact_supervisor` and `structured_output`, and **no
`teams(...)` tool**. A host that does provide a teams-style tool maps the same
four operations to
`teams({action:"delegate"/"message_dm"/"member_status"/"team_done"})`.

`AGENTS.md` at the project root is the universal contract: Claude Code, opencode,
Codex, Cursor, Windsurf, Gemini CLI, Aider and Pi all read it. Write the team
constitution there once (`teamwork.py agents-md`) and every host inherits it.

## Degraded modes (still complete, just slower)

- **No scheduler** (operation 5): run `teamwork.py pulse --commit` on a host `cron`
  entry, or have the CEO re-issue the pulse prompt at milestones, or simply have
  each lane self-serve with `teamwork.py task next <name>` between turns. The rule
  "never let an idle lane sit while runnable work exists" is unchanged; only the
  automation of the wake-up differs.
- **No teammate tool** (operation 1/2): the same role charters are executed
  sequentially by one agent that switches hats, claiming tasks from the same
  shared queues. The evidence gates, the Reviewer separation and the ledger are
  unaffected - which is the point: the protocol does not depend on parallelism.
- **No message tool** (operation 3): the mailbox is already a file
  (`Agents/<Name>/Inbox.md`); writing to it is a valid message on every host.
- **No `teams` tool**: spawn with the host's own CLI in a `bash` job and point it
  at `Agents/<Name>/StartHere.md` - the startup routine is identical.
- **Only bounded runs** (Pi's `subagent`, a CLI job): fan the lanes out as
  concurrent calls instead of persistent teammates - one Reviewer instance per
  call, each starting from its own `StartHere.md`. Bounded runs cannot see each
  other, so the **board is what keeps them apart**: the CEO fans deliverables out
  with `pulse --commit` and every lane takes work with
  `review ... --claim --by <lane>` / `task next`, which is exactly why a claim is
  a record and not a handshake. Two Reviewer lanes that skip the claim will
  review the same deliverable twice.

## Host detection also drives model routing

The same detection that picks the adapter picks the model: `teamwork.py model auto`
reads the host (pi, claude, opencode, codex, cursor, gemini) and the model that host
exposes, then routes the strongest available model to the decision lanes and the
economy model to the mechanical lanes; `TEAMWORK_AGENT_HOST` pins the detection when
the markers are ambiguous. Policy: [Concurrency](Concurrency.md).

## The skill copy is the thing that runs

Every host reads a *copy* of this skill from its skills directory, so the copy has
to follow the remote. One command owns that on every host:

```sh
teamwork refresh            # fetch origin/main, then mirror into the host's skills dir
teamwork refresh --check    # drift only, writes nothing, exit 1 when stale
teamwork refresh --dest ~/.agents/skills/teamwork   # another host's directory
teamwork refresh --mirror --repo <url>             # no checkout yet: create the mirror once
```

Measured failure this prevents: a host copy with an old `SKILL.md` and eight
engine modules missing - the engine imported `config`/`gitutil`/`records` fine
from the checkout and failed from the installed copy. A dirty checkout is
mirrored, never reset; files the source dropped are deleted; a host reload is
required after a write and the command says so.

## Rules

1. **The engine is the constant.** `teamwork.py` (stdlib only, Python 3.9-3.13) is
   the only thing a host must be able to run. It never calls a host API.
2. **State lives in git and in `.pi/`.** Nothing important lives in a host's
   private memory: a teammate that dies and is respawned on another host resumes
   from `StartHere.md`, the task queue and the ledger.
3. **One voice to the user** stays true on every host: only the CEO reports.
4. **A missing capability is not a red line.** Record the adapter used and the
   degradation in the task evidence; never fake a tool call that the host lacks.
5. **Adding a host** means adding a column here plus a smoke test that the six
   operations exist in some form - not changing the protocol.
