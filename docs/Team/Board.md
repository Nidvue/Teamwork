# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## Snapshot (2026-10-19, `main` @ `8444134`)

Gates below are re-measured on this records branch (P-0026), which is based on
`main` 8444134 (the T-0003 merge) and adds only documentation, one justified
allowlist entry and its wiring, so the same commands reproduce on the merge commit.

- Milestone: M6 (evidence packets + repro gate) and M7 (reviewer fan-out + claims)
  are closed; `v1.0.2` is the latest release.
- Local gate: `pytest -q --cov=teamwork` -> 421 passed, 1 skipped, coverage 70.58%
  (floor 55%, enforced in `pyproject.toml` and `ci.yml`). The local skip is the
  console-script acceptance test (covered by `verify_release.py`).
- Privacy: `privacy_scan.py --tree --history --allow .github/privacy-allow.txt`
  -> PASS, 0 findings. Without `--allow` the same scan reports the audit quotation
  of the host install path and the scanner's own test fixture, which is why
  `make privacy` and both CI jobs pass exactly one justified allowlist file
  ([SECURITY](../../SECURITY.md), `docs/Team/Decisions.md` 2026-10-19).
- Links: `teamwork.py links` -> 0 problems (67 markdown files, 321 internal links)
- Gate: `teamwork.py audit` -> 20 problems, every one an open completion gate
  (unmerged branches, review-pending deliverables, layer gaps); `teamwork.py loop`
  -> CONTINUE while P-0026 and P-0027 are unmerged.
  The closing export is `docs/Team/AuditManifest.json` (chain verified, exported
  from a clean tree, four pinned artifacts plus the ledger head)
- Remote: `origin/main` is behind the local merges until the Release Engineer
  pushes the reviewed revision; CI on the pushed SHA is the certification step.

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | T-0027 close the M7 records, T-0028 repair the archive | P1 | in review (P-0026, P-0027) | `Plan.md`, `Board.md`, `Archive.md`, `AuditManifest.json` |

The task queue (`teamwork.py task list ceo`) is authoritative for a task's exact
state; this table only says which lanes are open.

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
| M4 publish | done | releases `v1.0.0`, `v1.0.1`, `v1.0.2` with wheel, sdist, `SHA256SUMS`, SBOM |
| M5a engine split + Windows green | done | commits `c8fb469`, `f2e3b5a`, `b7fe03b`; CI `39173857076` |
| M5b dependency upkeep + governance refresh | done | `9b56f1b` (T-0014), `1d49c21` (T-0015), `4cd8afc` (T-0016) |
| M6 evidence packets + repro gate | done | T-0020..T-0026, `docs/Team/Archive.md`, merge `479742d` |
| M7 review fan-out + claims | done | Developer T-0001, merge `8f210bc`, 10 new unit tests |

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| purge of the pre-rewrite commit object | GitHub garbage collection or Support | CEO | owner decision: leave it, recreate the repository, or file a Support purge request. It is unreachable from any branch and was already unreachable when the history was rewritten |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
