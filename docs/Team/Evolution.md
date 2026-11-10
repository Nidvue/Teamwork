# EVOLUTION - how this team learns, and how learning is promoted

Owner: CEO.

Related: [Project](Project.md) · [Plan](Plan.md) · [Throughput](Throughput.md) · [Risks](Risks.md) · [Archive](Archive.md)

This page is the operating record of the team's self-evolution. It is not a
second store: every row names the tool that re-reads it, and every number is
bound to a cut. A claim without a command and a cut is prose, not evidence.

The one rule that matters: **a failure is classified before it is recorded**. A
tool defect recorded as a lesson comes back as the same defect: the archive
render was handled as a lesson, and the renderer gap returned on the next
branchless merge (`L-0001`).

## 1. Purpose and non-goals

- Purpose: make the team's own mistakes change future behaviour, with evidence,
  without weakening a gate.
- In scope: findings, records, promotion of rules, metrics, cadence, rollback.
- Non-goals: a second ledger, a dashboard, a new org layer, deleting history, or
  raising a gate to make a number look better.

## 2. The four books

| book | lives in | owner | close check |
|---|---|---|---|
| Metrics | §5 here + [Throughput](Throughput.md) | COO | every row has `cut` + command |
| Evolution | §9 `EV-` rows | COO | every change has a verdict label |
| Known issues | §9 `KI-` rows + [Risks](Risks.md) | COO | no row past `re_measure_by` |
| Promotion | §9 `PB-` rows | CTO | every `L1` item has a level and a blocker |

A row is written through the engine where one exists (`lesson`, `knowledge`,
`decision`, `skill`); a hand edit of a record store is a defect, not a shortcut.

## 3. Five classes

Classify first, then act. The class decides the destination, and a class never
changes later to make the fix cheaper.

| class | test | destination | this project's evidence |
|---|---|---|---|
| **T** tool defect | reproducible from an input, independent of judgement | code task + a regression that fails on the old revision | archive render of branchless deliverables drops entries (`L-0001`); `--credit` impossible on a branchless review (`K-0002`) |
| **P** process defect | order, contract or human flow | checklist / `tw-*` skill / preflight | 25 of 29 classified review fails were `mechanical=no` - substantive, so the first-pass contract, not lint |
| **D** doc drift | a statement disagreed with the tree or a command | doc fix + `measured_at` | the repo's own `Archive.md` carries 36 fail verdicts against 29 passes at this cut (`grep -c 'FAIL @'`, `grep -c 'PASS @'`; two passes are spelled `VERDICT PASS @`) |
| **G** governance | a trade-off with alternatives | `D-` record with evidence and falsifier | `D-20261104-CEO`: a runner-capacity failure is re-run, never a weakened matrix |
| **K** knowledge | a durable fact, command or gotcha | `K-` record, superseded not overwritten | `K-0001` gate parity; `K-0003` macOS cache artifact |

**The rule**: a T-class finding has no lesson. It gets a failing reproduction, a
fix, and a test that would have caught it.

## 4. Lifecycles

```text
Finding : observed -> classified -> recorded -> assigned -> fixed/verified -> promoted -> retired
Known   : open -> re-measured -> {closed | waived(reason) | escalated}
Change  : proposed -> baseline -> single-variable experiment -> verdict -> promoted | reverted
Skill   : draft -> shared -> stable -> deprecated (a replacement is named)
Record  : active -> superseded -> archived (cold)
```

- A finding older than one milestone with no owner is escalated, not forgotten.
- `waived` needs a written reason; silence is not a waiver.
- A change whose verdict is `confounded` keeps its row and is re-measured, never
  relabelled `helped`.

## 5. Metrics

Cut #1 is the M18 baseline in [Throughput](Throughput.md) at ledger `n=1859`.
Cut #2 is the 2026-11-04 engagement. **Never compare across cuts without saying
so.**

