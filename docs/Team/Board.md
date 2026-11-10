# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## Snapshot

- Milestone: M12 (release parity: GitHub, npm, Pages) is the engagement that is
  live - intake in [Project](Project.md) M12, scope and rows in [Plan](Plan.md)
  M12, exit condition AC-22 and AC-23 verified by a role other than the author on
  the merged revision. M11 (solid review and tree truth) is still open behind it
  and its rows are in the same table below; M10 (release truth on every OS) and
  M9 (release truth) are closed. Live state is read with `teamwork.py board` and
  `teamwork.py task list <role>`; the rows of this board are rendered from those
  queues and are a human summary of the same records.
- Tree census (project-manager T-0001): 214 tracked files classified, 206 live,
  2 superseded-in-part records, 0 duplicates, 6 unreferenced in-tree and kept
  with a written reason, 0 deleted - see [Plan](Plan.md) M11.
- Release state, each fact read by its own command - no value is pinned here,
  because every one of them moves:
  - npm `latest`: `npm view @nidvue/teamwork dist-tags`
  - newest git tag: `git tag -l --sort=-v:refname | head -1`
  - version on `main`: `grep __version__ src/teamwork/version.py`
  - the published version that has no tag: `cat release-exceptions.json`
- Release parity (M12), each fact read by its own command and none of it pinned:
  - whether a tag publishes to npm: the `on:` block of
    `.github/workflows/release.yml` and `grep -c 'npm publish' .github/workflows/release.yml`
  - whether a tag rebuilds the site: the `on:` block of `.github/workflows/docs.yml`
    and the `github-pages` environment's deployment branch policies
    (`gh api repos/Nidvue/Teamwork/environments/github-pages/deployment-branch-policies`)
  - the two rows the M12 exit clause names, whose state this line must not quote:
    release-engineer T-0012 and release-engineer T-0011, read with
    `teamwork.py task list release-engineer`
  - the row that closes AC-22's evidence, and what it waits on: release-engineer
    T-0015, which is listed in the Blocked table below with the action that closes it
- Local gate: `pytest -q` on this branch head -> all pass; the count is read from
  that run and never pinned here, because every commit that adds a test changes it.
  A test that needs a tool the host lacks skips with a stated reason instead of
  failing or passing silently: the guard is `tests/tooling.py` (`require_tool`,
  `GUARDED_TOOLS`) and `tests/unit/test_tool_guards.py` pins it, including that no
  test runs a guarded tool without it - the same pair
  [Architecture](Architecture.md) names. The console-script acceptance test is
  covered by `scripts/verify_release.py`.
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


## Live queues - M11 and M12 (rendered)

One queue per role carries both open milestones: M11 (solid review and tree truth)
is described in [Plan](Plan.md) M11 and M12 (release parity: GitHub, npm, Pages) in
[Plan](Plan.md) M12. This table is rendered from
`Roles/*/TaskQueue.md` at the commit that carries it, so it is the queues' state
and not an opinion about it; read the same cells with
`teamwork.py task list <role>`, and the PR and merged revision with
`teamwork.py pr list`. Task ids are allocated per role queue, so the same id
under two roles is two tasks.

