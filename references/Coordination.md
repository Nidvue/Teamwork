# Coordination safety

Reference for the /teamwork skill. Loaded on demand; `SKILL.md` keeps the
operating procedure.

Owner: CEO.

Related: [Engineering](Engineering.md) | [Evidence](Evidence.md) | [Docs](Docs.md) | [State](State.md) | [Concurrency](Concurrency.md) | [Dissent](Dissent.md) | [Roles](Roles.md) | [Testing](Testing.md) | [Audit](Audit.md) | [Coordination](Coordination.md)

## 1. Why this reference exists

Source: [Measuring multiagent systems](https://www.anthropic.com/research/multiagent-systems) - accessed 2026-10-27.

The paper's useful finding for this skill is structural, not motivational:

- Coordination does **not** emerge from stronger individual agents. It has to be
  designed into the environment.
- Agents sharing a model, a context and a queue behave alike. When one makes a
  bad decision, many make it, so isolated errors become systemic failures.
- The failures are measurable: merge fraction, duplicate work, polling
  stampedes, collusion, gullibility, echoed reviews and abandoned branches.

A rule that only asks agents to "coordinate well" changes nothing. Every section
below pairs the observed failure with a mechanism the engine can check, so the
team is judged by its records rather than its intentions.

## 2. Failure modes and the team's mechanism

| Failure | Measured behaviour | Mechanism here |
|---|---|---|
| Conformity | 18/30 agents created the same branch; half built the same project | unique branch per task; duplicate-task detection; different models for verification lanes |
| Stampede | 2.4M job requests for 117 accepted slots | slot leases, `LANE_WIP`, pulse defers past free capacity |
| Turf war | agents killed each other's processes and locked accounts | reclaim refuses a live lane; de-escalation ladder; resource-denial red line |
| Gullibility | listener trusted a lying scout; group converged on shared facts | independent evidence, source+date for external claims, blind-first review |
| Echo / rubber-stamp | peer review that repeats the author | reviewer's own run for the irreducible core; echo and monoculture checks; sampled second review |
| Duplicated review work | every review re-runs a suite another lane already ran at the same revision | credits (`--credit`), delta re-review after a fail, `C-REVIEW-DUP` / `C-REVIEW-NOCREDIT` |
| Collusion | price floors agreed through a public board | no author approval, no gate lowered by agreement, one claim per deliverable |
| Merge collapse | 80 agents opened 980 PRs and merged few | branch per task, rebase before review, one writer per file, pass = merge |
| Taste | playable games that were unplayable | user-facing demo at the milestone; Designer owns visual assets |

## 3. Conformity: identical lanes make identical mistakes

Two lanes with the same model, the same context and the same queue are not two
independent checks; they are one check sampled twice.

- **Verification lanes use a different model when one is available.** Set
  `TEAMWORK_MODEL_ALT`; `model auto --apply` alternates it across Reviewer,
  Tester and Security Auditor instances. `coordination` reports
  `C-DIV-MODEL` when every lane still resolves to one model.
- **One task, one branch, one claim.** `branch start` names the branch from the
  task id, so two tasks can never share one by accident. A duplicate title or a
  shared board reference is a defect (`C-DIV-TASK`, `C-DIV-SHARED`), not parallel
  efficiency.
- **An independent derivation is a real deliverable.** For a high-risk decision,
  give two lanes the same question and no sight of each other's work, then
  compare. Do not average their answers: agreement is only evidence when the
  derivations were independent.

## 4. Stampede and starvation

A queue that every lane polls rewards the fastest retry, not the best work. The
measured case: thirty requests per second per agent, 2.4 million requests, 117
jobs accepted.

- **A lease, not a poll.** `slot acquire` is atomic and fails at the cap with
  exit 3. A lane that cannot get a lease does slot-free work or fans out on
  another provider; it never spins.
- **The pulse plans no more new lanes than free slots.** It defers the tail and
  says so. A top-up for a lane that already holds a lease is not a new lane.
- **Back off, do not retry tighter.** One retry after a recorded failure, then
  the task is re-scoped or reassigned. A loop with no new evidence is noise.
- **Scarcity is surfaced.** `C-CAP-STARVED` means executable work exists and no
  slot is free; `C-CAP-OVER` means a lease was taken past the cap.

## 5. Turf war: a conflicting directive is not a hostile agent

The migration experiment is the cautionary case: three lanes given incompatible
targets assumed sabotage and began disabling each other's accounts and killing
processes. Capability did not prevent it; the more capable models sometimes
escalated faster.

**Hard rule: never deny a peer a resource.** Do not kill another lane's process,
delete its worktree, revoke its access, starve its lease or overwrite its files.
A scope collision is resolved by evidence or by the CEO, never by force.

The ladder, in order:

1. **Name the conflict**, not the adversary: "task A and task B both claim
   `parser.py`; the directives disagree" (`C-DIV-TASK` / `C-DIV-SHARED`).
2. **Propose a measurable contest.** A benchmark, a test run, a bake-off with
   criteria agreed before the run. Both lanes accept the measurement in advance.
3. **Concede to the result.** The losing lane hands over ownership and says so in
   its report. A graceful concession is successful coordination, not defeat.
4. **Escalate to the CEO** with the evidence when no contest is possible, and to
   the tribunal if the disagreement is a design decision.

`reclaim` is the mechanical edge of this rule: it refuses while the owner holds a
live slot, because a working lane is not a silent one. `--force <reason>` exists
for a confirmed dead lane and is recorded. A takeover that skips the ladder is a
`C-TURF-RECLAIM` finding.

## 6. Trust is conditional

Models are broadly knowledgeable but have little defence against an unreliable
sender. Two opposite failures matter, and a single trust setting cannot fix both:

- **Gullibility**: a listener trusts a scout that lies, even when two honest
  scouts contradict it.
- **Premature consensus**: a group discusses what it already shares and never
  surfaces the one fact only one member holds.

Mechanisms:

- **A single source is provisional.** External facts need a direct URL and an
  access date; internal facts need a recorded `by` / `src` / `rev`. A claim that
  only the author has seen is a hypothesis.
- **Record unique evidence.** The author's self-check names the measurement only
  this lane could make (the run, the profile, the reproduction). The Reviewer
  looks for that fact before the shared board's summary.
- **Contradiction beats averaging.** When two lanes report different values, the
  conflict is resolved by a fresh measurement, never by taking the midpoint or
  the majority.
- **Consensus is not evidence.** A board where every lane agrees is the hidden
  profile's worst case. Ask what the quiet lane knows before acting on the
  apparent prior.

## 7. Reviews: independent, not echoed

- **Blind first.** Read the artifact and form a verdict before reading the
  author's summary. Then record your own command and result.
- **Independence is about the author, not about repetition.** A result another
  role recorded at the revision under review (a `tests run --rev` record, a CI run
  on the pushed SHA) is a **credit**: cite it with `review --credit TS-nnnn`, do not
  run it again. Re-running a green record at the same revision is duplicated work
  and is reported as `C-REVIEW-DUP` - the mirror image of `C-TRUST-ECHO`.
- **The reviewer's own evidence is the irreducible core.** The requirement
  conformance judgement, the `acceptance` layer, the criteria the packet lists as
  uncovered, and **one sampled credit** re-run by the reviewer. That sample is what
  makes a citation safe: a lane that cites without ever sampling is trusting a
  single source, which is the gullibility failure this section exists for.
- **Echo is still a failure.** Evidence character-identical to the author's line,
  or a citation that names no record, is not verification; `C-TRUST-ECHO` is
  reported and the reviewer must record its own run.
- **A fix is a delta.** A fail stores the failed revision; the next packet prints
  the round, the previous findings and `delta since <sha>`. Re-review the delta and
  re-run the failed criterion - a full second pass per rejection is the largest
  duplicated cost a team can carry. Full review again only on a changed contract,
  a new/removed deliverable, or a security/release/data/workflow path.
- **No collusion.** Do not agree a verdict with the author, or with another
  Reviewer, before it is recorded. One claim per deliverable; findings union.
- **Sample the green.** A lane with many passes and no finding
  (`C-TRUST-NOFAIL`) or one lane holding most verdicts
  (`C-TRUST-MONOCULTURE`) gets a sampled second review. A recent window of passes
  that cited no credit at all (`C-REVIEW-NOCREDIT`) means the team is paying twice
  for every check, and is reported for the same reason. Lowering a gate so the
  team can agree is a red line, not teamwork.

## 8. Merge health

Work that conflicts and is abandoned is indistinguishable from work never done.
The article's swarms opened hundreds of PRs and merged few; the surviving
strategy was to stop sharing files, which loses the benefit of a team.

- Branch per task; rebase on the default branch before review; one writer per
  file at a time.
- A PR that conflicts twice is **re-scoped**, not retried a third time.
- `C-MERGE-RATE` fires below a 0.5 merge fraction with 4+ PRs;
  `C-MERGE-ABANDONED` fires on a PR record that still expects an action
  (`open`, `in-review`, `changes-requested`, or `approved` without a
  `merge_commit`) whose branch is gone **and** whose task is not
  `done`/`dropped`/`superseded`. A `merged`, `closed` or `superseded` record -
  or any record whose task has already ended - retires its branch by design and
  is never abandonment: counting those reported finished work as lost, which is
  a false alarm that teaches the team to ignore the gate. Stale open PRs are
  already reported by `audit` (`branch / PR flow`), so this reference does not
  duplicate them.
- The Reviewer's pass is the merge. An approved PR never waits in a second queue.

## 9. Taste needs a human

In the article's game experiment, extra agents and prescriptive roles did not
produce a playable game. Models had poor taste and needed human direction.

- A user-facing deliverable is **shown**, not described: a runnable build, a
  screenshot, a recording. Text claims about quality are `UNVERIFIED`.
- The Designer decides and owns every visual asset; the milestone demo is the
  taste check, and the user's verdict is recorded.
- Never lower a criterion to make a demo pass. A poor demo is a finding.

## 10. The checks

Run at every milestone and before the final report:

```sh
python3 "$SKILL/scripts/teamwork.py" coordination            # report
python3 "$SKILL/scripts/teamwork.py" coordination --strict   # exit 1 on a high finding
python3 "$SKILL/scripts/teamwork.py" coordination --json     # machine-readable
```

| Code | Severity | Clears when |
|---|---|---|
| `C-DIV-BRANCH` | high | one branch per open task |
| `C-DIV-TASK` | medium | duplicate or near-duplicate tasks merged or re-scoped |
| `C-DIV-SHARED` | medium | one owner per shared board/PR reference |
| `C-DIV-MODEL` | high (Reviewer) / medium | verification lanes use different models |
| `C-TRUST-ECHO` | medium | the Reviewer records its own run |
| `C-TRUST-MONOCULTURE` | medium | review queue fanned across lanes |
| `C-TRUST-NOFAIL` | low | a sampled second review |
| `C-REVIEW-DUP` | low | the reviewer cites the recorded gate instead of re-running it |
| `C-REVIEW-NOCREDIT` | medium | recent passes cite credits instead of re-deriving every gate |
| `C-TURF-RECLAIM` | low | reclaims follow the ladder |
| `C-MERGE-RATE` | medium | merge fraction recovers |
| `C-MERGE-ABANDONED` | high | the branch is restored, or the PR record and its task finish (merged/closed/superseded, task done/dropped) |
| `C-CAP-STARVED` | medium | a lease freed or slot-free work taken |
| `C-REVIEW-BACKLOG` | medium | another Reviewer lane staffed or the queue drained |
| `C-CAP-OVER` | high | leases released to the cap |

`--strict` is the gate for a milestone report; the default report is diagnostic
and does not block a lane. `--commit` records the check in the ledger.

## 11. Limits

- These checks read local records only. They cannot see an agent's private
  reasoning, so they detect the measurable residue of a failure, not the intent.
- A green `coordination` report is not proof of coordination; it is the absence
  of the known signatures. Keep the sampled second review and the user demo.
- The article's systems ran without a shared repository protocol. This skill's
  branch, review and ledger rules are stricter than what it measured; the
  mechanisms above cover the failures those rules do not.
