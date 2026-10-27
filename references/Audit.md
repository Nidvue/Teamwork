# Recording, traceability and audit

Reference for the /teamwork skill. Loaded on demand.

Related: [Evidence](Evidence.md) | [Roles](Roles.md) | [Engineering](Engineering.md) | [State](State.md) | [Docs](Docs.md) | [Testing](Testing.md) | [Concurrency](Concurrency.md) | [Coordination](Coordination.md)

## What is recorded

Every piece of state is a record with provenance, not a note in a chat:

| Record | Where | Provenance |
|---|---|---|
| Memory entry | `Roles/<Role>/ShortTermMemory.md`, `LongTermMemory.md` | `by`, `src`, `rev` on every entry |
| Task | `Roles/<Role>/TaskQueue.md` | `claimed_by`, `branch`, `pr`, `area`, `evidence`, `reviewer`, `merge_commit`, `forced` |
| Acceptance criterion | `Criteria.md` | owner + the verifying instance and its evidence |
| Test layer | `Tests.md`, `TestPlan.md` | owner role, runner, command, evidence, revision |
| Review / PR | `Reviews.md` | author, branch, reviewer, verdict, merge revision |
| Dispute | `Disputes.md` | raiser, opponent, every round, signatures, ruling |
| Decision | `docs/Team/Decisions.md` | decider, evidence, falsifier, consequences |
| Accepted result | `docs/Team/Archive.md` | what shipped, by which instance, verified how, at which revision |
| **Every mutation** | `Ledger.jsonl` | timestamp, actor, role, action, target, detail, revision |

Nothing is written without naming who wrote it and what it came from.

## The ledger

`Ledger.jsonl` is append-only. Each line is one record:

```json
{"ts":"2026-10-17T20:08:43","n":7,"actor":"developer-1","role":"developer",
 "action":"commit","target":"T-0001","detail":"feat(auth): src/auth.py | 2 file(s) e257f69",
 "rev":"e257f69","prev":"<hash of record 6>","hash":"<sha256(prev + canonical record)>"}
```

`hash = sha256(prev_hash + canonical_json(record))`, so records are chained: editing
or deleting any line breaks every hash after it.

Actions cover the whole lifecycle: `memory.add|update|promote|drop|merge|evict`,
`task.add|claim|status|evidence|reclaim`, `selfcheck`, `review.pass|fail`,
`pr.open|merge`, `branch.start|retire`, `criteria.add|verify`, `tests.add|run`,
`dispute.open|round|escalate|sign|resolve`, `decision.add`, `commit`, `ledger.export`.

Memory maintenance is logged too, so a fact never disappears silently: promotion,
dropping, key-merging and archive eviction each write a record with the entry key.

## Internal audit

```sh
teamwork.py trace <T-id|AC-id|TS-id|P-id>   # one claim, end to end
teamwork.py ledger show --tail 40 [--action review.pass] [--actor reviewer-1]
teamwork.py ledger verify                    # recompute the chain
teamwork.py audit                            # trail health + provenance + coverage
teamwork.py loop                             # a broken trail blocks STOP
```

`trace` joins the task, its commits, the PR, the review, the tests, the criteria and
the ledger events into one chronological view: claim -> evidence -> commit -> review
-> merge -> archive.

`audit` reports: chain problems, memory entries without `by` provenance, decisions
without evidence, a ledger that shrank since the last export, plus the usual gates,
coverage and branch checks.

## External audit

`teamwork.py ledger export` writes two committed artifacts that a third party can
check **without trusting the team**:

- `docs/Team/AuditManifest.json` - team, project, git revision and branch, ledger
  record count and head hash, a sha256 digest for every committed state artifact
  except `docs/Team/Archive.md` (append-only: it gains an entry when a review
  passes, so a digest committed beside it would be stale by construction; its
  entries are followed through the ledger), and the exact verification steps.
- `docs/Team/AuditReport.md` - the human summary of the same facts.

Verification procedure (reproducible by anyone with the repository):

```sh
teamwork.py ledger verify --reconcile   # recompute the chain; a head cache left
                                        # behind by a crash is repaired, a removal
                                        # of records is reported
teamwork.py ledger repair --by <instance> --reason "<why>"   # drop a torn tail
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
git cat-file -t <git.head>   # the reviewed revision still exists
teamwork.py trace <T-id>     # follow any individual claim
```

What each check proves:

| Check | Proves |
|---|---|
| hash chain + head hash | the trail was not edited, reordered or truncated after export |
| `verify --reconcile` | a crash artefact is distinguishable from tampering: a stale cache is repaired, a *shrinking* ledger is reported |
| `ledger repair` | a torn tail is recoverable, and the repair itself is a logged record |
| artifact digests | the records themselves are byte-identical to the reviewed state |
| git revision | the work that was accepted is the work that exists |
| per-record provenance | every claim can be attributed to an instance, a role and a revision |

The manifest separates **externally verifiable** artifacts (committed project
output under `docs/Team/`) from **local_state** (hidden working state under
`.pi/`, only checkable on the machine that produced it). The export records its own
`ledger.export` event *before* capturing the checkpoint, so `ledger verify` after
an export matches the manifest exactly.

`AuditManifest.json` should be committed with the milestone it covers (the Reviewer
can include it in the `chore(records)` commit), so the head hash becomes a
checkpoint in git history - and a later truncation of the ledger is then detected
by comparing against it.

## Honest limits

- The ledger is tamper-**evident**, not tamper-**proof**: anyone with write access
  can rebuild it, but they cannot reproduce the exported head hash without also
  rewriting the committed manifest, and the manifest's git history is append-only.
- Identity is accountability, not cryptography: `--by` names an existing instance,
  and every action it performs is recorded against it. It does not prove which OS
  process typed the command.
- A record proves that something was declared, with the evidence that was given.
  Whether the evidence proves the claim is what the Reviewer and `criteria verify`
  are for: both require an independent role.
