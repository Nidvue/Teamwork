# THROUGHPUT - measured bottlenecks and the token economy

Owner: CEO. This is the optimization record: what the team's own history says is
slow, what it costs in context, and the change each number justifies. Re-read a
row with its command; do not trust a count in this file.

Related: [Project](Project.md) | [Plan](Plan.md)

## 1. Objective

The operator asked to optimize the roles, organization, structure, hierarchy,
order and tasks so the team has no bottleneck, and to optimize token consumption
against the team's own history and track records. This file is the measured
answer: a baseline from the ledger and tree, the bottleneck ranking, the change
made for each, and the command that re-reads it.

Non-goals: a new org layer, a hosted dashboard, a second store, deleting history,
or a gate weakened to make a number look better.

## 2. Baseline (ledger n=1626, measured 2026-11-03)

Snapshot, not a pinned census. The command column re-reads it.

| Fact | Measured | Command |
|---|---|---|
| review claim -> verdict | p50 5.2 min, p90 24.5 min, max 69 min (n=95) | parse `Ledger.jsonl` `review.claim` -> `review.pass\|fail` |
| review verdicts | 56 pass, 39 fail (41% of verdicts fail) | `ledger show --tail` / the same parse |
| targets needing more than one verdict | 27 of 58 (46.6%) | group verdicts by role+task |
| worst rework | architect T-0002: 4 verdicts (3 fail, 1 pass) | `trace architect:T-0002` |
| task intake | 85 `task.add`, 50 merged, 5 reclaim, 3 disputes | `ledger show` action counts |
| open work | 7 todo, 2 doing, 1 review across the role queues | `teamwork board` |
| instances | 34 agent directories for the open work: 17 developer, 9 reviewer, 3 tester, 2 writer | `teamwork instance list` |
| always-on per instance | 107-123 kB; the developer lane read OVER by 278 B against the 120 kB cap | `teamwork harness budget` |
| review evidence field | p50 82 B, p90 607 B, max 1,681 B | the review packet clips at 600 chars |
| `docs/Team/Archive.md` | 2,463,413 B, ~616k tokens | `wc -c docs/Team/Archive.md` |
| `docs/Team/Decisions.md` | 323,086 B, ~81k tokens | `wc -c docs/Team/Decisions.md` |
| `docs/Team/Plan.md` | 87,221 B, ~22k tokens | `wc -c docs/Team/Plan.md` |
| all `docs/Team/*.md` | 3,344,696 B, ~836k tokens | the same `wc`, summed |
| one startup read | AGENTS 34,764 B + SKILL 61,492 B + own charter + short memory; the total across 15 charters is 256,163 B (~64k tokens) | `teamwork harness list` / `harness budget` |

## 3. Bottlenecks, ranked by what the numbers say

1. **Review rework, not review capacity.** 41% of verdicts fail and 46.6% of
   targets need a second verdict; the p90 wait is 24.5 min with nine reviewer
   lanes for two unclaimed items. The queue is not starved - the first pass is
   not review-ready. Of the 29 fails that carry the `review_mechanical` field,
   25 are `no` (a green preflight existed at that revision): the failures are
   substantive - a missing existing flag, an undefined second-call transition, a
   concurrency race - not lint the preflight could catch. More reviewer lanes do
   not fix this; a better author self-review does.
2. **The roster is over-supplied for the work.** 34 instance directories for ten
   open tasks, 17 developer and 9 reviewer instances. Every spawned idle lane
   still costs a startup read and a coordination surface; the org chart should
   scale on demand, not be pre-staffed at the maximum ever used. **The cut is
   blocked on a defect:** `instance retire` removes the instance directory with
   `shutil.rmtree`, so retiring an idle lane would delete its `Artifacts/`,
   `Reports/` and `WorkLog.md` - evidence the ledger and Archive may still cite.
   The fix is part of T-0034: retirement moves the directory to
   `Runtime/Retired/<instance>/` and records the path; only then is the live cut
   safe.
3. **On-demand reads are the real token cost.** One whole `Archive.md` read is
   ~616k tokens - five times the entire always-on prompt - and `Decisions.md`
   adds ~81k, `Plan.md` ~22k, all `docs/Team` ~836k. The largest task queue is
   ~57k tokens. A single "read the archive for close-out" costs more than a
   complete instance startup.
4. **Always-on accounting is wrong in one direction.** The budget counts
   `LongTermMemory.md`, which `load` never prints (it is recall-only) and does
   not count the lessons/knowledge that `load` now does print. The developer
   lane is reported OVER while its actual startup read is under the cap.
5. **Review queue latency is second-order - but duplicate full-suite runs are
   not.** p90 is 24.5 min, max 69 min, with 13 renewals and 10 releases: some
   reviews are too large for one lease. That is a slice-size problem (change 4).
   The hidden latency is the ~30-minute full suite: the author, the Tester and
   the Reviewer can each run it on one revision. The Tester's independent record
   is creditable under the verify-once rule, so a Reviewer that re-runs it spends
   30 minutes proving a fact another role already recorded. Current dispatch
   starts the Reviewer before the Tester on a code task, so the duplication is
   structural, not accidental.

## 4. Changes, each owned and measurable