| role | id | area | state | pr | merged revision |
|---|---|---|---|---|---|
| architect | T-0001 | - | done | - | - |
| architect | T-0002 | architecture | done | P-0024 | eea0824 |
| ceo | T-0001 | - | dropped | - | - |
| ceo | T-0002 | throughput | doing | - | - |
| ceo | T-0003 | context | done | P-0001 | 2fcd9fd |
| ceo | T-0004 | records | dropped | P-0011 | - |
| ceo | T-0005 | - | doing | - | - |
| ceo | T-0006 | - | done | - | - |
| ceo | T-0007 | - | done | - | - |
| ceo | T-0008 | - | done | - | - |
| ceo | T-0009 | - | done | - | - |
| ceo | T-0010 | context | done | P-0013 | 6ad1132 |
| ceo | T-0011 | - | done | - | - |
| ceo | T-0012 | - | dropped | - | - |
| ceo | T-0013 | records | done | P-0014 | 8835b16 |
| ceo | T-0014 | - | dropped | P-0015 | - |
| ceo | T-0015 | records | dropped | P-0016 | - |
| ceo | T-0016 | team-docs | done | P-0018 | a88e9d2 |
| ceo | T-0017 | team-docs | done | P-0028 | ebc0c8b |
| ceo | T-0018 | team-docs | done | P-0031 | 079ee66 |
| ceo | T-0019 | team-docs | done | P-0041 | 1724fd7 |
| developer | T-0001 | - | done | - | - |
| developer | T-0002 | cli-records | done | P-0003 | 3ab4a0d |
| developer | T-0003 | memory | done | P-0005 | 521e190 |
| developer | T-0004 | harness | done | P-0035 | b2e5f10 |
| developer | T-0005 | preflight | done | P-0025 | ca60f28 |
| developer | T-0006 | io | done | P-0004 | c57e9d4 |
| developer | T-0007 | records | done | P-0009 | 9e3ed06 |
| developer | T-0008 | identity | done | P-0006 | 76bc10a |
| developer | T-0009 | git-timeout | done | P-0007 | 602ee84 |
| developer | T-0010 | clean | done | P-0036 | a2da634 |
| developer | T-0011 | config | done | P-0037 | cc7a923 |
| developer | T-0012 | preflight | done | - | - |
| developer | T-0013 | ledger | done | P-0038 | df22172 |
| developer | T-0014 | audit | done | P-0039 | 91c2d7f |
| developer | T-0015 | - | done | - | - |
| developer | T-0016 | - | done | - | - |
| developer | T-0017 | - | done | - | - |
| developer | T-0018 | typing | done | P-0040 | c24a595 |
| developer | T-0019 | - | done | - | - |
| developer | T-0020 | - | done | - | - |
| developer | T-0021 | - | done | - | - |
| developer | T-0022 | - | doing | - | - |
| developer | T-0023 | privacy | done | P-0008 | 206c099 |
| developer | T-0024 | - | dropped | - | - |
| developer | T-0025 | - | done | - | - |
| developer | T-0026 | - | done | - | - |
| developer | T-0027 | - | done | - | - |
| developer | T-0028 | ledger | done | P-0012 | e252fcc |
| developer | T-0029 | lanes | done | P-0022 | 2722c27 |
| developer | T-0030 | privacy | done | P-0010 | 25f2c0c |
| developer | T-0031 | - | done | - | - |
| developer | T-0032 | preflight | done | P-0032 | 0cbcb03 |
| developer | T-0033 | - | done | - | - |
| developer | T-0034 | - | todo | - | - |
| developer | T-0035 | merge | done | P-0033 | 4895b2a |
| developer | T-0036 | memory | done | P-0017 | a8ffd0e |
| developer | T-0037 | branch | done | P-0034 | b914ae4 |
| developer | T-0038 | lanes | done | P-0020 | dd5904e |
| developer | T-0039 | docs | done | P-0019 | 550118b |
| developer | T-0040 | lanes | done | P-0021 | d47922d |
| developer | T-0041 | lanes | done | P-0027 | cca7654 |
| developer | T-0042 | lanes | done | P-0029 | bc29abe |
| developer | T-0043 | memory | done | P-0030 | 55c891c |
| developer | T-0044 | - | done | - | - |
| developer | T-0045 | - | dropped | - | - |
| developer | T-0046 | clean | done | P-0042 | 4e31f14 |
| developer | T-0047 | audit | done | P-0043 | 8b5a3c9 |
| developer | T-0048 | audit | done | P-0044 | e24c38c |
| developer | T-0049 | audit | done | P-0045 | 6d4d6cd |
| developer | T-0050 | memory | done | P-0046 | 0e88de8 |
| developer | T-0051 | lanes | done | P-0047 | ad5753d |
| developer | T-0052 | audit | done | P-0048 | c95afdf |
| developer | T-0053 | preflight | done | P-0049 | 38112f9 |
| developer | T-0054 | audit | done | P-0050 | 17bd3a9 |
| reviewer | T-0001 | - | done | - | - |
| reviewer | T-0002 | - | done | - | - |
| team-leader | T-0001 | ci | done | P-0002 | 5de68e8 |
| tester | T-0001 | - | done | P-0023 | dadd920 |
| tester | T-0002 | - | done | P-0026 | 4c857a4 |

