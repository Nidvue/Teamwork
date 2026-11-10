# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Archive](Archive.md)

## Snapshot

- Date: - Milestone: - Verified criteria: <n>/<m>

## Task table

One row per task in the shared role queues; `teamwork.py board --write` renders
this table and the In-flight table below from `Roles/*/TaskQueue.md`, so both are
the queues' state and not an opinion about it.

| role | id | area | state | pr | merged revision |
|---|---|---|---|---|---|

Rows whose PR is not merged carry no merged revision; the revision is read from
the PR record, not from this table.

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|

The task queue (`teamwork.py task list <role>`) is authoritative for a task's
exact state; this table only says which lanes are open.

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| | | | |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| | | |
