# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## Snapshot (2026-10-21, `main` as `git rev-parse --short main` reports it)

- Milestone: M9 Harness^2 adoption is open. The whole surface is on `main`:
  `harness` (developer T-0001, merge `b33120c`), `hooks` (developer T-0002, merge
  `49cd42e`), the Architect's contract for both (architect T-0001, merge
  `bef4e02`), the ordered review rubric and the untrusted-material rule (ceo
  T-0001, merge `2f44f00`), Research section 8 (product-manager T-0001, merge
  `73be637`), the process-boundary and acceptance suites (tester T-0001, merge
  `47db23d`) and the docs pass for the new surface (ceo T-0002, merge
  `28c1133`). Every one of those merges is an ancestor of `main`
  (`git merge-base --is-ancestor <sha> main` -> rc 0). AC-H1..AC-H8 are verified
  on the merged revision (`teamwork.py criteria list` -> 8/8). M9 stays open on
  the exit condition `pytest -q` clean on `main`, not on a missing surface, and
  it closes when the CEO records that. M8 records hygiene is closed (ceo
  T-0028, merge `62ef5db`).
- Local gate: `pytest -q` on this branch -> 0 failed, some skipped. The suite is
  green: the AC-5 privacy row that used to fail it no longer does, because the
  privacy tree side is closed and the false green claim was corrected
  (ceo T-0005, merge `f91bf1b`). The passing count is read from that run and
  never pinned here, because every commit that adds a test changes it. The
  skips are the gitignored team tree (a worktree carries no `.pi/`) and the
  console-script acceptance test (covered by `verify_release.py`).
- Privacy: **RED in HISTORY, GREEN in TREE.** `python3 scripts/privacy_scan.py
  --tree --allow .github/privacy-allow.txt` -> PASS - 0 finding(s), exit 0: the
  tree family is closed, the archive mask covers every rule the shipped gate
  reports (developer T-0007, merge `ba947c0`), the two archived lines that
  quoted the operator address were rewritten (ceo T-0008, merge `51b8235`) and
  the scanner false positive on a relative path was fixed (developer T-0006,
  merge `0343b28`). `python3 scripts/privacy_scan.py --tree --history --allow
  .github/privacy-allow.txt` -> FAIL, exit 1: the history family is still red on
  the local commits, in commit metadata (the forge squash merge `4de397e`
  carries the operator account as author, and one commit message carries a
  40-hex tree id the entropy rule reports) and in the older
  `docs/Team/Archive.md` blob revisions that quote that address inside archived
  reviewer evidence. The rewrite plan is measured, not asserted: the Security
  Auditor ran the whole remediation in a throwaway clone and the history scan
  went from FAIL to PASS 0 there - a measurement on a throwaway copy, not a
  property of this tree, so re-measure it on the real branch after the rewrite.
  That rewrite needs the **user's** authorization, because AGENTS.md's red-line
  list names "history rewrite" without the published qualifier; it is owned by
  ceo T-0003 and is blocked on that authorization, not on any team work. The
  finding count is read from the run and never pinned: `--history` reaches other
  lanes' unmerged branches, so the count moves while `main` does not.
  [Project](Project.md) row AC-5 says red (G-8) and says so honestly.
- Links: `teamwork.py links` -> 0 problems
- Gate: `teamwork.py loop` -> CONTINUE while any task branch is unmerged, and
  STOP only after the last review lands; `teamwork.py audit` lists one entry per
  open gate and its count moves with each review round, so it is read, not quoted.
  The closing export `docs/Team/AuditManifest.json` names the revision it was
  exported from, so it verifies at that head - but that head is behind the
  current `main`, so the digests it pins for [Plan](Plan.md) and
  [Decisions](Decisions.md) no longer match the live files and a re-export is
  owed before the milestone closes
