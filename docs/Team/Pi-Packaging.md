# pi packaging - `@nidvue/teamwork`

Owner: CEO. Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Release](Release.md) · [Architecture](Architecture.md)

Why this file: the skill was written host-agnostic and said "Pi" in places where
Pi 1.3.0 has no such tool. This records what a comparable pi package does, what
we changed, and how the published artefact is built.

## 1. What comparable pi packages do

| Package | Shape | What it does well | What it lacks for a team |
|---|---|---|---|
| `@tmustier/pi-agent-teams` | extension + one skill | team-shaped prompts and hooks | no evidence gate, no ledger, no role-owned test layers |
| this skill, before the pi layer | skill + stdlib engine | the protocol: two-stage gate, hash-chained ledger, layered tests, disputes | pi-hostile wording (`teams()`, `schedule_prompt`) and no npm artefact |

## 2. What changed for pi

| Change | Before | After |
|---|---|---|
| Spawn | `teams({action:"delegate", tasks:[...]})` | the engine's own lane runtime: `teamwork.py lane start` detaches one host CLI child per lane, writes its packet and record, and reconciles it later - no extension required |
| Pulse | `schedule_prompt({type:"cron"})` | `teamwork.py swarm run`: waves computed from the board (ready tasks, reviews, free slots, unfinished assignments) and **sized by the measured weight of the work**, each lane under a hard per-profile minute budget; `pulse --commit --spawn` runs one wake end to end |
| Close | `teams({action:"team_done"})` | `teamwork.py lane stop <run>` per live lane (`lane reap` for a dead one), then the report |
| Coordinate | `teams({action:"message_dm"})` | the `Agents/<Instance>/Inbox.md` mailbox, plus the board's claims; no host messaging tool is required |
| Package | pip only | the `@nidvue/teamwork` npm package: `pi.skills` + `pi.prompts`, host packages in `peerDependencies` only, no third-party package of any kind |

The portable skill stays portable: `test_adoption_surfaces_stay_agent_agnostic`
(`tests/unit/test_skill_contracts.py`) scans eight adoption surfaces - `README.md`,
`docs/index.md`, `docs/guide/install.md`, `docs/guide/quickstart.md`,
`docs/guide/cli.md`, `docs/guide/architecture.md`, `assets/demo.svg` and `SKILL.md` -
and fails on a host name, so the core talks about "the teammate tool".
`references/Adapters.md` is deliberately not scanned: it is the adapter table and
must name the host. The same test globs every `roles/*.md` (those ship inside the
package) and fails on a host tool call - `subagent(`, `subagent_supervisor(`,
`schedule.create` or `teams(` - because that is the same portability regression as
one in `SKILL.md`; provider and model names are content, not a host dependency, so
they are not scanned. The concrete pi launcher (`pi -p`) lives in
`skills/teamwork-pi/SKILL.md` and in the adapter table.
`tests/unit/test_pi_package.py` then pins the package itself: licence field,
shipped files, host-only peers with no third-party package at all, no
duplicated pi layer, runnable engine.

### No third-party package

The manifest declares the five host-provided packages (`@earendil-works/pi-ai`,
`-agent-core`, `-coding-agent`, `-tui`, `typebox`) as peers, and nothing else - not
as a `dependency`, not bundled, not as an optional peer.

Why nothing else:

- The lanes run on the engine's own runtime: `lane start` and `swarm run` detach
the host CLI (`pi -p`), so the package needs no extension to be installed beside
it. A session with no plugin at all runs the whole team in parallel.
- Pi installs a package's `dependencies`, but an extension that lands in our
  `node_modules/` does not load unless the manifest points at
  `./node_modules/<name>/...`: "Other Pi packages used as dependencies must be
  included in the published tarball and referenced through their `node_modules`
  resource paths" - Pi's package docs, section *Declare dependencies*, read from
  the installed CLI on 2026-11-09 (`docs/packages.md` under the
  `@earendil-works/pi-coding-agent` package). This package declares no extension,
  so any such entry would promise a tool nobody loads.
- Naming a plugin as an optional peer still tells an installer the package is
  written against that plugin. It is not: the adapter names the engine commands,
  and `tests/unit/test_pi_package.py` fails if a plugin tool or a third-party
  package name appears in the built manifest or in the pi layer.

## 3. Build and install

```sh
make package                                 # assemble dist/@nidvue/teamwork
cd dist/@nidvue/teamwork && npm pack         # npm reports the file count and size
pi install npm:@nidvue/teamwork              # or: pi -e ./dist/@nidvue/teamwork for one session
```

`pi install` then `/skill:teamwork` (protocol) and `/skill:teamwork-pi`
(pi tool mapping) are available. No other package is needed or suggested: the
lanes are launched by the engine, so `pi` alone is enough.
 Verified on pi 1.3.0: the local install listed
