# RELEASE - build, ship, roll back

Owner: Release Engineer. The canonical answer to "how does this get built, shipped,
verified and reverted". Keep it executable: every command here must run as written.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Archive](Archive.md)

## Build

| step | command | expected result |
|---|---|---|
| clean checkout | | |
| build | | |
| package / artefact | | |
| provenance (hash, signing) | | |

## CI gates

| gate | command | blocks a merge? |
|---|---|---|
| | | |

## Deploy

- environments and what differs between them:
- order of operations (migrations first? feature flag?):
- configuration and secrets *mechanism* (never values):

## Rollback

- one command to return to the previous version:
- what is *not* reversible (data migrations) and how it is handled:
- last drill: `<command> @<rev> -> <result>` (date, duration, outcome)

## Observability

- metrics, logs, traces, dashboards:
- alerts and their thresholds:
- runbooks:

## Sources

- [title](https://full-url) - accessed YYYY-MM-DD
