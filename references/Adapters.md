# Adapters - running the team on any agent host

Owner: CEO.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Coordination](Coordination.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md) | [Remotes](Remotes.md)

The team is a **protocol**, not a product feature. Everything normative in this
skill - the workspace format, acceptance-criteria records, the two-stage gate,
the hash-chained ledger, the test-layer matrix, `AGENTS.md` - is host-independent
and lives in files the team owns. Only six operations need a mechanism, and the
engine now provides all six itself:

| # | Operation | Engine mechanism |
|---|---|---|
| 1 | **Spawn a teammate** | `teamwork.py lane start --agent <instance>` - one detached child process, its packet and its record |
| 2 | **Delegate one-shot work** | the same `lane start --task <T-id>` / `--prompt-file <packet>` |
| 3 | **Message an agent** | `Agents/<Name>/Inbox.md` (always was a file), read at the start of every run |
| 4 | **Inspect teammate state** | `teamwork.py lane list|status|logs`, `pulse`, `board`, `WorkLog.md` |
| 5 | **Re-wake on a schedule** | `pulse --commit --spawn` (one async wake: dispatch and return) or `swarm run` (one async wave; `--wait` drains) |
| 6 | **Close the team** | `teamwork.py lane stop <run>` per live lane, then the final report |

A host is now only a **launcher**: a CLI that accepts a prompt and exits. That one
fact is the whole adapter surface - the engine detects the host, or takes a
template. Nothing in a normative step depends on a plugin, an extension, or a
host-private teammate tool.

## Host mapping for operation 1

| Host | Default launcher | Notes |
|---|---|---|
| Pi | `pi -p --no-session [--provider P] [--model M] "<packet>"` | `--session-id` instead of `--no-session` with `lane start --resume` |
| Claude Code | `claude -p [--model M] "<packet>"` | |
| opencode | `opencode run [--model M] "<packet>"` | |
| Codex | `codex exec [--model M] "<packet>"` | |
| Gemini CLI | `gemini -p [--model M] "<packet>"` | |
| Cursor | `cursor-agent -p "<packet>"` | |
| Generic (no agent runtime) | `TEAMWORK_LANE_CMD` / `LaneCommand` | a template split **without a shell**; the fallback every host has |

The template takes whole-argument placeholders - `{prompt}` `{packet}` `{log}`
`{agent}` `{model}` `{provider}` `{cwd}` `{run}` - for example
`"my-agent --task {packet} {model}"`. With no placeholder the prompt is appended
as the last argument. `LaneHost` pins the detected host; `TEAMWORK_AGENT_HOST`
does the same from the environment.

A host that also offers its own teammate, scheduler or messaging tool does not
change this protocol: such a tool is not part of it, and no surface may require
one. The engine's lane runtime is the mechanism - `lane start` and `swarm run`
detach the host CLI - so a session with no plugin installed runs the whole team,
and a host tool that appears or disappears changes nothing. A lane always takes
its work with `task next` or `review --claim`, so the board - not a host tool -
decides who owns what.

## How a lane runs

1. **The board decides who works.** `swarm run` computes a wave from the records:
   ready tasks by priority, unclaimed reviews, free provider slots, unfinished
   assignments. A wave is a fact about the board at that moment, never a plan
   written in advance.
2. **One lane, one assignment.** A lane is one child process with its own context;
   a wave hands each idle instance one unit and fans the rest out to other idle
   instances. `LANE_WIP` still lets a lane the CEO dispatches hold two units in its
   own run - that is a different shape from a supervised wave.
3. **The wave is sized by the work.** Ready tasks and unclaimed reviews are
   weighted 1 (prose), 2 (code) and 3 (security/release/data, +1 for a bug); the
   wave runs `ceil(weight / 3)` lanes, re-measured every wave and bounded by the
   free provider slots and `LaneMax`. One prose task is one lane; a board of code
   fans out. A unit's own budget follows its profile (10/10, 16/25, 24/40 tool
   calls/minutes), so a lane is never given a deep unit's time for a prose edit.
4. **The packet is the prompt.** `Agents/<Instance>/Runs/<run>.md` names the
   assignment, the charter, the exact commands, the budget and the result contract
   (`LANE-RESULT: <ok|blocked|failed> ...`). The packet is written before the
   process starts, so it is auditable even when the lane dies.
5. **The record is the state.** `Runtime/Lanes/<run>.json` carries the pid, the
   provider lease, the budget deadline, and the outcome; `Runtime/Lanes/<run>.outcome.json`
   is written by the wrapper (`teamwork.lanerun`) with the exit status. A missing
   outcome with a dead pid reads as `lost`, never as success.
