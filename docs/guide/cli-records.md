# CLI: records and knowledge - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [CLI reference](cli.md)

Learning, the context tree, acceptance criteria and layered test records. The
commands here write the records that `loop` reads and `audit` verifies.

This page is one part of the [CLI reference](cli.md) set; the overview lists every group.

## Learning

Two team-local stores turn a run into experience: `Roles/<Role>/Lessons.md` for
the mistakes a role will not repeat, and `Knowledge.md` at the team root for
durable project facts. Both are gitignored and never committed, and both are
written only through the commands below - a hand edit is a defect, not a
shortcut.

### `lesson`

```text
teamwork lesson {add,list,show,fix} ...
```

A lesson is one recorded mistake: the observable failure, its cause, the rule the
role now follows, and the evidence that proved it. Ids are `L-` plus four digits
and are globally unique across the team (allocated from the maximum over every
role's file). `load` prints the role's open lessons at startup.

#### `lesson add`

```text
teamwork lesson add --by BY --mistake TEXT --cause TEXT --rule TEXT --evidence TEXT
    [--role ROLE] [--task TASK]
```

Record a mistake. `--by`, `--mistake`, `--cause`, `--rule` and `--evidence` are
all required; `--role` defaults to the actor's role, and `--task` records the
`T-` id it happened on. A missing required flag is an argparse usage error
(`2`); an empty value or a role with no instance exits `1`.

#### `lesson list`

```text
teamwork lesson list [--role ROLE] [--status open|fixed|all]
```

List lessons, one line each, sorted by id. Defaults: every role, `--status all`.
Each row is:

```text
- L-0001 [open] developer: <mistake> -> <rule> (skill: tw-name | no skill)
```

#### `lesson show`

```text
teamwork lesson show L_ID
```

Print one lesson, every field in record order, then its file. An unknown id exits
`1`.

#### `lesson fix`

```text
teamwork lesson fix L_ID --by BY [--rule RULE] [--skill TW_NAME] [--evidence EVIDENCE]
```

Close a lesson. On an `open` lesson it sets `status: fixed` and updates the date;
`--rule` replaces the rule, `--skill` must name a registered `tw-` skill of kind
`mistake` (exit `1` otherwise), and the evidence stays unless `--evidence` is
given. On an already `fixed` lesson the command is allowed only with new
`--evidence` - a re-proof of the fix - and otherwise exits `1` naming the skill
that fixed it, changing nothing.

The other order is equally valid: `skill create --from-lesson L-0001` creates the
mistake skill and marks the lesson `fixed` in the same command. Either way the two
records link to each other.

### `knowledge`

```text
teamwork knowledge {add,list,search,show,touch} ...
```

The shapes are frozen in `docs/Team/Architecture.md` sections 15.2 and 16.5. The
records live in `Knowledge.md` at the team root, shared by every role, gitignored
and never committed; a missing file is an empty store, never an error.

#### `knowledge add`

```text
teamwork knowledge add --by BY --topic TEXT --statement TEXT --evidence TEXT
    [--kind KIND] [--tags TAGS] [--importance 1-5] [--supersedes K-ID] [--task T]
```

Record one durable fact, rule, command or measured behaviour. `--by`, `--topic`,
`--statement` and `--evidence` are required; `--topic` is at most 120 characters
and `--statement` at most 500 (one line each); `--tags` defaults to empty and is
normalised to a lower-case kebab comma list; `--importance` defaults to `3`. On
success it prints `# K-0001 recorded: <topic>` then `- path: <Knowledge.md>`.

`--kind` is `fact` (default), `experience`, `preference`, `gotcha` or `rule`. An
unknown value exits `2`; a record written without the field reads as `fact`, so
older records need no migration. The field is written after `statement`. `list`
and `search` accept `--kind` to filter; `show`, `load` and the context L0 display
it. The duplicate key is unchanged: kind is metadata, not identity.

A duplicate is **active-only** and exact: both the normalised `topic` and the
normalised `statement` are equal (whitespace collapsed, case-folded). `add`
applies this precedence:

1. An exact active duplicate returns the existing id and exits `0` with
   `# K-0003 already records this: <topic>`, adding no second entry. If
   `--supersedes K-0002` is also given, K-0002 must be active; it is marked
   `superseded` with `superseded_by: K-0003`. A target that is the duplicate
   itself or already inactive exits `2`.
2. Otherwise an active record with the same topic and a different statement is
   refused with exit `2`:
   `topic '<topic>' is already claimed by K-0002; pass --supersedes K-0002 to replace it`.
3. Otherwise the new record is created active.

Re-adding a fact whose only match is `superseded` is not a duplicate: when no
active record claims the topic the command creates a new active record and the
old fact stays history. `--supersedes` retires the current holder and records the
edge on the new record; a nonexistent target, the record itself, or an
already-superseded target exits `2` naming the active record at the end of its
chain. The one exception is reinstating an exactly matching retired fact, whose
id may be named; it rewrites no `superseded_by`. Knowledge is never silently
deleted, only superseded.

#### `knowledge list`

```text
teamwork knowledge list [--tag TAG] [--role ROLE] [--kind KIND]
    [--status active|superseded|all] [--limit N]
```

List records, default `--status active` and `--limit 20` (`0` means all), with no
role, kind or tag filter until asked. `--role` matches the `owner` field
(provenance, not a permission), `--kind` keeps only that kind, and `--tag`
matches one tag in the record's list. Rows are ordered by importance descending,
then uses descending, then updated descending, then id ascending:

```text
- K-0001 [active] importance=3 uses=2 tags=build,ci: <topic> - <statement>
```

An empty tag list renders `tags=-`. The last line is exactly
`# knowledge: N active, M superseded, T use(s)`.

#### `knowledge search`

```text
teamwork knowledge search QUERY [--kind KIND] [--status active|superseded|all] [--limit N]
```

Case-insensitive substring match over `topic`, `statement` and `tags`, read-only,
with the same rows and ranking as `list`. It defaults to active records and
`--limit 20`; `--kind` keeps only that kind; `--status superseded|all` reads the
history. No match prints `# no knowledge matched "<query>"` and exits `0`.

#### `knowledge show`

```text
teamwork knowledge show K_ID
```

Print one record's fields in record order, including `kind`, and its file. A
superseded record still prints its status and `superseded_by`: history is
readable, not hidden. An unknown id exits `2`.

#### `knowledge touch`

```text
teamwork knowledge touch K_ID --by BY
```

Increment `uses`, update the date and print `# K-0001 uses=N`; an unknown id
exits `2`. Touch a record you actually used - it is what makes the ranking follow
need rather than volume.

Startup ranking: `load` prints the top 10 **active** records project-wide, one
line each (`- [K-0001] [experience] <topic>: <statement> (uses=N, tags=...)`),
then
`# project knowledge: N active, M superseded; search: teamwork.py knowledge search "<topic>"`.
The cap is fixed at 10 and the order is `list`'s, so every agent reads the most
important and most used facts, not the newest ten.

Evidence and privacy: a record without evidence is opinion, and a statement
whose evidence names no command, path or dated source is refused at review.
Never store a secret, credential, token or personal data. A decision cites the
`K-` record **and its evidence**, never the record's authority.


## The rest of the reference

- [CLI reference](cli.md) - every command, grouped by job.
- [CLI: records and knowledge (this page)](cli-records.md) - learning, context, criteria and tests.
- [CLI: review and governance](cli-review.md) - review, archive, decisions, disputes, red lines, skills.
- [CLI: feature teams and git workflow](cli-workflow.md) - features, branches, PRs, commits, hooks.
- [CLI: audit and control](cli-audit.md) - ledger, trace, coordination, loop, model, scripts.
