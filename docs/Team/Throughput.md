# THROUGHPUT - measured bottlenecks and the token economy

Owner: CEO. This is the optimization record: what the team's own history says is
slow, what it costs in context, and the change each number justifies. Re-read a
row with its command; do not trust a count in this file.

Related: [Project](Project.md) | [Plan](Plan.md) | [Evolution](Evolution.md) | [Memory](Memory.md)

## 1. Objective

The operator asked to optimize the roles, organization, structure, hierarchy,
order and tasks so the team has no bottleneck, and to optimize token consumption
against the team's own history and track records. This file is the measured
answer: a baseline from the ledger and tree, the bottleneck ranking, the change
made for each, and the command that re-reads it.

Non-goals: a new org layer, a hosted dashboard, a second store, deleting history,
or a gate weakened to make a number look better.

**State at this cut (2026-11-04):** AC-M18-1 and AC-M18-3 verified; AC-M18-2 is
**open** - the roster cut lost 102 artifact paths (`L-0001`) and the M17 docs
pushed Developer/Reviewer startup over the cap. The report is a baseline and a
change list, not a completion claim; `loop` is CONTINUE.

## 2. Baseline (ledger n=1859, measured 2026-11-04)

Snapshot, not a pinned census. The command column re-reads it.

| Fact | Measured | Command |
|---|---|---|
| review claim -> verdict | p50 5.8 min, p90 22.1 min, max 54.2 min (n=104) | `teamwork.py throughput` |
| review verdicts | 63 pass, 43 fail (41% of verdicts fail) | `teamwork throughput` |
| targets needing more than one verdict | 31 of 65 (47.7%) | `teamwork throughput` |
| worst rework | architect T-0002: 4 verdicts (3 fail, 1 pass) | `trace architect:T-0002` |
| task intake | 85 `task.add`, 50 merged, 5 reclaim, 3 disputes | `ledger show` action counts |
| open work | 7 todo, 2 doing, 1 review across the role queues | `teamwork board` |
| instances | 34 agent directories for the open work at intake (17 developer, 9 reviewer, 3 tester, 2 writer); cut to 12 active at this milestone | `teamwork instance list` |
| always-on per instance | 112,730-134,160 B; Developer-1/8 129,207 and Reviewer-6..9 134,160 are OVER the 122,880 cap after the M17 docs landed | `teamwork harness budget` |
| review evidence field | p50 82 B, p90 607 B, max 1,681 B | the review packet clips at 600 chars |
| `docs/Team/Archive.md` | 2,541,748 B, ~635k tokens | `wc -c docs/Team/Archive.md` |
| `docs/Team/Decisions.md` | 330,814 B, ~83k tokens | `wc -c docs/Team/Decisions.md` |
| `docs/Team/Plan.md` | 84,369 B, ~21k tokens | `wc -c docs/Team/Plan.md` |
| all `docs/Team/*.md` | 3,446,516 B, ~862k tokens | the same `wc`, summed |
| one startup read | AGENTS 34,764 B + SKILL 61,492 B + own charter + short memory; the total across 15 charters is 256,163 B (~64k tokens) | `teamwork harness list` / `harness budget` |

## 3. Bottlenecks, ranked by what the numbers say

1. **Review rework, not review capacity.** 41% of verdicts fail and 47.7% of
   targets need a second verdict; the p90 wait is 22.1 min with nine reviewer
   lanes at intake (four now) for two unclaimed items. The queue is not starved -
   the first pass is
   not review-ready. Of the 29 fails that carry the `review_mechanical` field,
   25 are `no` (a green preflight existed at that revision): the failures are
   substantive - a missing existing flag, an undefined second-call transition, a
   concurrency race - not lint the preflight could catch. More reviewer lanes do
   not fix this; a better author self-review does.
2. **The roster is over-supplied for the work.** 34 instance directories for ten
   open tasks, 17 developer and 9 reviewer instances. Every spawned idle lane
   still costs a startup read and a coordination surface; the org chart should
   scale on demand, not be pre-staffed at the maximum ever used. The cut was
   executed **and it went wrong**: the shared checkout was detached at `ac481aacbdacd7819bcedbdf1fc679730d7f2e98`
   (before the move-only retirement merged in `8a578b112d68c9488d3ad001f180f23163d2bb21`), so the 22 retirements
   ran the inherited `rmtree` and deleted their `Artifacts/`, `Reports/` and
   `WorkLog.md`. 102 evidence paths named by `Tests.md` are gone; the loss is
   recorded as lesson `L-0001` and cannot be undone. The move-only code is now
   merged and tested (`Runtime/Retired/<instance>/`), and no further cut runs
   until the checkout is verified at or after that revision. This is the clearest
   proof in this report that **the base checkout's revision is part of the
   safety surface**, not an operational detail.