Rows whose PR is not merged carry no merged revision; the revision is read from
the PR record, not from this table. A task with no PR is a task whose deliverable
landed by commit without a PR record.

## Feature teams (rendered)

Shared services serve every feature and are attached to none: Architect, CEO, CFO, COO, CTO, Project Manager, Release Engineer, Reviewer, Security Auditor.

| feature | state | owner | squad | paths |
|---|---|---|---|---|
| F-0001 | ready | TeamLeader | - | .github/workflows/, scripts/, tests/, docs/guide/ci.md, docs/Team/Evolution.md |

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | T-0002 · Restore the record store and measure the engagement baseline with commands (pytest, lint, mypy, links, harness budget, throughput, archive size) | P0 | doing | - |
| ceo | T-0005 · Push the reviewed stage and confirm CI green on that SHA (route any red run to its owner) | P1 | doing | - |
| developer | T-0022 · the pre-commit gate installs no privacy scan although privacy_scan.py --staged exists (S-3) | P1 | doing | - |
| developer | T-0034 · task set --status selfcheck silently unsubmits a deliverable whose PR is already open | P2 | todo | - |

The task queue (`teamwork.py task list <role>`) is authoritative for a task's
exact state; this table only says which lanes are open.

## M9 - release truth (closed)

The milestone is described in [Plan](Plan.md) M9 (goal, non-goals, deliverables,
dependencies and the acceptance criteria). Its rows are the close record: the
worktree was re-initialised for M11, so the shared queues no longer carry these
ids and this table cannot be regenerated. Each merged revision is still read from
the PR record `teamwork.py pr list` holds for that branch.

