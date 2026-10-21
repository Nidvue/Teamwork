# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## Snapshot

- Milestone: M9 (release truth) is in progress. Its state is read with
  `teamwork.py board` and `teamwork.py task list <role>`; the rows of this
  board are a human summary of the same records.
- Release state, each fact read by its own command:
  - npm `latest`: `npm view @nidvue/teamwork dist-tags` -> the `latest` tag
  - newest git tag: `git tag -l --sort=-v:refname | head -1`
  - version on `main`: `grep __version__ src/teamwork/version.py`
  - the published version that has no tag: `cat release-exceptions.json`
- Local gate: `pytest -q` on this branch head -> all pass; the count is read from
  that run and never pinned here, because every commit that adds a test changes it.
  The one skip is the console-script acceptance test (covered by
  `verify_release.py`).
- Privacy: `privacy_scan.py --tree --history --allow .github/privacy-allow.txt`
  -> PASS, 0 findings; the shipped gate passes that allow file (`Makefile`,
  `ci.yml`, `docs.yml`). Without `--allow` the scan reports findings in exactly two
  path families - the pi install tree (`agent-config`) and one operator user name
  (`home-path`) - and no credential rule fires. The no-allow count is read from the
  run and never pinned: most of those hits are the justification text that documents
  the exemption, so the commit that documents the count raises it.
  `tests/unit/test_privacy_scan.py` pins every entry as one fully escaped literal,
  rejects a wildcard or a sibling name, and proves a credential on an exempted line
  is still reported. The alternatives (rewriting
  unpublished history, deleting a real reviewer finding) were refused in
  D-20261019-CEO-15: a user name or an install path is not a credential, and a
  credential quoted on the same line is still reported.
- Links: `teamwork.py links` -> 0 problems
- Gate: `teamwork.py loop` -> CONTINUE while any task branch is unmerged, and
  STOP only after the last review lands; `teamwork.py audit` lists one entry per
  open gate and its count moves with each review round, so it is read, not quoted.
  The closing export `docs/Team/AuditManifest.json` is committed with this pass
  and names the revision it was exported from, so it verifies at that head
- Remote: `origin/main` is behind the local merges until the Release Engineer
  pushes the reviewed revision; CI on the pushed SHA is the certification step.

- pi packaging: [Pi-Packaging](Pi-Packaging.md)

## M9 - release truth

The milestone is described in [Plan](Plan.md) (goal, non-goals, deliverables,
dependencies and the acceptance criteria). The state of every row is read with
`teamwork.py task list <role>`; the PR and the merged revision are read with
`teamwork.py pr list`. Task ids are allocated per role queue, so the same id
under two roles is two tasks.

