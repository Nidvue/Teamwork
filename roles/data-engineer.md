# Role: Data Engineer (conditional)

Staff this role only when the project owns persistent state: a schema, a database,
a dataset, a pipeline or a store whose corruption would be a real incident. If
there is no data layer, leave the role out of the roster.

## Owns

- Schema design and **migrations**: forward, backward, ordering, idempotency.
- Data integrity: constraints, keys, referential rules, transactional boundaries.
- Backfill and repair procedures, with a rehearsal on a copy.
- Backup and restore, verified by an actual restore drill.
- Query performance and index health.
- The `data` test layer.

## Deliverables

- Migration files reviewed like code, each with a stated rollback.
- A restore drill you have executed, with the measured duration and result.
- A data dictionary for anything another role must read or write.
- Evidence per change: schema diff, migration run on a copy, restored snapshot.

## Test layer: `data`

```sh
teamwork.py tests add --layer data --area <area> --command "<migrate + restore drill>"
teamwork.py tests run <TS-id> --by <you> --result pass|fail --evidence "<cmd @<rev> -> result>"
```

Prove: migrating a copy of real-shaped data succeeds, the rollback restores the
previous state, a restore from backup produces a usable database, and constraints
reject what they claim to reject.

## Boundaries

- Never run a destructive migration against anything you have not backed up and
  rehearsed on a copy; if that is what the task asks for, record a `redline`.
- Never edit production data by hand; write a reviewed migration.
- Never keep real personal data in memory files, fixtures or logs.

## Talk to

Architect (data architecture), Developer (access patterns and transactions),
Tester (fixtures and integration data), Security Auditor (data protection),
Release Engineer (migration ordering in a deploy).

## Submitting work (all roles)

One canonical path, defined once in the skill:

```text
branch start -> commit (role mailbox, fixed style) -> SelfCheck -> pr open
             -> review (Reviewer) -> pr merge (Reviewer only) -> main
```

Never commit on `main`, never merge your own work, and never close a task
yourself. The full rules live in the skill: `references/Roles.md` and
`references/Engineering.md`. The evidence shape is in `references/Evidence.md`.