3. **On-demand reads are the real token cost.** One whole `Archive.md` read is
   ~635k tokens - five times the entire always-on prompt - and `Decisions.md`
   adds ~83k, `Plan.md` ~21k, all `docs/Team` ~862k. The largest task queue is
   ~64k tokens. A single "read the archive for close-out" costs more than a
   complete instance startup.
4. **Always-on accounting is right, and it now shows a real overage.** T-0034
   splits startup from recallable: Developer-1/8 **129,207 B** and Reviewer-6..9
   **134,160 B** are OVER the 122,880 cap; the overage is the M17 docs in
   `AGENTS.md`/`SKILL.md` plus the reviewer's 24-entry short memory. The budget
   now makes the overage visible instead of hiding it behind recall-only bytes.
   The fix is to trim what `load` prints or the always-on prose, not to raise
   the cap; the roster cut alone does not reduce a shared-memory read.
5. **Review queue latency is second-order - but duplicate full-suite runs are
   not.** p90 is 22.1 min, max 54.2 min, with 13 renewals and 10 releases: some
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
| 9 | Every lane works in a worktree, including the CEO | the base checkout stays on `main`, so the merge path, the host skill scan and every lane see the integrated tree; no lane checks out its branch in the shared tree | checkout switches, stale skill scans, merge-target confusion | CEO, all lanes |

## 5. The token budget

| Surface | When it is paid | Budget rule |
|---|---|---|
| AGENTS block + `SKILL.md` + own charter + short memory + open lessons + top-10 knowledge | every startup (`load`) | <= `AlwaysOnBudgetKb` (120 kB); the `harness budget` `startup` row is the one the cap applies to |
| Long-term memory, memory archive | on `recall`/search only | not startup; report as `recallable` |
| `references/*.md` | only when a task needs that reference | read the one file, not the directory |
| `Archive.md`, `Decisions.md`, `Plan.md`, `TaskQueue.md` | only by id/filter | never whole; the archive is ~635k tokens and the largest queue ~64k |
| review packet | one screen per deliverable | evidence clipped at 600 chars; cite a recorded run instead of re-running it |

**The rule that follows from the numbers:** the always-on prompt is ~113-134 kB
while a single whole-archive read is ~635k tokens. Read by id, and the token
cost of a whole wave is bounded by the startup, not by the history.

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
<= 35%, measured by the same ledger parse. At 41%/47.7% both are the gap; a
later report re-reads them rather than asserting them.

## 7. Roster right-sizing

Policy: the default tier is `slim` (CEO, Architect, Developer, Tester, Reviewer-1,
Reviewer-2). A role joins only for a named deliverable, test layer or decision
right; an instance is added only when the ready queue for its role exceeds the
lanes, and retired when the queue is empty. **Retirement is move-only:** the
instance directory is moved to `Runtime/Retired/<instance>/` so its artifacts,
reports and worklog survive as evidence. The first live cut (22 lanes) ran from a
detached pre-fix checkout and lost its artifacts; lesson `L-0001` is the record.
The move-only code is merged at `8a578b112d68c9488d3ad001f180f23163d2bb21`; the live tree now holds 12 instances,
and every future cut verifies `git rev-parse HEAD` is at or after that revision
and that `Runtime/Retired` is created before it retires one. `teamwork instance
list` is the source of truth, and `teamwork parallel` says how many lanes the
ready work supports.

## 8. How to re-measure

```sh
teamwork.py board                  # open work per role
teamwork.py parallel               # free slots vs ready work
teamwork.py instance list          # roster size
teamwork.py harness budget         # startup vs recallable bytes
teamwork.py coordination --strict  # review oversupply, rework, merge health
teamwork.py throughput             # ledger latencies, rework share, surface bytes
```

The last command is the report's own reader: it prints the review, queue and
surface facts in section 2 (latency, verdicts, rework, queue depth, instances,
surface bytes). The remaining rows are read with the named command in their row;
nothing in this file is a substitute for running it.

## 9. Falsifiers

- If the fail share does not fall after the first-pass contract ships, the
  contract is ceremony and must be replaced, not restated.
- If a lane is dry while a ready task of its role waits, the bottleneck is the
  assignment path, not the work.
- If `harness budget` startup bytes exceed the cap after the accounting fix, the
  cap or the prompt must shrink; do not move the cap to make it pass.
- If a whole-archive read still appears in a close-out or review, rule 2 was not
  adopted and the report is wrong about the token win.
- If a retirement runs from a checkout older than the move-only fix, or creates
  no `Runtime/Retired/<instance>/`, stop the cut: the artifacts are the evidence,
  and this report already owns one loss (`L-0001`) it will not repeat.