- Remote: the local `main` is **109 commits ahead** of `origin/main`
  (`git rev-list --left-right --count origin/main...main` -> `8 109`), and the
  published side is **8 commits ahead of the local merge base** - the remote is
  not caught up, and it is not a simple fast-forward either. The published tip
  carries work the local `main` does **not** have: the committer guard
  (`identity --guard-committer` plus its CI job) and the rebase-merge
  explanation in `references/Remotes.md` and `CONTRIBUTING.md`
  (D-20261020-CEO-8). A rewrite of the local history must therefore be based on
  the **published** tip, not on the local merge base, or the rewrite drops the
  guard that stops the red from coming back
  ([D-20261020-CEO-8](Decisions.md)). Only the Release Engineer pushes, and only
  after the Reviewer has passed the revision; CI on the pushed SHA is the
  certification step.

- pi packaging: [Pi-Packaging](Pi-Packaging.md)

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | T-0003 the false AC-5 privacy claim | P0 | blocked on the user's authorization for a history rewrite | [Project](Project.md) AC-5 |
| product-manager | T-0007 refresh the Plan and Board for the merged state of M9 | P1 | in review | this PR |

The task queue (`teamwork.py board`, `teamwork.py task list <role>`) is
authoritative for a task's exact state; this table only says which lanes are open.
The product-manager records lanes that closed on earlier PRs are no longer listed
here: T-0004 (merge `fe0afb9`), T-0005 (merge `80f0cfa`) and T-0006 (merge
`cd516f1`); ceo T-0011 is `done` on the same measurement (D-20261020-CEO-8), and
the only open CEO lane is the blocked T-0003.

## Dependency PRs (landed)

| PR | bump | outcome |
|---|---|---|
| #11 | `anchore/sbom-action` 0.24.0 -> 0.24.3 | closed; landed in `9b56f1b` via #17 |
| #12 | `actions/attest-build-provenance` -> `4d101475` | closed; landed in `9b56f1b` via #17 |
| #13 | `softprops/action-gh-release` -> `efb35369` | closed; landed in `9b56f1b` via #17 |

The three branches were rebased onto `6905869` (the earlier red Windows jobs came
from the retired umask assertion, fixed in `f2e3b5a`), each passed 17/17 checks,
and they were landed as one reviewed commit. All refs keep the SHA-pinned style
(`uses: owner/action@<sha> # vN`). Missing `ci` and `dependencies` labels were
created so Dependabot can label future PRs.

## Closed history

| milestone | result | evidence |
|---|---|---|
| M1 package the engine | done | `scripts/verify_release.py` -> `OK - release verified` |
| M2 attractive docs | done | `mkdocs build --strict` green; `links` -> 0 |
| M3 independent verification | done | `docs/Team/Archive.md` verdicts |
| M4 publish | done | tags `v1.0.0`, `v1.0.1`, `v1.0.2`, `v1.1.0` on the local `main`; `v1.1.2` is tagged on the published side and is not on the local `main` yet |
| M5a engine split + Windows green | done | commits `c8fb469`, `f2e3b5a`, `b7fe03b`; CI `39173857076` |
| M5b dependency upkeep + governance refresh | done | `9b56f1b` (T-0014), `1d49c21` (T-0015), `4cd8afc` (T-0016) |
| M8 records hygiene | done | ceo T-0028, merge `62ef5db` (P-0027, Reviewer-4): merge fields proved or `pending`, Plan de-duplicated, manifest re-pinned |
| M7 review fan-out + claims | done | Developer T-0001, merge `8f210bc`, 10 new unit tests |
| M6 evidence packets + repro gate | done | T-0020..T-0025, `docs/Team/Archive.md`, merge `3934690` |

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| AC-5 privacy history is red on `main` (ceo T-0003) | the user's authorization for a history rewrite | CEO | remediating the history family means rewriting unpublished local history, a red line under AGENTS.md; the alternatives in the task record are an exact-literal allowlist entry with a written reason and Security Auditor triage, or keeping the role identity through the merge path so the finding never appears. The tree side is already green, so only the history side is at stake |
| ceo T-0003 the local history rewrite | the published tip to be the base of the rewrite | CEO | base the rewrite on `origin/main`, not on the local merge base, and carry the published side's files over verbatim ([D-20261020-CEO-8](Decisions.md)); the committer guard is what stops the red from coming back. The rewrite plan is measured (history scan FAIL -> PASS 0 in a throwaway clone) and the authorization asked for is in the ceo T-0003 task record |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