6. **The supervisor does not need to survive.** A lane keeps running when the CLI
   exits, and a later `lane reap` / `swarm run` reconciles it from the records.
7. **An unfinished assignment is retried, then left to the CEO.** `LaneAttempts`
   (default 2) bounds the retries; progress is read from the task record
   (self-check, PR, status), never from an exit code. Past the budget the claim
   stays on the board and the CEO decides.
8. **A claim with no live lane is adopted.** `pulse --commit` (or a lane that
   died) can leave a claim owned by an instance with no process behind it; the
   supervisor launches it for that instance instead of planning around it, but only
   while the attempt budget allows. That is what makes `pulse --commit --spawn`
   one safe command.
9. **A review becomes a lane.** When a deliverable reaches `review`, the next wave
   claims it for a Reviewer instance and starts that lane - the dynamic hand-off
   the protocol depends on.

## Settings and environment

| Key | Default | Meaning |
|---|---|---|
| `LaneMinutes` / `TEAMWORK_LANE_MINUTES` | 25 | wall-clock budget per lane; the wrapper kills it and records `timeout` |
| `LaneAttempts` | 2 | attempts per assignment before the CEO is asked |
| `LaneToolBudget` | - | overrides the per-profile tool budget (10 fast / 16 standard / 24 deep) for every unit when set |
| `LanePollSeconds` / `TEAMWORK_LANE_POLL` | 2 | supervisor poll interval |
| `LaneMax` | 8 | ceiling on lanes per wave, whatever the measured complexity |
| `LaneHost` / `TEAMWORK_LANE_HOST` | detected | which host's CLI to launch |
| `LaneCommand` / `TEAMWORK_LANE_CMD` | - | launcher template, overrides the host |
| `SwarmMinutes` | 60 | swarm budget; `swarm run --minutes 0` means none |

Every lane child gets `TEAMWORK_ROOT`, `TEAMWORK_TEAM`, `TEAMWORK_LANE` and
`TEAMWORK_LANE_AGENT`, so an instance started from any cwd acts on this team.

## Degraded modes (still complete, just slower)

- **No launcher for the host** (operation 1/2): the same role charters are
  executed sequentially by one agent that switches hats, claiming tasks from the
  same shared queues. The evidence gates, the Reviewer separation and the ledger
  are unaffected - which is the point: the protocol does not depend on parallelism.
- **No scheduler** (operation 5): `pulse --commit` once per wake by hand, or let
  every lane self-serve with `task next` between turns. The rule "never let an
  idle lane sit while runnable work exists" is unchanged; only the automation of
  the wake-up differs.
- **No message tool** (operation 3): the mailbox is a file
  (`Agents/<Name>/Inbox.md`); writing to it is a valid message on every host.
- **A bounded host run** (`pi -p`, a CLI job): fan the lanes out as concurrent
  processes instead of persistent teammates - one Reviewer instance per lane, each
  starting from its own packet. Bounded runs cannot see each other, so the **board
  is what keeps them apart**: the CEO fans deliverables out with `pulse --commit`
  or `swarm run`, and every lane takes work with `task next` /
  `review ... --claim --by <lane>`, which is exactly why a claim is a record and
  not a handshake. Two Reviewer lanes that skip the claim will review the same
  deliverable twice.
- **No `teams` tool**: nothing is lost - a team-style tool maps onto the four
  operations the engine already implements (`lane start`, `Inbox.md`, `lane
  status`, `lane stop`).

## Host detection also drives model routing

The same detection that picks the launcher picks the model: `model auto` reads
the host (pi, claude, opencode, codex, cursor, gemini) and the model
that host exposes, then routes the strongest available model to the decision lanes
and the economy model to the mechanical lanes; `TEAMWORK_AGENT_HOST` pins the
detection when the markers are ambiguous. Policy: [Concurrency](Concurrency.md).

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

1. **The engine is the constant.** `teamwork.py` (stdlib only, Python 3.11-3.13) is
   the only thing a host must be able to run. It never calls a host API; it starts
   a host CLI as a child process.
2. **State lives in git and in `.pi/`.** Nothing important lives in a host's
   private memory: a lane that dies and is respawned resumes from its packet, the
   task queue and the ledger.
3. **One voice to the user** stays true on every host: only the CEO reports.
4. **Never hard-code a host tool in a normative step**, and never fake one the
   host lacks. A missing capability is not a red line: record the adapter used and
   the degradation in the task evidence.
5. **Adding a host** means adding a launcher row (or a `LaneCommand` template)
   plus a smoke test that a lane started and reconciled - not changing the
   protocol.