| role | id | area | state | pr | merged revision |
|---|---|---|---|---|---|
| architect | T-0002 | architecture | dropped | P-0068 | - |
| architect | T-0003 | architecture | done | P-0075 | b02ed38 |
| architect | T-0004 | architecture | done | P-0079 | cf95b98 |
| architect | T-0005 | ci | dropped | P-0081 | - |
| ceo | T-0059 | release | done | P-0069 | 3078c48 |
| ceo | T-0060 | - | done | - | - |
| ceo | T-0061 | release | done | P-0070 | 135ae06 |
| ceo | T-0062 | release | done | P-0067 | e4b141c |
| ceo | T-0063 | - | done | - | - |
| ceo | T-0064 | docs | done | P-0082 | def7b1c |
| ceo | T-0065 | - | done | P-0096 | - |
| ceo | T-0066 | links | done | P-0098 | b6c0817 |
| ceo | T-0067 | - | done | P-0097 | 143e192 |
| ceo | T-0068 | - | done | - | - |
| ceo | T-0069 | - | done | - | - |
| ceo | T-0070 | links | done | P-0100 | 4e2fda5 |
| ceo | T-0071 | - | doing | - | - |
| developer | T-0005 | release | done | P-0073 | 5fa73ef |
| developer | T-0006 | release | done | P-0074 | 74740be |
| developer | T-0007 | makefile | done | P-0071 | 3ee1d35 |
| developer | T-0009 | release-consistency | done | P-0085 | f8dd596 |
| developer | T-0010 | release | done | - | - |
| developer | T-0011 | ci-contracts | done | P-0083 | a1a04bc |
| developer | T-0012 | release-consistency | done | P-0080 | 5fa73ef |
| developer | T-0013 | release-consistency | done | P-0084 | 602c56d |
| developer | T-0014 | - | done | P-0089 | 2cbb2e7 |
| developer | T-0015 | - | done | P-0091 | cc2f50f |
| developer | T-0016 | - | done | P-0095 | 03c7fbf |
| developer | T-0017 | - | done | P-0094 | b5fbc93 |
| developer | T-0018 | - | done | P-0101 | 35b6f2d |
| developer | T-0019 | - | done | P-0107 | 3404a42 |
| developer | T-0020 | - | done | P-0106 | - |
| reviewer | T-0002 | - | done | - | - |
| reviewer | T-0003 | - | done | P-0093 | f6242c9 |
| reviewer | T-0004 | - | done | P-0102 | 44259cb |
| tester | T-0003 | - | doing | P-0087 | - |
| tester | T-0004 | - | done | P-0092 | c84932e |
| tester | T-0005 | - | done | P-0103 | b91084d |
| product-manager | T-0001 | traceability | done | P-0037 | eeab44c |
| project-manager | T-0001 | - | done | P-0034 | 69116cc |
| project-manager | T-0002 | plan | done | P-0086 | 203b515 |
| release-engineer | T-0001 | - | done | - | - |
| release-engineer | T-0002 | release | done | P-0062 | d0c4c4a |
| release-engineer | T-0003 | ci | done | P-0076 | 46c4aeb |
| release-engineer | T-0004 | - | todo | - | - |
| release-engineer | T-0005 | release | done | P-0072 | 8fcf3fc |
| release-engineer | T-0006 | - | todo | - | - |
| release-engineer | T-0007 | release | done | P-0078 | 6fa8930 |
| release-engineer | T-0008 | ci | done | - | - |
| release-engineer | T-0009 | - | done | P-0090 | e3a2476 |
| release-engineer | T-0010 | - | done | P-0104 | 3b0fbfa |
| security-auditor | T-0001 | core | dropped | P-0023 | - |
| security-auditor | T-0002 | - | dropped | - | - |
| security-auditor | T-0003 | security | done | P-0051 | 4e1e53f |
| security-auditor | T-0004 | - | done | P-0058 | d40a5db |
| security-auditor | T-0005 | privacy | done | P-0088 | e2c18a5 |

Rows whose PR is not merged carry no merged revision; the revision is read
from the PR record, not from this table. A row with no PR is a task whose
deliverable landed by commit without a PR record.

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | T-0071 · The board-vs-queue comparison is a test, not a discipline | P1 | doing | - |
| tester | T-0003 · M9-J acceptance proof that the release claims hold | P1 | doing | - |
| release-engineer | T-0004 · M9-L push the merged M9 revision and certify CI on the pushed SHA | P0 | todo | - |
| release-engineer | T-0006 · CI identity audit: a rewritten-history push audits all history and fails on unrepairable old commits | P2 | todo | - |

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
| M8 records hygiene | done | ceo T-0028, merge fields repaired, Plan de-duplicated, manifest re-pinned |
| M7 review fan-out + claims | done | Developer T-0001, merge `8f210bc`, 10 new unit tests |
| M6 evidence packets + repro gate | done | T-0020..T-0025, `docs/Team/Archive.md`, merge `3934690` |

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| purge of the pre-rewrite commit object | GitHub garbage collection or Support | CEO | owner decision: leave it, recreate the repository, or file a Support purge request. It is unreachable from any branch and was already unreachable when the history was rewritten |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
