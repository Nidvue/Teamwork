# Features - feature teams (one record per vertical slice)

Owner: Project Manager.

> The independence map (docs/Team/Architecture.md 13). Every record's
> `paths` is its whole write set; `feature check` refuses two open records
> that own one path. Field authority: `owner`, `statement`, `paths`,
> `depends-on` and the `active`/`done`/`dropped` transitions belong to the
> record's owner; `interface` and the `ready` transition belong to the
> Architect; the id, the dates and every validation belong to the command.

Related: docs/Team/Architecture.md (the frozen rules) and docs/guide/cli.md (this command surface)


## F-0001 · Green CI under a bounded, reproducible gate: local/CI parity, proof-once, docs-on-prose pushes, measured budgets
- owner: TeamLeader
- interface: Architecture.md#9
- paths: .github/workflows/, scripts/, tests/, docs/guide/ci.md, docs/Team/Evolution.md
- depends-on: -
- state: ready
- created: 2026-11-05
- updated: 2026-11-05