| role | id | area | state at the M9 close | pr | merged revision |
|---|---|---|---|---|---|
| architect | M9 T-0002 | architecture | dropped | P-0068 | - |
| architect | M9 T-0003 | architecture | done | P-0075 | b02ed38 |
| architect | M9 T-0004 | architecture | done | P-0079 | cf95b98 |
| architect | M9 T-0005 | ci | dropped | P-0081 | - |
| ceo | M9 T-0059 | release | done | P-0069 | 3078c48 |
| ceo | M9 T-0060 | - | done | - | - |
| ceo | M9 T-0061 | release | done | P-0070 | 135ae06 |
| ceo | M9 T-0062 | release | done | P-0067 | e4b141c |
| ceo | M9 T-0063 | - | done | - | - |
| ceo | M9 T-0064 | docs | done | P-0082 | def7b1c |
| ceo | M9 T-0065 | - | done | P-0096 | df3de8c |
| ceo | M9 T-0066 | links | done | P-0098 | b6c0817 |
| ceo | M9 T-0067 | - | done | P-0097 | 143e192 |
| ceo | M9 T-0068 | - | done | - | - |
| ceo | M9 T-0069 | - | done | - | - |
| ceo | M9 T-0070 | links | done | P-0100 | 4e2fda5 |
| ceo | M9 T-0071 | - | done | P-0108 | 9099e51 |
| ceo | M9 T-0072 | - | done | P-0110 | 4af8b2e |
| ceo | M9 T-0073 | - | done | P-0111 | 25f8f3e |
| ceo | M9 T-0074 | - | review | P-0115 | - |
| developer | M9 T-0005 | release | done | P-0073 | 5fa73ef |
| developer | M9 T-0006 | release | done | P-0074 | 74740be |
| developer | M9 T-0007 | makefile | done | P-0071 | 3ee1d35 |
| developer | M9 T-0009 | release-consistency | done | P-0085 | f8dd596 |
| developer | M9 T-0010 | release | done | - | - |
| developer | M9 T-0011 | ci-contracts | done | P-0083 | a1a04bc |
| developer | M9 T-0012 | release-consistency | done | P-0080 | 5fa73ef |
| developer | M9 T-0013 | release-consistency | done | P-0084 | 602c56d |
| developer | M9 T-0014 | - | done | P-0089 | 2cbb2e7 |
| developer | M9 T-0015 | - | done | P-0091 | cc2f50f |
| developer | M9 T-0016 | - | done | P-0095 | 03c7fbf |
| developer | M9 T-0017 | - | done | P-0094 | b5fbc93 |
| developer | M9 T-0018 | - | done | P-0101 | 35b6f2d |
| developer | M9 T-0019 | - | done | P-0107 | 3404a42 |
| developer | M9 T-0020 | - | done | P-0106 | 3fad639 |
| developer | M9 T-0021 | - | done | P-0109 | 6962dfb |
| developer | M9 T-0022 | ci | done | P-0112 | 8e87b9e |
| developer | M9 T-0023 | ci | done | P-0113 | f3330c4 |
| developer | M9 T-0024 | - | done | P-0114 | dc260d7 |
| reviewer | M9 T-0002 | - | done | - | - |
| reviewer | M9 T-0003 | - | done | P-0093 | f6242c9 |
| reviewer | M9 T-0004 | - | done | P-0102 | 44259cb |
| tester | M9 T-0003 | - | done | P-0087 | a43e61e |
| tester | M9 T-0004 | - | done | P-0092 | c84932e |
| tester | M9 T-0005 | - | done | P-0103 | b91084d |
| tester | M9 T-0006 | - | done | - | - |
| product-manager | M9 T-0001 | traceability | done | P-0037 | eeab44c |
| project-manager | M9 T-0001 | - | done | P-0034 | 69116cc |
| project-manager | M9 T-0002 | plan | done | P-0086 | 203b515 |
| release-engineer | M9 T-0001 | - | done | - | - |
| release-engineer | M9 T-0002 | release | done | P-0062 | d0c4c4a |
| release-engineer | M9 T-0003 | ci | done | P-0076 | 46c4aeb |
| release-engineer | M9 T-0004 | - | dropped | - | - |
| release-engineer | M9 T-0005 | release | done | P-0072 | 8fcf3fc |
| release-engineer | M9 T-0006 | - | done | - | - |
| release-engineer | M9 T-0007 | release | done | P-0078 | 6fa8930 |
| release-engineer | M9 T-0008 | ci | done | - | - |
| release-engineer | M9 T-0009 | - | done | P-0090 | e3a2476 |
| release-engineer | M9 T-0010 | - | done | P-0104 | 3b0fbfa |
| release-engineer | M9 T-0011 | - | dropped | - | - |
| release-engineer | M9 T-0012 | - | done | - | - |
| security-auditor | M9 T-0001 | core | dropped | P-0023 | - |
| security-auditor | M9 T-0002 | - | dropped | - | - |
| security-auditor | M9 T-0003 | security | done | P-0051 | 4e1e53f |
| security-auditor | M9 T-0004 | - | done | P-0058 | d40a5db |
| security-auditor | M9 T-0005 | privacy | done | P-0088 | e2c18a5 |

In flight at the M9 close, kept with the record:

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | M9 T-0074 · Docs and tree hygiene: update stale README/docs claims, delete dead symbols, remove redundant banners | P0 | review | - |
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
| release-engineer T-0015 - backfill the already-tagged release to npm, the evidence AC-22 is waiting on | the operator's one-time npm trusted-publisher configuration for `.github/workflows/release.yml` (or an `NPM_TOKEN` repository secret) | release-engineer lane; the CEO runs the dispatch, the lane publishes nothing | once the credential exists, the CEO runs the release workflow's dispatch path for the existing tags in ascending version order; the close is `npm view @nidvue/teamwork dist-tags` and `scripts/check_release_consistency.py --online` (rule R3) on the merged revision |
| purge of the pre-rewrite commit object | GitHub garbage collection or Support | CEO | owner decision: leave it, recreate the repository, or file a Support purge request. It is unreachable from any branch and was already unreachable when the history was rewritten |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
