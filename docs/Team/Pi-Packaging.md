# pi packaging - `pi-teamwork`

Owner: CEO. Related: [Plan](Plan.md) · [Board](Board.md) · [Release](Release.md) · [Architecture](Architecture.md)

Why this file: the skill was written host-agnostic and said "Pi" in places where
Pi 1.3.0 has no such tool. This records what a comparable pi package does, what
we changed, and how the published artefact is built.

## 1. What comparable pi packages do

| Package | Shape | What it does well | What it lacks for a team |
|---|---|---|---|
| [`pi-subagents`](../../references/Adapters.md) | extension + skills + prompts, `pi.extensions`/`skills`/`prompts` | real host primitives: `subagent`, `subagent_supervisor`, `contact_supervisor`, durable `schedule.*`, workflows with `runs.all` | no team protocol: no queue, no gate, no audit trail |
| `@tmustier/pi-agent-teams` | extension + one skill | team-shaped prompts and hooks | no evidence gate, no ledger, no role-owned test layers |
| this skill, v1.0.2 | skill + stdlib engine | the protocol: two-stage gate, hash-chained ledger, layered tests, disputes | pi-hostile wording (`teams()`, `schedule_prompt`) and no npm artefact |

## 2. What changed for pi

| Change | Before | After |
|---|---|---|
| Spawn | `teams({action:"delegate", tasks:[...]})` | `subagent({agent, task, async:true, cwd})`, one call per lane; a dependent batch is `subagent({workflow})` with `runs.all` |
| Pulse | `schedule_prompt({type:"cron"})` | `subagent({action:"schedule.create", options:{every:"5m"}})` (pi-subagents persists it under `.pi/subagents/schedules/`) |
| Close | `teams({action:"team_done"})` | `subagent({action:"stop", id})` per live lane, then the report |
| Coordinate | `teams({action:"message_dm"})` | `subagent({action:"steer"})` for a live lane, `subagent_supervisor({action:"reply"})` for a child that asked |
| Package | pip only | `pi-teamwork` npm package: `pi.skills` + `pi.prompts`, host packages in `peerDependencies` only |

The portable skill stays portable: `tests/unit/test_skill_contracts.py` fails if
`SKILL.md` names a host, so the pi specifics live in `skills/teamwork-pi/SKILL.md`
inside the package, not in the core.

## 3. Build and install

```sh
make package                      # assemble dist/pi-teamwork
cd dist/pi-teamwork && npm pack   # 65 files, ~870 kB
pi install npm:pi-teamwork        # or: pi -e ./dist/pi-teamwork for one session
```

`pi install` then `/skill:teamwork` (protocol) and `/skill:teamwork-pi`
(pi tool mapping) are available. Verified on pi 1.3.0: the local install listed
the package and `pi -p "list the skills that contain teamwork"` answered
`teamwork, teamwork-pi`.

## 4. Layout of the published tarball

```text
pi-teamwork/
├── package.json          # name, pi-package keyword, pi.skills/pi.prompts, peer deps
├── skills/teamwork/      # SKILL.md + references/ roles/ templates/ scripts/ src/
├── skills/teamwork-pi/   # the pi adapter layer (six operations, packet shape, pitfalls)
├── prompts/              # teamwork-pulse, teamwork-review
└── README CHANGELOG LICENSE NOTICE SECURITY
```

Single source of truth: `scripts/build_pi_package.py` copies those trees into
`dist/pi-teamwork`; the repository keeps `SKILL.md` at its root because the pip
package and every `scripts/teamwork.py` reference already point there.

## 5. Publishing gates

- [ ] `make package` clean, `npm pack --dry-run` shows only intended files
- [ ] `pi install ./dist/pi-teamwork` lists the package and both skills load
- [ ] `pytest -q`, `ruff`, `mypy`, `links`, `privacy` green on the release commit
- [ ] version bumped in `src/teamwork/version.py` (single source) and CHANGELOG written
- [ ] the npm publish itself is the CEO's step and needs the user's authorization

## 6. Known limits

- Pi has no `teams()`: a lane is a bounded run, so the queue and the ledger carry
  the continuity, not a live teammate object.
- `subagent` worktree isolation refuses a dirty tree, so parallel lanes share the
  checkout and must commit with explicit `--paths`.
- The pi package ships the engine under `skills/teamwork/src`, so `python3` and
  the standard library are the only runtime requirements - no node dependency.
