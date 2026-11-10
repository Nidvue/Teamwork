---
name: teamwork-pi
description: "pi native layer for the teamwork skill - how a pi session starts and supervises parallel team lanes with the engine's own runtime, schedules the pulse, and answers a lane's blocker. Use together with /skill:teamwork when running a team on pi."
---

# Teamwork on pi

Owner: CEO. Related: `../teamwork/SKILL.md` (the protocol) · `../teamwork/references/Adapters.md` · `../teamwork/references/Concurrency.md`

The core skill is host-agnostic and the engine is the runtime. Pi contributes one
thing: a headless CLI (`pi -p`) that turns a lane packet into an agent run. Nothing
here needs an extension - if `pi-subagents` is installed you may use it, but the
team must keep running when it is not.

## Six operations, all in the engine

| Operation | On pi |
|---|---|
| spawn a lane | `teamwork.py lane start --agent developer-1 --task T-0007` - the engine launches `pi -p` itself |
| fan many lanes out | `teamwork.py swarm run` - waves computed from the board and sized by the measured weight of the work (one detached `pi -p` child per lane) |
| send a fact to a lane | write `Agents/<Instance>/Inbox.md`; the next run reads it |
| inspect | `teamwork.py lane list|status|logs`, `teamwork.py board`, `teamwork.py pulse` |
| pulse | `teamwork.py swarm run` (loop) or `teamwork.py pulse --commit` (one wake) |
| close | `teamwork.py lane stop <run>` per live lane, `lane reap`, then the final report |

The launcher the engine uses on pi is
`pi -p --no-session [--provider P] [--model M] "<packet>"`; `lane start --resume`
switches that to `--session-id`, so a retry continues the lane's own session. Set
`LaneHost`/`TEAMWORK_AGENT_HOST=pi` when detection is ambiguous, or
`LaneCommand`/`TEAMWORK_LANE_CMD` to pin an exact command line.

## Packet shape that survives a bounded lane

The engine writes the packet; keep the same discipline when you write one by hand
with `--prompt-file`: at most two assignments, numbered steps with exact commands,
a tool-call budget (<= 16) and a hard minute budget, an explicit "stop and report
the blocker" clause, and an anchor-first reading rule (`rg -n` then read +/-30
lines). Lanes that were given open-ended verification timed out at 30 minutes with
zero commits; the same work finished in 8 calls when the packet named the commands.

Every lane ends with one line:

```text
LANE-RESULT: <ok|blocked|failed> <one sentence naming the revision or the blocker>
```

The supervisor records that verdict in `Runtime/Lanes/<run>.json` and quotes it in
the swarm summary; an `ok` lane that left no self-check or PR on the board is
retried, not believed.

## Scheduling the pulse

There is no host scheduler to depend on: `swarm run` is the loop, `pulse
--commit --spawn` is the one wake, and both size the wave from the work in hand -
one prose task is one lane, a board of code fans out, and it scales down as the
board drains. Run it from the session, and pin the width only when you mean to:

```sh
teamwork.py swarm run --minutes 60 --poll 5      # complexity-sized
teamwork.py swarm run --fixed --lanes 4          # exactly four lanes
```

A wave ends when one lane ends, so the CEO stays free between waves. If the session
must return to the user, leave the lanes running - they are detached children with
their own outcome files - and reconcile them on the next turn with `lane status`.

## Rules that cost us real time

- A lane inherits `TEAMWORK_ROOT`, `TEAMWORK_TEAM` and `TEAMWORK_LANE` from the
  spawn, so it acts on this team even from another cwd; a hand-started lane needs
  `TEAMWORK_ROOT=<repo>/.pi/Teamwork/Teams/<Team>` exported.
- Worktree isolation is refused on a dirty tree; lanes share the checkout and
  commit with `--paths` so no lane sweeps a peer's uncommitted work.
- A review verdict names the revision it measured; a lane that reviewed a stale
  head is re-dispatched with the head sha and told to assert it first.
- One task, one branch: `branch start` creates the branch from the default branch
  and switches the checkout, so start it before writing and never from a lane
  branch.
- `lane stop` signals the whole process group; `lane reap` is for a lane whose
  process is already gone. Never kill a peer's lane by pid.
