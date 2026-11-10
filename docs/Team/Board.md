# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## Snapshot (2026-10-20, `main` as `git rev-parse --short main` reports it)

- Milestone: M9 Harness^2 adoption is open. On `main`: `hooks` (developer T-0002,
  merge `49cd42e`), the ordered review rubric and the untrusted-material rule (ceo
  T-0001, merge `2f44f00`), Research section 8 (product-manager T-0001, merge
  `73be637`). Not on `main`: the `harness` command group - it is in rework behind
  P-0004 - and the Architect's contract, whose last review (`f476b82`) sent it back
  for rework. M8 records hygiene is closed (ceo T-0028, merge `62ef5db`).
- Local gate: `pytest -q` on this branch (`main` `74b5522`) -> 1 failed, 3 skipped.
  The one failure is
  `tests/unit/test_traceability_matrix.py::test_every_deterministic_state_matches_a_real_run`,
  i.e. the AC-5 privacy row below, not a code defect; the passing count is read
  from that run and never pinned here, because every commit that adds a test
  changes it. Two skips are the gitignored team tree (a worktree carries no
  `.pi/`), the third is the console-script acceptance test (covered by
  `verify_release.py`).
- Privacy: **RED at HEAD.** `python3 scripts/privacy_scan.py --tree --history
  --allow .github/privacy-allow.txt` -> FAIL, exit 1, in two families: commit
  metadata (the forge squash merge `4de397e` carries the operator account as
  author, and two unmerged branch commits `d692f38`, `a7f24af` match an
  e-mail/domain rule or the entropy rule in their messages) and tree text
  (`docs/Team/Archive.md` line 1070 quotes that operator address verbatim inside an
  archived reviewer finding). [Project](Project.md) row AC-5 still claims this gate
  green; the claim is false at this head and CEO T-0004 owns it, so this Board does
  not repeat it as green. The finding count is read from the run and never pinned:
  `--history` reaches other lanes' unmerged branches, so the count moves while
  `main` does not.
- Links: `teamwork.py links` -> 0 problems
- Gate: `teamwork.py loop` -> CONTINUE while any task branch is unmerged, and
  STOP only after the last review lands; `teamwork.py audit` lists one entry per
  open gate and its count moves with each review round, so it is read, not quoted.
  The closing export `docs/Team/AuditManifest.json` names the revision it was
  exported from, so it verifies at that head
- Remote: `origin/main` is behind the local merges until the Release Engineer
  pushes the reviewed revision; CI on the pushed SHA is the certification step.

- pi packaging: [Pi-Packaging](Pi-Packaging.md)

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| architect | T-0001 contract for the harness surface and the hooks CLI | P1 | in rework after 2 review rounds (P-0003, changes-requested) | `docs/Team/Architecture.md` 11, `docs/Team/Decisions.md` |
| developer | T-0001 `harness list` / `lint` / `budget` | P0 | in rework after 2 review rounds (P-0004, changes-requested at `5eabdc9`) | `src/teamwork/harness.py`, `tests/unit/test_harness_surface.py` |
| tester | T-0001 process-boundary + acceptance suite | P0 | blocked on developer T-0001 | `tests/integration/test_harness_cli.py`, `tests/acceptance/test_harness_docs.py` |
| ceo | T-0002 docs pass for the new surface | P1 | in review (P-0008 at `20a99fd`) | `docs/guide/cli.md`, `CHANGELOG.md`, `SKILL.md` |
| ceo | T-0003 / T-0004 the false AC-5 privacy claim | P0 / P2 | blocked on a ruling / ready | [Project](Project.md) AC-5 |
| reviewer | T-0001 run the acceptance record TS-0004 | P2 | ready | acceptance record TS-0004 |
| product-manager | T-0002 one clarifying line for `Project.md` | P3 | in review; the sentence is routed to the CEO, no edit made | this PR |

The task queue (`teamwork.py board`, `teamwork.py task list <role>`) is
authoritative for a task's exact state; this table only says which lanes are open.

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
| M4 publish | done | tags `v1.0.0`, `v1.0.1`, `v1.0.2`, `v1.1.0` with wheel, sdist, `SHA256SUMS`, SBOM |
| M5a engine split + Windows green | done | commits `c8fb469`, `f2e3b5a`, `b7fe03b`; CI `39173857076` |
| M5b dependency upkeep + governance refresh | done | `9b56f1b` (T-0014), `1d49c21` (T-0015), `4cd8afc` (T-0016) |
| M8 records hygiene | done | ceo T-0028, merge `62ef5db` (P-0027, Reviewer-4): merge fields proved or `pending`, Plan de-duplicated, manifest re-pinned |
| M7 review fan-out + claims | done | Developer T-0001, merge `8f210bc`, 10 new unit tests |
| M6 evidence packets + repro gate | done | T-0020..T-0025, `docs/Team/Archive.md`, merge `3934690` |

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| AC-5 privacy claim is false on `main` (ceo T-0003, T-0004) | a ruling on the three options in the task record | CEO | exempt the exact anchored literal with a written reason and Security Auditor triage; or keep the role identity through the merge path so the finding never appears; or rewrite published history - a red line that needs the user's authorization and would invalidate the SHAs `Archive.md` cites |
| tester T-0001 process-boundary suite | developer T-0001 (the `harness` engine) merging | Developer | rebase onto `main` and re-run the moment the engine lands; its probe merge already passes 26 of 29 against the hooks branch |
| purge of the pre-rewrite commit object | GitHub garbage collection or Support | CEO | owner decision: leave it, recreate the repository, or file a Support purge request. It is unreachable from any branch and was already unreachable when the history was rewritten |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