| # | Change | Mechanism | Metric it moves | Owner/task |
|---|---|---|---|---|
| 1 | Right-size the roster | safe retirement first (move to `Runtime/Retired/<instance>/`, never delete artifacts), then retire idle lanes; default `slim`; `instance add` only for a named deliverable | instances vs open tasks; startup reads per wave | CEO T-0020 + Developer T-0034 |
| 2 | Read by id, never whole | `archive --task <T-id>`, `decision list --kind`, `trace <id>`, `board`; never `cat` the archive, decisions, plan or a task queue | tokens per close-out/review; bytes read | Developer T-0034, docs T-0013 |
| 3 | Review first pass | author self-review names the three likely failure modes (boundary, second call, concurrency, contract completeness, scope) with a test or a reason; the Reviewer judges the requirement, not the lint | fail share, targets >1 verdict | docs T-0013, Reviewer rubric |
| 4 | Right-sized slices | `preflight` warns when a diff exceeds the profile's slice (12 files / 600 changed lines for standard, 24 / 1,200 deep) | review lease overruns, p90 | Developer T-0034 |
| 5 | Token-true budget | `harness budget` reports `startup` (what `load` prints) separately from `recallable` (long/archive) and applies the cap to startup | OVER false alarms; startup bytes | Developer T-0034 |
| 6 | Reviewer oversupply | `coordination` reports `C-REVIEW-OVERSUPPLY` when reviewer lanes exceed twice the unclaimed queue and the queue is small | idle reviewer lanes | Developer T-0034 |
| 7 | One owner, one board, one feature | already frozen; re-stated at intake so a second manager or a second feature per leader is refused | queue conflicts, duplicate tasks | CEO, Architect |
| 8 | Tester before Reviewer on a code task | the Tester records the full suite at the revision; the Reviewer packet cites it (`--credit`) and runs only its acceptance layer, the uncovered criteria and one sampled credit; no gate weakens | full-suite runs per revision; claim-to-verdict p90 | CEO dispatch order, Reviewer rubric |

## 5. The token budget

| Surface | When it is paid | Budget rule |
|---|---|---|
| AGENTS block + `SKILL.md` + own charter + short memory + open lessons + top-10 knowledge | every startup (`load`) | <= `AlwaysOnBudgetKb` (120 kB); the `harness budget` `startup` row is the one the cap applies to |
| Long-term memory, memory archive | on `recall`/search only | not startup; report as `recallable` |
| `references/*.md` | only when a task needs that reference | read the one file, not the directory |
| `Archive.md`, `Decisions.md`, `Plan.md`, `TaskQueue.md` | only by id/filter | never whole; the archive is ~616k tokens and the largest queue ~57k |
| review packet | one screen per deliverable | evidence clipped at 600 chars; cite a recorded run instead of re-running it |

**The rule that follows from the numbers:** the always-on prompt is ~115 kB; a
single whole-archive read is ~616k tokens. Read by id, and the token cost of a
whole wave is bounded by the startup, not by the history.

## 6. Review first-pass contract

The author, before `selfcheck`, answers in the self-check note:
- the boundary and the empty/duplicate/second-call case, and where it is tested;
- the contract surface: every existing flag, field and transition still defined;
- concurrency and shared-file writes, if the change has any;
- the scope: the exact files changed and why nothing else moved;
- the failure a hostile reviewer would name, and the evidence that it cannot
  happen.
A self-check that only says "re-read the diff" is not a self-check. The Reviewer
still judges the requirement and the acceptance layer; this contract only stops
the substantive failure the author could have found.

**One full suite per revision.** On a code deliverable the Tester runs the full
suite first and records it; the Reviewer cites that record (`--credit`) and runs
its own acceptance layer, the uncovered criteria and one sampled credit. The
Reviewer re-runs the full suite only when no Tester record exists at the revision
or the record is failing. The dispatch order is Tester -> Reviewer, so the
30-minute suite is paid once, not twice.

Target: fail share <= 30% of verdicts and targets needing more than one verdict
<= 35%, measured by the same ledger parse. At 41%/46.6% the first target is the
gap; a later report re-reads it rather than asserting it.

## 7. Roster right-sizing

Policy: the default tier is `slim` (CEO, Architect, Developer, Tester, Reviewer-1,
Reviewer-2). A role joins only for a named deliverable, test layer or decision
right; an instance is added only when the ready queue for its role exceeds the
lanes, and retired when the queue is empty. **Retirement is move-only:** the
instance directory is moved to `Runtime/Retired/<instance>/` so its artifacts,
reports and worklog survive as evidence; the current `rmtree` behaviour is the
defect T-0034 fixes before any live cut. The live tree is cut to the active
lanes at this milestone once that fix lands; `teamwork instance list` is the
source of truth, and `teamwork parallel` says how many lanes the ready work
supports.

## 8. How to re-measure

```sh
teamwork.py board                  # open work per role
teamwork.py parallel               # free slots vs ready work
teamwork.py instance list          # roster size
teamwork.py harness budget         # startup vs recallable bytes
teamwork.py coordination --strict  # review oversupply, rework, merge health
teamwork.py throughput             # ledger latencies, rework share, surface bytes
```

The last command is the report's own reader: it parses `Ledger.jsonl` and the
tree and prints the facts in section 2. A scratch probe may exist under
`.pi/Scratch/`, but the report is reproducible from the shipped command, not
from a gitignored file.

## 9. Falsifiers

- If the fail share does not fall after the first-pass contract ships, the
  contract is ceremony and must be replaced, not restated.
- If a lane is dry while a ready task of its role waits, the bottleneck is the
  assignment path, not the work.
- If `harness budget` startup bytes exceed the cap after the accounting fix, the
  cap or the prompt must shrink; do not move the cap to make it pass.
- If a whole-archive read still appears in a close-out or review, rule 2 was not
  adopted and the report is wrong about the token win.
