# CLI: review and governance - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [CLI reference](cli.md)

The review gate and the governance surface: review packets and leases, the
archive, decisions, disputes, red lines and team skills.

This page is one part of the [CLI reference](cli.md) set; the overview lists every group.

## Review and archive

### `review`

```text
teamwork review [AGENT] [HANDLE] [--queue] [--full] [--packet]
    [--claim] [--release] [--renew] [--by BY]
    [--result {pass,fail}] [--evidence EVIDENCE] [--artifact PATH]...
    [--baseline BASELINE] [--replay REPLAY] [--findings FINDINGS]
    [--credit TS-0006[,TS-0007]] [--keep-branch] [--no-merge] [--force REASON]
```

Reviewer: independent second review of a deliverable. `--queue` lists everything
awaiting review. **A pass merges the PR at once** and closes its branch: the
Reviewer that verified the revision runs the merge itself, so a passing review
never waits in a second queue. `--keep-branch` keeps the branch; `--no-merge`
lands only the verdict and leaves the merge to `pr merge`. A fail returns the
task to its owner. `--artifact` binds a verification artifact (hashed into the
ledger) to the verdict; `--baseline` and `--replay` record where the
verification started and how to rerun it. `--force` overrides the review gates
and requires a recorded reason.

Before a pass records anything it runs the same mergeability probe as `preflight`:
`git merge-tree --write-tree <base> <branch>`. When the probe is non-zero - the
branch conflicts with the base it would merge into - the pass is **refused** with
the conflicting paths and the rebase command, exit `2`: no verdict is recorded, the
PR is not flipped to `approved` and the task stays in `review`. That refusal is the
point of the probe: a pass that precedes a merge that cannot happen leaves reviewed
work unlanded behind a green verdict (P-0057 recorded `review_status=passed` and
then died in `pr merge` on a `Board.md` conflict). `--force <reason>` records a
deliberate override of the probe on the task's `forced` field and in the
`review.pass` ledger detail, and that detail **leads** with the override
(`FORCED: <reason> | mergeability overridden: <probe>`) so a Reviewer's full
evidence line can never truncate it away - the queue is local and gitignored, so the
hash-chained ledger is the only durable proof the override happened; git still cannot
land a conflict, so the merge is reported as not run rather than counted as shipped.

Several Reviewers may run at once, so a lane announces what it took:
`review --next --by <reviewer>` claims the highest-priority unclaimed deliverable
and prints its packet in one atomic step, and
`review <role> <T-id> --claim --by <reviewer>` pins a specific one. A claim is a
work lease scaled to its profile - base `ReviewLeaseMinutes` /
`TEAMWORK_REVIEW_LEASE_MINUTES` (20 min) ×1 for a prose diff, ×2 standard, ×4 deep,
capped by `ReviewLeaseMaxMinutes` - so a deep review is not taken over mid-flight
while a prose one frees its item quickly. `--renew` extends it, and `--release`
hands an unfinished one back. `review --next` claims the highest-priority unclaimed
deliverable and prints its packet in one step; it exits `3` when the queue is empty.
A lease nobody renews expires and the next lane takes it over; `--force <reason>` releases another lane's live claim, which is the
case where that lane is dead. The claim, renew and release modes take no
`--result` - the verdict is a separate call.

`--packet` prints what a Reviewer needs before claiming: the inferred profile
(`fast` prose-only, `standard` code, `deep` security/release/data/workflow), the
changed files and diffstat, the author's self-check, the gate set for that profile,
the **credits** available at the revision under review (the passing `tests run`
records another role made there, with their command, and the author's own record
excluded), the layers left **uncovered** for the area, and - on a re-submitted fix
- the review round, the previous findings and the changed files since the failed
revision. `--queue --packet` prints a packet per item.

