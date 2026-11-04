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
| architect | T-0001 | portability | done | P-0012 | 0cac9bd |
| architect | T-0002 | contract | doing | P-0037 | - |
| architect | T-0003 | - | todo | - | - |
| architect | T-0004 | architecture | done | P-0051 | d6d178e |
| architect | T-0005 | architecture | done | P-0052 | ee33a3d |
| architect | T-0006 | architecture | done | P-0055 | d05763c |
| ceo | T-0001 | - | done | P-0005 | d36e731 |
| ceo | T-0002 | - | done | P-0006 | cd561a5 |
| ceo | T-0004 | - | done | P-0019 | f3a765f |
| ceo | T-0005 | plan | done | P-0024 | eed95de |
| ceo | T-0006 | - | done | - | - |
| ceo | T-0007 | plan | done | P-0030 | dacd0f3 |
| ceo | T-0008 | records | doing | P-0033 | - |
| ceo | T-0009 | - | todo | - | - |
| ceo | T-0010 | records | done | P-0036 | 5ffaf70 |
| ceo | T-0011 | release | done | P-0040 | 1c91255 |
| ceo | T-0012 | records | review | P-0041 | - |
| ceo | T-0013 | - | blocked | - | - |
| ceo | T-0014 | - | done | - | - |
| ceo | T-0015 | records | done | P-0045 | bbdffbf |
| ceo | T-0016 | release | done | P-0046 | 2893940 |
| ceo | T-0017 | records | done | P-0049 | d3a7988 |
| ceo | T-0018 | records | done | P-0050 | 4d34851 |
| ceo | T-0019 | records | done | P-0062 | bace8e2 |
| ceo | T-0020 | throughput | dropped | - | - |
| ceo | T-0021 | privacy | done | P-0063 | ca608bf |
| ceo | T-0022 | merge | done | P-0065 | 9c18b3c |
| ceo | T-0023 | - | dropped | - | - |
| ceo | T-0024 | - | done | P-0068 | 46b084f |
| designer | T-0001 | - | done | P-0002 | 7783953 |
| designer | T-0002 | docs | done | P-0004 | aeb5d62 |
| designer | T-0003 | ui-assets | done | P-0013 | 1f648fd |
| designer | T-0004 | ui-readme | done | P-0020 | a5294b3 |
| designer | T-0005 | ui-assets | done | P-0023 | 94f3e40 |
| designer | T-0006 | ui-readme | done | P-0035 | 0a80105 |
| developer | T-0001 | - | done | P-0008 | 304d757 |
| developer | T-0002 | - | done | P-0003 | 381bb5c |
| developer | T-0003 | - | done | P-0009 | cf26e96 |
| developer | T-0004 | - | done | P-0007 | 252e9d4 |
| developer | T-0005 | clean | done | P-0010 | 6111b1a |
| developer | T-0006 | - | done | P-0017 | 5895411 |
| developer | T-0007 | board | done | P-0018 | 4895f66 |
| developer | T-0008 | assets | done | P-0021 | baa2cdb |
| developer | T-0009 | release | done | P-0027 | 938aad4 |
| developer | T-0010 | records | done | P-0022 | dbe19a8 |
| developer | T-0011 | records | done | P-0032 | 6877247 |
| developer | T-0012 | - | dropped | - | - |
| developer | T-0013 | records | done | P-0026 | 9789d84 |
| developer | T-0014 | attention | done | P-0031 | 02fcdbf |
| developer | T-0015 | engine | done | P-0039 | 326e4cf |
| developer | T-0016 | docs | done | P-0029 | 7decc35 |
| developer | T-0017 | records | done | P-0038 | b260682 |
| developer | T-0018 | release | done | P-0034 | 55ba101 |
| developer | T-0019 | engine | done | P-0042 | 3b16a9c |
| developer | T-0020 | - | done | - | - |
| developer | T-0021 | - | doing | - | - |
| developer | T-0022 | - | dropped | - | - |
| developer | T-0023 | review | done | P-0044 | 1d25519 |
| developer | T-0024 | - | todo | - | - |
| developer | T-0025 | - | todo | - | - |
| developer | T-0026 | - | todo | - | - |
| developer | T-0027 | - | doing | - | - |
| developer | T-0028 | - | dropped | - | - |
| developer | T-0029 | - | todo | - | - |
| developer | T-0030 | - | todo | - | - |
| developer | T-0031 | skills | done | P-0053 | 35b5695 |
| developer | T-0032 | knowledge | done | P-0056 | 81ea5cd |
| developer | T-0033 | context | done | P-0060 | 92df95c |
| developer | T-0034 | throughput | done | P-0058 | b9e5135 |
| developer | T-0035 | - | todo | - | - |
| developer | T-0036 | branch | blocked | - | - |
| developer | T-0037 | lint | doing | - | - |
| developer | T-0038 | identity | done | P-0067 | 3ba9d4b |
| developer | T-0039 | concurrency | review | P-0069 | - |
| developer | T-0040 | - | todo | - | - |
| developer | T-0041 | - | todo | - | - |
| reviewer | T-0001 | - | done | - | - |
| reviewer | T-0002 | records | done | - | - |
| technical-writer | T-0001 | - | done | P-0001 | ff9a708 |
| technical-writer | T-0002 | - | done | P-0011 | 543c665 |
| technical-writer | T-0003 | - | done | P-0014 | a1929ba |
| technical-writer | T-0004 | - | done | P-0016 | aeed914 |
| technical-writer | T-0005 | docs | done | P-0025 | b29a8bc |
| technical-writer | T-0006 | - | doing | - | - |
| technical-writer | T-0007 | - | todo | - | - |
| technical-writer | T-0008 | - | dropped | - | - |
| technical-writer | T-0009 | changelog | done | P-0047 | 4539796 |
| technical-writer | T-0010 | release | done | P-0048 | 856ba14 |
| technical-writer | T-0011 | docs | done | P-0054 | 723987c |
| technical-writer | T-0012 | - | dropped | - | - |
| technical-writer | T-0013 | docs | done | P-0061 | b4096f5 |
| technical-writer | T-0014 | - | todo | - | - |
| technical-writer | T-0015 | - | doing | - | - |
| technical-writer | T-0016 | - | todo | - | - |
| tester | T-0001 | integration | done | P-0015 | 8b5db3f |
| tester | T-0002 | integration | done | P-0028 | 4198781 |
| tester | T-0003 | integration | doing | P-0043 | - |
| tester | T-0004 | skills | done | P-0057 | 2fe28e2 |
| tester | T-0005 | context | done | P-0064 | e35352a |
| tester | T-0006 | throughput | done | P-0059 | 4c28b85 |
| tester | T-0007 | context | done | P-0066 | 8f5f8e2 |

