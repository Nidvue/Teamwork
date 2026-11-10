---
name: teamwork-pi
description: "pi native layer for the teamwork skill - how a pi agent spawns and steers team lanes with subagent, schedules the pulse, and replies to lane decisions. Use together with /skill:teamwork when running a team on pi."
---

# Teamwork on pi

Owner: CEO. Related: `../teamwork/SKILL.md` (the protocol) · `../teamwork/references/Adapters.md` · `../teamwork/references/Concurrency.md`

The core skill is host-agnostic. This one maps its six host operations onto the
tools a pi session actually has. Read it once per session, then work from the core
skill.

## Six operations

| Operation | On pi |
|---|---|
| spawn a lane | `subagent({ agent, task, async: true, cwd })` |
| fan many lanes out | `subagent({ workflow: "./packet.js", async: true })` with `runs.all([...])` inside |
| send a fact to a lane | `subagent({ action: "steer", id, message })` while it runs; `subagent_supervisor({action:"reply"})` for a child that asked |
| inspect | `subagent({ action: "status", id })`, `subagent_supervisor({action:"list"})` |
| pulse | `subagent({ action: "schedule.create", id: "teamwork-pulse", workflow: "./.pi/workflows/teamwork-pulse.js", options: { every: "5m" } })` |
| close | `subagent({ action: "stop", id })` per live lane, then the final report |

There is no `teams()` tool on pi. A lane is a bounded run: it reads its role
charter and the shared queue, takes work with `task next`, commits, self-checks,
opens a PR and returns. The queue - not the tool - is what makes the team.

## Agent names

`software-architect` (architect), `product-manager`, `project-manager` is not a
subagent, so the plan lane runs through `delegate` with the instance name stated
in the packet; `developer`, `tester`, `reviewer`, `security-auditor`,
`release-engineer` runs through `delegate`, `designer`, plus builtins `delegate`,
`worker`, `oracle`, `scout`, `researcher`.

State the instance name in the packet (`developer-1`, `reviewer-2`) and require it
in every `--by` flag, because provenance is recorded per instance.

## Packet shape that survives a bounded lane

At most two features, numbered steps with exact commands, a tool-call budget
(<= 16) and a hard minute budget, an explicit "stop and report the blocker"
clause, and an anchor-first reading rule (`grep -n` then read +/-30 lines). Lanes
that were given open-ended verification timed out at 30 minutes with zero commits;
the same work finished in 8 calls when the packet named the commands.

## Pulse workflow

`.pi/workflows/teamwork-pulse.js`:

```js
export default async function (ctx) {
  return await ctx.runs.all([{
    key: 'pulse',
    agent: 'delegate',
    task: `Teamwork pulse in ${ctx.cwd}: run
      python3 ${ctx.cwd}/scripts/teamwork.py pulse --commit, then message every
      assigned lane to start now, give each idle lane its highest-priority
      unblocked task, unblock what is stuck, aim a DIFFERENT Reviewer lane at each
      unclaimed deliverable, and report one short line. Never stop the team while
      loop says CONTINUE.`,
  }]);
}
```

## Rules that cost us real time

- A lane that cannot run `teamwork` needs `TEAMWORK_ROOT=<repo>/.pi/Teamwork/Teams/<Team>`
  exported; a worktree does not carry `.pi/`.
- Worktree isolation is refused on a dirty tree; run lanes in the shared checkout
  and commit with `--paths` so no lane sweeps a peer's uncommitted work.
- A review verdict names the revision it measured; a lane that reviewed a stale
  head is re-dispatched with the head sha and told to assert it first.
- One task, one branch: `branch start` creates the branch from the default branch
  and switches the checkout, so start it before writing and never from a lane
  branch.
