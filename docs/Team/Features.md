# Features - feature teams (one record per vertical slice)

Owner: Project Manager.

> The independence map (docs/Team/Architecture.md 13). Every record's
> `paths` is its whole write set; `feature check` refuses two open records
> that own one path. Field authority: `owner`, `statement`, `paths`,
> `depends-on` and the `active`/`done`/`dropped` transitions belong to the
> record's owner; `interface` and the `ready` transition belong to the
> Architect; the id, the dates and every validation belong to the command.

Related: docs/Team/Architecture.md (the frozen rules) and docs/guide/cli.md (this command surface)
