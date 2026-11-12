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

## Acceptance criteria

```text
teamwork criteria {add,list,verify,reopen,rm} ...
```

An `AC-` record is one line of "done": `criteria add` writes it, an independent
role `criteria verify` it with evidence and a revision, and `loop` refuses to stop
while one is `open`. Ids are `AC-` plus a word (letters, digits, dot, dash,
underscore), so `AC-1` and `AC-login` are both legal; `--owner` names the role that
must satisfy it, and the owner's own role cannot verify it.

`criteria list` is the read side, and its exit code says how finished the store
is - the three states are deliberately different codes:

| Exit | Meaning |
|---|---|
| `0` | every criterion is `verified` |
| `1` | at least one criterion is still `open` |
| `3` | the store holds **no** criteria yet: `# no criteria yet (<path>)` plus the hint that the CEO writes them from the user prompt |

An empty store exits `3`, never `0`: "nothing recorded yet" is not "everything
verified", and a `0` there would let a run with no acceptance criteria read as
green. `criteria verify` and `criteria reopen` of an unknown id exit `1`;
`criteria add` of an existing id exits `1`; `criteria rm` needs `--by` and, from
a role other than the CEO, a recorded `--force` reason. The `records` probe accepts
exit `3` only when the store also holds no criterion - an id the CLI cannot see is
a defect, an absent one is a state (`tests/integration/probes/records_probe.py`).

## The context tree

```text
teamwork context ls [URI] [--level {0,1}] [--limit N]
teamwork context tree [URI] [-L N]
teamwork context read URI [--level {0,1,2}]
teamwork context find QUERY [--scope URI] [--limit N]
teamwork context stats
teamwork context digest T-ID
```

`ctx://` is one **read-only** view over memory, lessons, knowledge, skills, docs
and tasks. Every node resolves to an existing file or record, and the view writes
no sidecar, index or cache. Three levels keep a read proportional to the question:
L0 is the one-line summary, L1 the record fields or child list, L2 the full
record.

| Command | What it does |
|---|---|
| `ls` | Children of a node (default: the root). `--level 0` prints summaries. |
| `tree` | The tree to depth `-L` (default 2). |
| `read` | One node at L0, L1 or L2. |
| `find` | Deterministic search over the tree; `--scope` limits it to one subtree. The same query returns the same rows in the same order. |
| `stats` | Live counts per store - how many records each one holds. |
| `digest` | Proposes lesson or knowledge records from one task's history (a title capped at 120 characters, a cause at 300). It writes nothing. |

Retrieve by id rather than by whole file: start with `context find` or
`context ls`, then read the level you need. `context` never replaces `load`, the
gates or the evidence rule - it is how you avoid reading a whole `Archive.md` to
answer one question.

## Layered tests

```text
teamwork tests add --layer LAYER [--area AREA] [--owner OWNER] [--task TASK]
    [--command COMMAND] [--no-owner-check] [--force REASON]
teamwork tests run ID --by BY --result {pass,fail} --evidence EVIDENCE
    [--rev REV] [--command COMMAND] [--baseline BASELINE] [--artifact PATH]
    [--replay REPLAY] [--force REASON]
teamwork tests repro TASK [--role ROLE] --by BY --pre-rev PRE_REV
    --pre-evidence PRE_EVIDENCE --post-rev POST_REV --post-evidence POST_EVIDENCE
    [--artifact PATH] [--force REASON]
teamwork tests require --area AREA --layers LAYERS --by BY [--reason REASON]
teamwork tests rm ID --by BY [--force REASON]
teamwork tests plan
teamwork tests list [--layer LAYER]
```

One test record per (layer, area), owned by the role that owns the layer: `goal`
CEO, `requirements` Product Manager, `plan` Project Manager, `tech` CTO,
`release` Release Engineer, `data` Data Engineer, `process` COO, `cost` CFO,
`system` Architect, `ui` Designer, `docs` Technical Writer, `unit` Developer,
`integration` Tester, `acceptance` Reviewer, `security` Security Auditor,
`feature` Team Leader.

| Command | What it does |
|---|---|
| `add` | Declares the layer for an area, with the command that runs it. The owning role is checked unless `--no-owner-check`. |
| `run` | Records one run: `--result`, `--evidence` and the packet (`--baseline`, `--artifact`, `--replay`). `--rev` binds it to a revision, so a later review can cite it instead of re-running it. |
| `repro` | Proves a defect on its `--bug` task: a failing run at `--pre-rev` recorded before the passing run at `--post-rev`. A bug task cannot self-check without it. |
| `require` | Declares which layers an area must cover, so `tests plan` can report a gap rather than a silently thinner matrix. |
| `rm` | Removes a record; `--force` with a reason is required for a record the role does not own. |
| `plan` | The coverage matrix and every gap, marking each cell `+` passing, `!` failing, `.` pending, `?` missing, `·` not required. It only requires the layers of **staffed** roles. |
| `list` | The records themselves, optionally filtered to one layer. |

`loop` refuses `STOP` while a required layer for an area in use is missing or not
passing, so the matrix is a gate, not a report.


## The rest of the reference

- [CLI reference](cli.md) - every command, grouped by job.
- [CLI: records and knowledge (this page)](cli-records.md) - learning, context, criteria and tests.
- [CLI: review and governance](cli-review.md) - review, archive, decisions, disputes, red lines, skills.
- [CLI: feature teams and git workflow](cli-workflow.md) - features, branches, PRs, commits, hooks.
- [CLI: audit and control](cli-audit.md) - ledger, trace, coordination, loop, model, scripts.