| metric | formula | cut #1 | cut #2 | target | command |
|---|---|---|---|---|---|
| RFR, review fail share | fail verdicts / verdicts | 43/106 = 41% | 0/7 | <= 30% | `teamwork throughput` |
| Rework | targets with >1 verdict / targets | 31/65 = 47.7% | 0/7 | falling | `teamwork throughput` |
| SFR / MFR | substantive / mechanical fail share | 25 of 29 fails substantive | none classified | SFR falling, MFR absorbed by preflight | `teamwork throughput` + the `mechanical` field |
| TTV p50 / p90 | claim -> verdict | 5.8 / 22.1 min | 2.3 / 69.2 min (n=7) | p90 falling | `teamwork throughput` |
| Verification waste | repeated full-suite runs at one revision | structural (author, Tester, Reviewer) | 0 credited duplicates | 0 | review evidence + `coordination` |
| Record density | `Archive.md` total bytes (committed, so reproducible) | 2.5 MB | 2.7 MB | bounded, segmented above 512 KiB | `wc -c docs/Team/Archive.md` |
| Freshness debt | `KI-` rows past `re_measure_by` | not tracked before this page | see §9 | 0 | §9 |
| Promotion lag | days from a repeated `L-` to a `tw-` skill | 3 skills, then stalled | see §9 | <= 7 days | `teamwork skill candidates` |
| Guardrails | required layers, security, budget, independence, chain | all green except budget | budget red (KI-0001) | any regression is `hurt` | `tests plan`, `code-scanning`, `harness budget`, `coordination`, `ledger verify` |

## 6. Cadence and RACI

| trigger | budget | action | stop condition | owner |
|---|---|---|---|---|
| any self-check or review failure | 5 min | classify, record, assign; a T-class opens a code task with a repro | a task or an existing skill is named | author |
| the same finding a second time | 15 min | promote `L1 -> L2`, or open the T/P task | the skill or task exists | role owner |
| every milestone close | 30 min | snapshot §5, age §9, decide promotions and rollbacks | one row per book updated | COO |
| every release | 60 min | promote `L2 -> L3`, `refresh --check`, changelog | new version green | CTO |
| two projects reproduce a rule | half a day | generalize into `SKILL.md` / `references/` | a decision is recorded | CEO |

| activity | CEO | CTO | COO | Reviewer | Security |
|---|---|---|---|---|---|
| classify and record | A | R | R | C | C |
| metrics snapshot | A | R | R | I | I |
| promote L1 -> L2 | I | A | R | C | - |
| promote L2 -> L3 | A | R | C | R (independent) | C |
| roll back | A | R | R | I | I |
| freshness audit | A | C | R | C | R (sample) |

## 7. Promotion and rollback

| level | where | promotion needs |
|---|---|---|
| L1 role lesson / knowledge | `.pi/.../Roles/<Role>/Lessons.md`, `Knowledge.md` | one recorded failure with evidence |
| L2 team skill | `.agents/skills/tw-*/SKILL.md` (committed) | >= 2 occurrences, a trigger, a budget, a stop condition, a proof command |
| L3 skill core | `SKILL.md`, `references/`, `roles/` | reproduced in >= 2 milestones or projects, no guardrail regression, independent review, a release |
| L4 adapter | host / CI / forge config | environment only; the semantics never change here |

**Evidence pack** for a promotion: the trigger occurrences, a single-variable
diff, a two-cut comparison, the guardrail check, the rollback command, and an
independent reviewer.

**Canary**: an L2 -> L3 change runs one milestone in one project before it is
stated as the rule.

**Rollback triggers**: the primary metric does not move, a guardrail regresses, a
new high-severity defect appears, or two cuts pass with no re-measurement.

## 8. Structural guards

| guard | source | check |
|---|---|---|
| a destructive action asserts the base revision | `L-0001` roster cut lost 102 artifact paths | the command refuses below the move-only revision |
| one writer per worktree, absolute artifact paths | R-20/R-21/R-22 | branch and path checks |
| no pinned census in prose | repeated review findings | doc-contract tests + `measured_at` |
| a failed review cap is tool-enforced | round 8 still exists in the archive | the third fail must open a dispute |
| a T-class defect has a failing-before test | the archive render recurred | `tests repro` on the fixing task |
| know the existing issue before filing a new one | the always-on overage was re-found in 2026-11 | `audit` maps to §9 |

A rule with no command that enforces it is a wish and cannot be a close
condition. This is the same test the harness lint applies to a skill.

## 9. Current ledgers

### 9.1 Known issues

