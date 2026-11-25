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
| architect | T-0001 | always-on-cap | done | P-0013 | 1747999f |
| architect | T-0002 | install-docs | done | P-0015 | 1b3f4577 |
| architect | T-0003 | display-docs | done | P-0019 | 00085661 |
| ceo | T-0001 | team-records | done | P-0001 | 8cc5ac7e |
| ceo | T-0002 | records | done | P-0014 | 64ed98d9 |
| ceo | T-0003 | records | done | P-0017 | 563ba6a9 |
| ceo | T-0004 | records | done | P-0023 | fb70f188 |
| developer | T-0001 | evidence-staleness | done | P-0003 | 4f46b4be |
| developer | T-0002 | team-records | done | P-0002 | f9e0fab2 |
| developer | T-0003 | lanes | done | P-0004 | c41880f0 |
| developer | T-0004 | claims | done | P-0006 | 823dc743 |
| developer | T-0005 | tests | done | P-0011 | 1f8d2dfd |
| developer | T-0006 | messages | done | P-0009 | 73404e80 |
| developer | T-0007 | bundle | done | P-0007 | 3c82fecd |
| developer | T-0008 | records | done | P-0008 | dd5cfa1c |
| developer | T-0009 | tests | done | P-0010 | 7f25caee |
| developer | T-0010 | records | done | P-0012 | 32ea1a5f |
| developer | T-0011 | sync | done | P-0016 | 60c1bbbd |
| developer | T-0012 | - | dropped | - | - |
| developer | T-0013 | - | dropped | - | - |
| developer | T-0014 | display | done | P-0020 | e77751d2 |
| developer | T-0015 | display | done | P-0018 | 1cce01e9 |
| developer | T-0016 | tests | done | P-0021 | 77feee0d |
| developer | T-0017 | tests | done | P-0022 | 236e2d7e |
| developer | T-0018 | tests | done | - | - |
| developer | T-0019 | release-gates | done | - | - |
| developer | T-0020 | release-gates | done | - | - |
| developer | T-0021 | release-gates | done | P-0024 | ba8c9b7e |
| developer | T-0022 | release-gates | done | P-0025 | 673f2b62 |
| developer | T-0023 | display | done | P-0027 | 857bc45c |
| developer | T-0024 | display | done | P-0026 | 28d6787c |
| developer | T-0025 | - | doing | - | - |
| tester | T-0001 | pi-package | done | P-0005 | 366a4cdd |

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
| developer | T-0025 · Allow the plugins root in the hygiene census | P0 | doing | - |

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
| architect | M9 T-0003 | architecture | done | P-0075 | 6642817b550cfa857f203304ab89c2e56454e0f4 |
| architect | M9 T-0004 | architecture | done | P-0079 | 5016c9ba3112ef0e32fefc30b1d4ec9fd7cf67e1 |
| architect | M9 T-0005 | ci | dropped | P-0081 | - |
| ceo | M9 T-0059 | release | done | P-0069 | b6deb2ce2be538856625a650d04d13378d327c66 |
| ceo | M9 T-0060 | - | done | - | - |
| ceo | M9 T-0061 | release | done | P-0070 | b6deb2ce2be538856625a650d04d13378d327c66 |
| ceo | M9 T-0062 | release | done | P-0067 | 7637265aad2bfbc3ddd2eb57fe980b6b7bf407da |
| ceo | M9 T-0063 | - | done | - | - |
| ceo | M9 T-0064 | docs | done | P-0082 | a0abd27789fb811f200e50b0be23d0c42de58b3e |
| ceo | M9 T-0065 | - | done | P-0096 | 2d3cdad650acf0273181450adec944ed42a76088 |
| ceo | M9 T-0066 | links | done | P-0098 | 9e96904cf0f723f139e9d0faec6131edeff7d3c2 |
| ceo | M9 T-0067 | - | done | P-0097 | f62539d6e0dfb8467a3531798a9a97fb5e01ecc0 |
| ceo | M9 T-0068 | - | done | - | - |
| ceo | M9 T-0069 | - | done | - | - |
| ceo | M9 T-0070 | links | done | P-0100 | e462b6d2ab013f4fab97e3683b8db90c96c485e6 |
| ceo | M9 T-0071 | - | done | P-0108 | 185930a07bd8d5fa98fff3963bfdc67502dd9454 |
| ceo | M9 T-0072 | - | done | P-0110 | 73abae71e17397a2f5fe7e6af31bbdc0be8ef80e |
| ceo | M9 T-0073 | - | done | P-0111 | c284799cf141981e173af49e467835488916baaa |
| ceo | M9 T-0074 | - | review | P-0115 | - |
| developer | M9 T-0005 | release | done | P-0073 | a0abd27789fb811f200e50b0be23d0c42de58b3e |
| developer | M9 T-0006 | release | done | P-0074 | 2f2763474695f77488637df7d1f6475c26a237e6 |
| developer | M9 T-0007 | makefile | done | P-0071 | bdae827c06c32e2aa310028d918fd21aafbb6f48 |
| developer | M9 T-0009 | release-consistency | done | P-0085 | 5016c9ba3112ef0e32fefc30b1d4ec9fd7cf67e1 |
| developer | M9 T-0010 | release | done | - | - |
| developer | M9 T-0011 | ci-contracts | done | P-0083 | a0abd27789fb811f200e50b0be23d0c42de58b3e |
| developer | M9 T-0012 | release-consistency | done | P-0080 | a0abd27789fb811f200e50b0be23d0c42de58b3e |
| developer | M9 T-0013 | release-consistency | done | P-0084 | bdae827c06c32e2aa310028d918fd21aafbb6f48 |
| developer | M9 T-0014 | - | done | P-0089 | ba51bce7fd44926232d7b95f9029148f67b5a52b |
| developer | M9 T-0015 | - | done | P-0091 | f08d444f88e0089446712d5d66af0058f8761567 |
| developer | M9 T-0016 | - | done | P-0095 | e06be40403888416d3b10d66578b74c28ea9647a |
| developer | M9 T-0017 | - | done | P-0094 | e06be40403888416d3b10d66578b74c28ea9647a |
| developer | M9 T-0018 | - | done | P-0101 | 27117c002f1627c1b141e480a17bb7954b19267e |
| developer | M9 T-0019 | - | done | P-0107 | 6ddc837d6880e45989f26cc22ccffaca8fc9946c |
| developer | M9 T-0020 | - | done | P-0106 | 6ddc837d6880e45989f26cc22ccffaca8fc9946c |
| developer | M9 T-0021 | - | done | P-0109 | 73abae71e17397a2f5fe7e6af31bbdc0be8ef80e |
| developer | M9 T-0022 | ci | done | P-0112 | 1c8836d6ba109c0ab2f5b551e70736e0a74543aa |
| developer | M9 T-0023 | ci | done | P-0113 | 1c8836d6ba109c0ab2f5b551e70736e0a74543aa |
| developer | M9 T-0024 | - | done | P-0114 | aaa4457ff7590898f56804cf495e09ccd2687be9 |
| reviewer | M9 T-0002 | - | done | - | - |
| reviewer | M9 T-0003 | - | done | P-0093 | 674cd795d91af76bf1f483ed94481a8afbc5771a |
| reviewer | M9 T-0004 | - | done | P-0102 | e462b6d2ab013f4fab97e3683b8db90c96c485e6 |
| tester | M9 T-0003 | - | done | P-0087 | 7cc3c74d9b3f3497c90f4526c117b8d33c9755fe |
| tester | M9 T-0004 | - | done | P-0092 | f08d444f88e0089446712d5d66af0058f8761567 |
| tester | M9 T-0005 | - | done | P-0103 | 27117c002f1627c1b141e480a17bb7954b19267e |
| tester | M9 T-0006 | - | done | - | - |
| product-manager | M9 T-0001 | traceability | done | P-0037 | 0c3816e9779e565b9fb1d0d65ddfdf4842f0366f |
| project-manager | M9 T-0001 | - | done | P-0034 | 69116cc |
| project-manager | M9 T-0002 | plan | done | P-0086 | 0e60134e20d0e0df05d71350a39cda1d7f978682 |
| release-engineer | M9 T-0001 | - | done | - | - |
| release-engineer | M9 T-0002 | release | done | P-0062 | a8dc95c2657727879a251ea0a984c0935fdc6fe4 |
| release-engineer | M9 T-0003 | ci | done | P-0076 | bdae827c06c32e2aa310028d918fd21aafbb6f48 |
| release-engineer | M9 T-0004 | - | dropped | - | - |
| release-engineer | M9 T-0005 | release | done | P-0072 | 7637265aad2bfbc3ddd2eb57fe980b6b7bf407da |
| release-engineer | M9 T-0006 | - | done | - | - |
| release-engineer | M9 T-0007 | release | done | P-0078 | bdae827c06c32e2aa310028d918fd21aafbb6f48 |
| release-engineer | M9 T-0008 | ci | done | - | - |
| release-engineer | M9 T-0009 | - | done | P-0090 | b6deb2ce2be538856625a650d04d13378d327c66 |
| release-engineer | M9 T-0010 | - | done | P-0104 | 22c48c03e89e4ace4c9b3aaed14e8cf49292e2c6 |
| release-engineer | M9 T-0011 | - | dropped | - | - |
| release-engineer | M9 T-0012 | - | done | - | - |
| security-auditor | M9 T-0001 | core | dropped | P-0023 | - |
| security-auditor | M9 T-0002 | - | dropped | - | - |
| security-auditor | M9 T-0003 | security | done | P-0051 | 4e1e53f |
| security-auditor | M9 T-0004 | - | done | P-0058 | a55e33a1597db50ee9e52595ae158ec8c3d3c0d2 |
| security-auditor | M9 T-0005 | privacy | done | P-0088 | a2f587b520fe1f70827b1e0e0ea909eca37f3a88 |