Rows whose PR is not merged carry no merged revision; the revision is read from
the PR record, not from this table. A task with no PR is a task whose deliverable
landed by commit without a PR record.

## Feature teams (rendered)

Shared services serve every feature and are attached to none: Architect, CEO, CFO, COO, CTO, Project Manager, Release Engineer, Reviewer, Security Auditor.

| feature | state | owner | squad | paths |
|---|---|---|---|---|

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| architect | T-0002 · M15 A8: Architecture section 11 freezes nine release-consistency rules; R10 makes the frozen contract false | P2 | doing | - |
| architect | T-0003 · Section 5 does not name Attention.md, the record T-0014 introduces; add the workspace-format row when it merges | P2 | todo | - |
| ceo | T-0008 · M15 plan: the surfaces table says four and lists five rows | P3 | doing | - |
| ceo | T-0009 · Plan.md still says the release-consistency checker has nine rules; R10 makes it ten (no project-manager role is staffed to own the file) | P1 | todo | - |
| ceo | T-0012 · M16 A0: charter the proportionality adoption (AC-13, AC-14, research section 11) | P1 | review | - |
| ceo | T-0013 · Release 1.5.0: tag the reviewed merged revision, push the tag, and certify the Release run publishes it | P0 | blocked | - |
| developer | T-0021 · clean deletes what another lane still depends on: a live review worktree, and a bound evidence artifact | P1 | doing | - |
| developer | T-0024 · links scans gitignored .pi Scratch, so a stale draft turns the link gate red team-wide | P2 | todo | - |
| developer | T-0025 · tests add invents a near-duplicate area (intake vs task-intake), so one run has to be recorded twice and the plan shows phantom gaps | P3 | todo | - |
| developer | T-0026 · docs/Team/Decisions.md is a pure append point, so every lane's entry conflicts on every later merge and tasks are failed for it twice | P2 | todo | - |
| developer | T-0027 · Integrate the published line into integration/m15-m16 (PR #30): three conflicts, both sides' behaviour preserved | P0 | doing | - |
| developer | T-0029 · CI annotates every ubuntu-latest job with a runner-image migration notice; pin the image or record why not | P2 | todo | - |
| developer | T-0030 · bb9866f left a dead BADGE_TABLE_ROW constant and a fragile header lookup in the badge guard | P3 | todo | - |
| developer | T-0035 · Code scanning: py/incomplete-url-substring-sanitization in tests/unit/test_skill_contracts.py | P2 | todo | - |
| developer | T-0036 · M20 B1: close branches that are no longer useful with branch prune | P0 | blocked | - |
| developer | T-0037 · M20 C1: no comments in code, enforced by the lint gate | P0 | doing | - |
| developer | T-0039 · M18 A6: make the lesson/knowledge concurrency tests tolerate a lock timeout while proving no lost record | P0 | review | - |
| developer | T-0040 · M20 F2: cap agent-initiated follow-up chains at a recorded hop depth | P1 | todo | - |
| developer | T-0041 · M20 F3: task text stays data - a task field can never set agent, cwd or access | P1 | todo | - |
| technical-writer | T-0006 · M15 A4: document the authority/attention model (reference, SKILL, AGENTS block, research check, changelog) | P1 | doing | - |
| technical-writer | T-0007 · M16 A2: the proportionality contract in the team's own documents (reference, constitution, docs rule, marker test) | P1 | todo | - |
| technical-writer | T-0014 · M20 A1: split README.md into a landing page and linked docs pages | P0 | todo | - |
| technical-writer | T-0015 · M20 F1: research Agent Autoloop - what Teamwork should adopt, adapt or reject | P1 | doing | - |
| technical-writer | T-0016 · M20 F4: tests name the failure they prevent, and the state modules stay pure | P2 | todo | - |
| tester | T-0003 · M15 A5: integration proof that mandate, accept mode, attention and stage compose on a throwaway tree | P1 | doing | - |

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