| id | issue | class | owner | first seen | re-measure by | status |
|---|---|---|---|---|---|---|
| KI-0001 | always-on startup over the 122,880 B cap: Reviewer 134,501 B, CEO 125,879 B at the fixing head; memory, lessons and knowledge are under 4 KB of it, the rest is `SKILL.md` 66,048 + the AGENTS.md managed block 41,132 + the reviewer charter 24,100 | D/G | ceo T-0003 | M18 (`Throughput` 2) | next milestone | open |
| KI-0002 | the traceability proof re-runs `privacy_scan.py --tree --history`, which now exceeds `PROOF_TIMEOUT_SECONDS=900` on a cold runner; run 41916744357 red on 3 lanes | T | developer T-0002 | 2026-11-04 | next full matrix | in flight |
| KI-0003 | `lesson add` waited 60 s for `lessons.lock` under 4 concurrent processes on Windows | T | developer T-0002 | 2026-11-04 | next full matrix | in flight |
| KI-0004 | a branchless deliverable's archive entry is rendered but not committed by the merge path; a reviewer restored two missing entries by hand (`b2d4fc3`) and the early return is still there | T | developer T-0006 | 2026-11-04 | next review | filed |
| KI-0005 | `AuditReport.md` F-P2/F-P3 have not been re-measured since 2026-10-25 | D | ceo | 2026-10-25 | next audit | open |
| KI-0006 | record growth: `Archive.md` 2.7 MB, largest task queue 23.8 KB at cut #2 (the 2026-11-02 peak was 511 KB, R-32); the 512 KiB segment trigger was never crossed | G | architect | 2026-11-02 | at the 512 KiB segment trigger | open |

### 9.2 Evolution ledger

| id | change | class | baseline -> result | verdict | evidence |
|---|---|---|---|---|---|
| EV-0001 | record the three red CI runs and their classes in [Release](Release.md) | D | run 41854143232: 18/19 -> re-run 19/19 | no observed effect (a record, not a change) | `gh run view 41854143232` |
| EV-0002 | boundary-aware host matcher in `test_skill_contracts.py` | T | the old test passed under a spoofed host; the new one fails | helped (defect fixed, mutation killed; not a throughput claim) | `gh api .../code-scanning/alerts/4` -> fixed; Reviewer-2 mutation table |
| EV-0003 | close 15 topic branches (13 merged, 2 superseded) | G | 15 remote refs -> `main` only | no observed effect (housekeeping) | `git ls-remote --heads origin` |
| EV-0004 | this page and the `tw-self-evolve` skill | P | no baseline yet | confounded (classification, books, metrics and cadence changed together) | falsifier: two milestones with RFR, promotion lag and freshness debt unmoved |

### 9.3 Promotion backlog

| record | level now | blocker | next step |
|---|---|---|---|
| `L-0001` archive render | L1 (lesson) | it is a T-class defect, not a process rule | developer T-0006; then retire the lesson |
| `K-0001` gate parity | L1 (knowledge) | one project, one occurrence pair | a `tw-` mistake skill if it recurs |
| `K-0002` branchless credit | L1 (knowledge) | the fix is a tool limitation | fold into the Reviewer's branchless rule, then retire |
| the first-pass contract (`Throughput` 6) | L2 (a section, not yet a skill) | unmeasured after the change | measure SFR at the next cut |

## 10. Adoption tiers

| tier | for | books required | cadence |
|---|---|---|---|
| Lite | a single-agent project | metrics + lessons | per task |
| Standard | this project | all four | per task + per milestone |
| Full | several projects | all four + cross-project comparison | + per release |

## 11. Verification

```sh
teamwork evolution snapshot --json && teamwork evolution check
teamwork throughput && teamwork coordination --strict && teamwork audit
teamwork harness budget && teamwork tests plan && teamwork links
teamwork skill candidates && teamwork ledger verify
```

A close-out checks: `teamwork evolution check` exits 0 - no `KI-` row past its
date, every `EV-` row has a verdict, every `PB-` row has a level, every metric
row names its command, and no required table is missing or empty - the snapshot
names a new cut, and the ledger chain is intact. The check is the gate; the other
rows are the readers it aggregates.

## 12. Sources

- [Throughput](Throughput.md) - the M18 baseline (cut #1) and the review contract.
- [Archive](Archive.md) - 36 fail verdicts against 29 passes at this cut.
- [Risks](Risks.md) - R-20, R-21, R-22, R-25, R-30, R-31, R-32.
- `docs/Team/Decisions.md` - `D-20261104-CEO` and the runner-capacity ruling (read by id with `teamwork decision list`).
- [Plan](Plan.md) - M18 and the throughput contract.