the package and `pi -p "list the skills that contain teamwork"` answered
`teamwork, teamwork-pi`. The tarball root carries `package.json`, `skills/`,
`prompts/`, `README.md`, `LICENSE`, `NOTICE`, `CHANGELOG.md`, `SECURITY.md`. Both
the file count and the unpacked size move with every edit, so they are read from
`npm pack`, never quoted in prose.

## 4. Layout of the published tarball

```text
@nidvue/teamwork/
├── package.json                     # name, pi-package keyword, pi.skills/pi.prompts, peer deps
├── skills/teamwork/                 # SKILL.md + references/ roles/ templates/ scripts/ src/
├── skills/teamwork-pi/SKILL.md      # the pi adapter layer (six operations, packet shape)
├── prompts/                         # teamwork-pulse.md, teamwork-review.md
├── extensions/teamwork-status.ts    # the optional live agent widget (no dependency)
└── README.md CHANGELOG.md LICENSE NOTICE SECURITY.md
```

Single source of truth: `scripts/build_pi_package.py` copies those trees into
`dist/@nidvue/teamwork`; the repository keeps `SKILL.md` at its root because the pip
package and every `scripts/teamwork.py` reference already point there.

## 5. Publishing gates

- [ ] `make package` clean, `npm pack --dry-run` shows only intended files
- [ ] the built `package.json` declares the host packages as peers and no
      third-party package in `peerDependencies`, `dependencies` or
      `bundledDependencies`
- [ ] `pi install ./dist/@nidvue/teamwork` lists the package and both skills load
- [ ] `pytest -q`, `ruff`, `mypy`, `links`, `privacy` green on the release commit
- [ ] version bumped in `src/teamwork/version.py` (single source) and CHANGELOG written
- [ ] the npm publish itself is the CEO's step and needs the user's authorization

## 6. Known limits

- Every lane is a detached child process of the engine, so a lane that dies is a
  record with a dead pid (`lane reap` reconciles it) - not a lost teammate
  object. The queue and the ledger carry the continuity.
- Parallel lanes each get their own git worktree (`lane start --worktree`,
  `Runtime/Worktrees/<Instance>/<T-id>`) and must commit with explicit `--paths`,
  so no lane sweeps a peer's uncommitted work.
- The pi package ships the engine under `skills/teamwork/src`, so `python3` and
  the standard library are the only runtime requirements - no node dependency.
- No third-party package is declared, required or suggested: every lane runs
  through `lane start` / `swarm run`, which launch the host CLI itself.

## The status extension

The package ships one optional pi extension of its own,
`extensions/teamwork-status.ts`. It renders live agent state from
`teamwork.py status --json` in the smallest shape that answers "who is working on
what, and is it moving":

```text
teamwork · 21 act · 6 live · 8 busy · 2 review
⚙ L-0383 Developer-1 T-0130 run     12m deepseek/deepseek-chat
⚙ L-0381 Reviewer-1  -       run      4m host
● Developer-2 T-0070 19s · tests.run TS-0214 - 76 passed in 35s   12m ███░░  60% deepseek/deepseek-chat
● Reviewer-2  ↳T-0071 4m · review.pass T-0062 - Re-derived the mechanism, then mutated it   8m ██░░░  35% host
○ idle: 9 (activated 21)
```

The header counts activated instances, live lanes, busy instances and review
claims. After it, one line per **live** lane only (at most 3, in the feed's
order: live first, then newest; an ended lane is history and is not displayed):
`⚙ <id> <instance> <task> <state-abbrev> <elapsed> <model>` with the model
clipped to 22 columns and `host` when the feed carries no model - never a guess.
Then **one line per busy instance**, ordered by progress, carrying the latest
command that instance ran (`last`, from the ledger) and how long ago it ran
(`last_seconds`), then the lane elapsed, the progress bar and the model: a busy
row is the agent's live activity, not a static title, and it falls back to the
task title only when the feed carries no event. A review handle prints as `↳T-0071`
so the role prefix does not eat the column; every idle instance collapses into
**one count** (`○ idle: 9 (activated 21)`) - the widget never names an idle agent.

The widget renders to the **real terminal width** (100 columns when the width is
unknown, e.g. print mode) and clips each row to it, so a wide terminal shows the
whole command and a narrow one truncates it with an ellipsis: a row is always one
line and never wraps. It never exceeds 24 lines, a footer status line carries the
busy/total count, and it refreshes every 2 s by `execFile`-ing `python3 <engine>
status --json` at the team tree found by walking up from the session cwd. It is
silent when no engine is found, and `/teamwork-status` toggles it off and on.

It imports only `node:` built-ins and the host peer packages, so installing the
package adds no dependency; removing the file changes nothing in the protocol.
`tests/unit/test_pi_package.py::test_the_status_extension_ships_and_imports_only_host_peers`
pins the shipped path, the manifest entries and the import allowlist, and
`tests/unit/test_pi_status_render.py` **executes** `render()` through node's type
stripping on a synthetic payload and on the bare payload `status --json` emitted
before titles existed - the round-1 defect was an extension whose only test read
its source text, so a renderer that threw on the first refresh passed.