In flight at the M9 close, kept with the record:

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | M9 T-0074 · Docs and tree hygiene: update stale README/docs claims, delete dead symbols, remove redundant banners | P0 | review | - |
## Dependency PRs (landed)

| PR | bump | outcome |
|---|---|---|
| #11 | `anchore/sbom-action` 0.24.0 -> 0.24.3 | closed; landed in `42c930b7752dc43f0c1dbf2c520a4cef94730458` via #17 |
| #12 | `actions/attest-build-provenance` -> `4d101475` | closed; landed in `42c930b7752dc43f0c1dbf2c520a4cef94730458` via #17 |
| #13 | `softprops/action-gh-release` -> `efb35369` | closed; landed in `42c930b7752dc43f0c1dbf2c520a4cef94730458` via #17 |

The three branches were rebased onto `42c930b7752dc43f0c1dbf2c520a4cef94730458` (the earlier red Windows jobs came
from the retired umask assertion, fixed in `f60489efbb85d809baa9513c247ac69d5f983525`), each passed 17/17 checks,
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
| M5a engine split + Windows green | done | commits `73cb0429c043b827a1b5f8fd37b1e68bc88fef7f`, `f60489efbb85d809baa9513c247ac69d5f983525`, `6bf81d35702dfd61eedea6eab26c0fd0b4e14ffa`; CI `39173857076` |
| M5b dependency upkeep + governance refresh | done | `42c930b7752dc43f0c1dbf2c520a4cef94730458` (T-0014), `42c930b7752dc43f0c1dbf2c520a4cef94730458` (T-0015), `42c930b7752dc43f0c1dbf2c520a4cef94730458` (T-0016) |
| M8 records hygiene | done | ceo T-0028, merge fields repaired, Plan de-duplicated, manifest re-pinned |
| M7 review fan-out + claims | done | Developer T-0001, merge `2e9f01581886073701105266533a6f0ad1542f10`, 10 new unit tests |
| M6 evidence packets + repro gate | done | T-0020..T-0025, `docs/Team/Archive.md`, merge `4a98b7af321740217db459f5310d52ccf9b12f61` |

## Blocked

| task | waiting on | owner | unblock action |
|---|---|---|---|
| release-engineer T-0015 - backfill the already-tagged release to npm, the evidence AC-22 is waiting on | the operator's one-time npm trusted-publisher configuration for `.github/workflows/release.yml` (or an `NPM_TOKEN` repository secret) | release-engineer lane; the CEO runs the dispatch, the lane publishes nothing | once the credential exists, the CEO runs the release workflow's dispatch path for the existing tags in ascending version order; the close is `npm view @nidvue/teamwork dist-tags` and `scripts/check_release_consistency.py --online` (rule R3) on the merged revision |
| purge of the pre-rewrite commit object | GitHub garbage collection or Support | CEO | owner decision: leave it, recreate the repository, or file a Support purge request. It is unreachable from any branch and was already unreachable when the history was rewritten |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