Review economy: one run per fact per revision. A gate result another role already
recorded at this revision is cited, not re-run. `--credit TS-0006` names the record
your pass relies on; it is validated (the record must exist, be `passing`, carry
the revision under review, and have been run by a role other than the author's) and
recorded in the review evidence as
`credited: TS-0006 integration/harness by Tester @sha`. The Reviewer's own runs are
the requirement check, the `acceptance` layer, the criteria the packet lists as
uncovered, and one sampled credit. `--credit` is refused with `--result fail`:
a fail records findings, not citations. A fail stores the failed revision, so the
next packet is a **delta** review.

A fail also records whether it was **mechanical**, as `review_mechanical` on the
task and as the leading field of the `review.fail` ledger detail. The value comes
from the author's own self-check evidence at the revision under review - the
`preflight: PF-<digest> @<sha> (<n> checks, <k> failed)` line - and is one of:
`no` (a green preflight digest for that same revision is on the record, so the
finding is a judgement call on the work), `unknown` (no green preflight was
recorded for that revision, so the author skipped the gate and the finding may
well be mechanical), or `n/a` (no revision to preflight: a verdict or a records
pass). The point is measurement, not blame: the case for this gate is that most
fails are mechanical, and a rate that cannot be re-counted after the change would
stay an argument. `review.fail` details now begin `mechanical: <value> |`, so
`coordination` can count fails on revisions without a green preflight against
fails on revisions with one. The queue
lists only work the author has submitted - a `todo` has no frozen diff - and is
sorted by priority then age; it prints the lane capacity, the per-profile lease and
the number of expired claims, so the CEO can see when to staff another Reviewer
lane.

Independence is about the **author**, not about a second Reviewer: the author
never reviews or merges its own work, and a Reviewer who co-authored a
deliverable cannot review it. A pass that cannot merge (a conflict, a dirty
tree) keeps the verdict and prints the exact `pr merge` to finish - the work is
then not in the base branch yet, and the message says so.
`--queue` clips each evidence and findings line at 600 characters and marks what it
omitted (`... (+N chars: --full)`); `--full` prints them whole - the stored records
always keep the full text.

### `preflight`

```text
teamwork preflight AGENT HANDLE [--run]
```

The author's mechanical gate, run before `selfcheck`. It is offline, it reads the
local repository and the role queues only, and it fails closed: a check it cannot
measure is a failure, never a pass. One line per check, the exact command that
clears each finding, then the summary and a digest:

```text
PREFLIGHT pass @1a2b3c4d5e6f :: 7 checks, 0 failed
PREFLIGHT digest: PF-0f1e2d3c4b5a @1a2b3c4d5e6f
```

| Check | Fails when |
|---|---|
| `branch` | a branch the record names is not in this repository, the base is not a commit here, the base has moved past the branch (behind), or the branch carries no commit over the base. Two **warnings**, not failures: more than one commit (squash before review) and a task with no branch at all - a verdict, a records pass or a research note legitimately carries no code, and the other revision checks then report `not measured`. |
| `identity` | `identity --audit --range <base>..<branch>` reports a commit that is not authored and committed by a role mailbox, or that carries no `Acting role:` trailer. |
| `evidence` | the task's `evidence`, its `self_note`, or the note the running `selfcheck` is about to store (its `--test` line included) names an `@<sha>` that is not a commit in this repository. |
| `mergeable` | `git merge-tree --write-tree <base> <branch>` is non-zero, naming the conflicting paths; an unanswerable probe (git < 2.38) is a failure, not a pass. The same probe refuses a `review --result pass` and a `pr merge`, so a verdict can never precede an impossible merge. |
| `board` | the branch itself changes `docs/Team/Board.md` and that file disagrees with the queues. A branch that does not carry the board is never charged: the merging Reviewer renders it. |
| `features` | the feature records at the tree this branch would **land** - the base's records with the branch's rows folded in - break the independence rule (`feature check`). A lane's own revision can be green while the merged tree is red, because the record it collides with may live on another branch; the same predicate refuses a `review --result pass` and a `pr merge`. A tree with no records has nothing to judge and passes. |
| `slice` | the diff is past the review profile's slice budget: 6 files / 300 changed lines (`fast`), 12/600 (`standard`), 24/1,200 (`deep`). A **warning**, not a failure: split the task or record in the self-check why it is one coherent contract. |
| `gate` | `PreflightCommand` (below) was run with `--run` and exited non-zero. |

`--run` executes the project's own gate command from the team `Settings.json`,
e.g. `{"PreflightCommand": "make check"}`. Without `--run` it is reported as
`UNVERIFIED: PreflightCommand not run (pass --run): <cmd>`, and with no key in the
file as `UNVERIFIED: no PreflightCommand configured` - the skill names no
toolchain, so an unconfigured gate is not a red preflight. The command is split
with `shlex` and executed without a shell, so a pipeline belongs in a script.

Exit code 0 when no check failed and 1 when one did, so it composes:
`teamwork preflight developer T-0004 && teamwork selfcheck ...`.

### `selfcheck`

```text
teamwork selfcheck AGENT HANDLE [--by BY] [--result {pass,fail}]
    [--note NOTE] [--test TEST] [--baseline BASELINE] [--artifact PATH]...
    [--replay REPLAY] [--force REASON]
```

Author's own review and test before submitting for review. A passing self-check
requires a `--test` line; `--note` records what was re-read, and
`--baseline/--artifact/--replay` attach the rest of the evidence packet. A
`--bug` task is refused until a `tests repro` record exists for it.

A passing self-check also runs `preflight` at the branch head and is refused
while it is red, so the Reviewer never spends a lease on a `git rebase` or an
unreachable evidence revision. The note being recorded is part of that
measurement, not only what was already stored: the `--test` and `--note` text is
scanned for `@<sha>` before it is written, so `--test 'pytest -q @deadbeef -> 1
passed'` is refused instead of certifying a revision the repository does not have.
`--force <reason>` records the honest exception in the ledger and in the task's
`forced` field, naming the check that was overridden.
The evidence line carries the digest the preflight measured, so the Reviewer can
cite the mechanical half instead of repeating it:
`preflight: PF-0f1e2d3c4b5a @1a2b3c4d5e6f (6 checks, 0 failed)`. A `--result fail`
self-check is never blocked: an author reporting their own failure is the point.

### `archive`

```text
teamwork archive [--agent AGENT] [--task T-ID]... [--limit N] [--all] [--full]
```

Show the reviewed-result archive (the team's evidence ledger). The default is the
8 most recent entries; `--limit N`, `--all` and `--full` widen it. `--task T-ID`
(repeatable) prints only the entries whose heading names that task, which is the
read-by-id path: a whole `Archive.md` read is ~0.63M tokens on the current
revision against a ~0.11-0.15M startup, so read the entry the question is about,
not the history. Task ids are per role, so a repeated id can return entries from
more than one role; read the heading's role.

The `self-check`/`author evidence`/`reviewer evidence`/`findings history` lines
are clipped at 600 characters with an `... (+N chars: --full)` marker; `--full`
prints them whole. `docs/Team/Archive.md` itself always stores the full text, and
`pr merge` rewrites only the `branch / merge` line of the matching entry so it
records the real merge revision instead of `pending` - as a committed
`chore(records)` change on the base branch, not as an uncommitted edit. The
entry is written where the task's base branch is checked out, so the base
carries it; a base branch that has no entry yet gets one from `pr merge` before
the merge commit is made.


## The rest of the reference

- [CLI reference](cli.md) - every command, grouped by job.
- [CLI: records and knowledge](cli-records.md) - learning, context, criteria and tests.
- [CLI: review and governance (this page)](cli-review.md) - review, archive, decisions, disputes, red lines, skills.
- [CLI: feature teams and git workflow](cli-workflow.md) - features, branches, PRs, commits, hooks.
- [CLI: audit and control](cli-audit.md) - ledger, trace, coordination, loop, model, scripts.
