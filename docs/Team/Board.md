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
| architect | T-0003 | architecture | doing | P-0129 | - |
| architect | T-0004 | lanes | review | P-0131 | - |
| architect | T-0005 | lanes | todo | - | - |
| ceo | T-0001 | - | dropped | - | - |
| ceo | T-0002 | throughput | done | - | - |
| ceo | T-0003 | context | done | P-0001 | 2fcd9fd |
| ceo | T-0004 | records | dropped | P-0011 | - |
| ceo | T-0005 | - | dropped | - | - |
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
| ceo | T-0020 | records | done | P-0051 | f36e133 |
| ceo | T-0021 | team-docs | done | P-0052 | f187e21 |
| ceo | T-0022 | records | done | P-0053 | c2bed4b |
| ceo | T-0023 | records | done | P-0062 | 55817f9 |
| ceo | T-0024 | graph | done | P-0065 | 825aff2 |
| ceo | T-0025 | - | done | P-0067 | 33f5761 |
| ceo | T-0026 | identity | done | P-0068 | bbc7cdd |
| ceo | T-0027 | lanes | done | P-0069 | 352b81f |
| ceo | T-0028 | - | done | - | - |
| ceo | T-0029 | records | done | P-0070 | f695188 |
| ceo | T-0030 | ui | done | P-0071 | cf41761 |
| ceo | T-0031 | graph | done | P-0072 | eb40ea2 |
| ceo | T-0032 | records | done | P-0073 | d300307 |
| ceo | T-0033 | records | done | P-0074 | 01f547e |
| ceo | T-0034 | records | done | P-0075 | 2e9a621 |
| ceo | T-0035 | decisions | done | P-0077 | 494cf667 |
| ceo | T-0036 | records | done | P-0079 | c824be5a |
| ceo | T-0037 | records | done | P-0083 | f6e62305 |
| ceo | T-0038 | records | done | P-0085 | dbc56003 |
| ceo | T-0039 | - | done | - | - |
| designer | T-0001 | design | done | P-0086 | 830636bc |
| designer | T-0002 | design | done | P-0088 | 7abfa18e |
| designer | T-0003 | design | done | P-0096 | cd59fa15 |
| designer | T-0004 | design | done | P-0107 | 449cbd20 |
| designer | T-0005 | - | done | - | - |
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
| developer | T-0022 | hooks | done | P-0054 | b90089c |
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
| developer | T-0034 | - | done | - | - |
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
| developer | T-0055 | privacy | done | P-0055 | 0d913cf |
| developer | T-0056 | records | done | P-0056 | b8805b8 |
| developer | T-0057 | records | done | P-0057 | 0908643 |
| developer | T-0058 | privacy | done | P-0058 | 567402a |
| developer | T-0059 | lanes | done | P-0059 | b060209 |
| developer | T-0060 | ledger | done | P-0061 | 8a50ec9 |
| developer | T-0061 | ci | done | P-0063 | 0096027 |
| developer | T-0062 | lanes | done | P-0064 | 1360077 |
| developer | T-0063 | tests | done | P-0076 | 7f439aa1 |
| developer | T-0064 | worktree | done | P-0078 | 29d20d4f |
| developer | T-0065 | status | done | P-0080 | 53225821 |
| developer | T-0066 | lanes | done | P-0082 | dbb42541 |
| developer | T-0067 | board | done | P-0089 | bf95dfc5 |
| developer | T-0068 | agent-state-display | done | P-0087 | 008b126d |
| developer | T-0069 | - | dropped | - | - |
| developer | T-0070 | status-widget | done | P-0091 | 5e37f092 |
| developer | T-0071 | pr-merge | done | P-0093 | 66f2a703 |
| developer | T-0072 | records | done | P-0094 | 5267f8ea |
| developer | T-0073 | pi-package | done | P-0095 | ad86404b |
| developer | T-0074 | status | done | P-0097 | cd28c50c |
| developer | T-0075 | - | dropped | - | - |
| developer | T-0076 | widget | done | P-0099 | 926ec94c |
| developer | T-0077 | - | dropped | - | - |
| developer | T-0078 | audit | done | P-0100 | 9de0c8b1 |
| developer | T-0079 | docs-link-graph | done | P-0104 | c77cd126 |
| developer | T-0080 | privacy-scan | done | P-0105 | ebcff866 |
| developer | T-0081 | widget-header | done | P-0106 | 262be1e3 |
| developer | T-0082 | status | done | P-0115 | 71d8da75 |
| developer | T-0083 | team-records | done | P-0109 | - |
| developer | T-0084 | widget | done | P-0112 | 7e085c95 |
| developer | T-0085 | unit-coverage | done | P-0117 | 85a94e26 |
| developer | T-0086 | model-cost-policy | done | P-0118 | 47d6a6fa |
| developer | T-0087 | model-cost-policy | selfcheck | P-0120 | - |
| developer | T-0088 | lanes | review | P-0130 | - |
| developer | T-0089 | lanes | done | P-0123 | f37cf990 |
| developer | T-0090 | lanes | done | P-0121 | 2fcf72ec |
| developer | T-0091 | lanes | review | P-0124 | - |
| developer | T-0092 | extensions | done | P-0125 | 2319ae1f |
| developer | T-0093 | lanes | done | - | - |
| developer | T-0094 | model | review | P-0127 | - |
| developer | T-0095 | lanes | dropped | - | - |
| developer | T-0096 | lanes | done | - | - |
| developer | T-0097 | lanes | done | - | - |
| developer | T-0098 | lanes | done | P-0132 | 834c92bf |
| release-engineer | T-0001 | changelog | done | P-0084 | 88a60cd1 |
| release-engineer | T-0002 | - | dropped | - | - |
| release-engineer | T-0003 | - | done | - | - |
| release-engineer | T-0004 | release-integrity | done | P-0108 | 3b7f4425 |
| release-engineer | T-0005 | changelog | done | P-0113 | c08da898 |
| reviewer | T-0001 | - | done | - | - |
| reviewer | T-0002 | - | done | - | - |
| reviewer | T-0003 | - | dropped | - | - |
| reviewer | T-0004 | security | done | P-0060 | 59c240f |
| reviewer | T-0005 | - | done | - | - |
| reviewer | T-0006 | - | done | - | - |
| reviewer | T-0007 | status | done | P-0090 | edc00c18 |
| reviewer | T-0008 | - | blocked | - | - |
| reviewer | T-0009 | - | done | - | - |
| reviewer | T-0010 | - | todo | - | - |
| reviewer | T-0011 | lanes | todo | - | - |
| reviewer | T-0012 | lanes | todo | - | - |
| reviewer | T-0013 | lanes | todo | - | - |
| reviewer | T-0014 | lanes | todo | - | - |
| reviewer | T-0015 | lanes | todo | - | - |
| security-auditor | T-0001 | security-audit | done | P-0102 | a9b0ef95 |
| security-auditor | T-0002 | security-audit | done | P-0111 | e5cfb54b |
| technical-writer | T-0001 | docs-audit | done | P-0101 | c1a0ca82 |
| technical-writer | T-0002 | docs-links | done | P-0119 | d1845257 |
| technical-writer | T-0003 | roles | done | P-0128 | 059e413c |
| team-leader | T-0001 | ci | done | P-0002 | 5de68e8 |
| team-leader | T-0002 | lanes | blocked | P-0126 | - |
| tester | T-0001 | - | done | P-0023 | dadd920 |
| tester | T-0002 | - | done | P-0026 | 4c857a4 |
| tester | T-0003 | - | dropped | - | - |
| tester | T-0004 | tests | done | P-0066 | 66d55cd |
| tester | T-0005 | - | done | P-0081 | cc343480 |
| tester | T-0006 | ci-shard-matrix | done | P-0092 | 23aa21e4 |
| tester | T-0007 | ui-agent-state | done | P-0098 | 7284ad6b |
| tester | T-0008 | tests | done | P-0103 | 49e8fde7 |
| tester | T-0009 | tests | done | P-0110 | 4986d86b |
| tester | T-0010 | pi-package | done | P-0114 | 5164a1db |
| tester | T-0011 | tests | done | P-0116 | 1e3ae139 |

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
| architect | T-0003 · Freeze the lane-runtime contract so a team leader can own the reliability stream | P0 | doing | - |
| architect | T-0004 · Root cause: T-0003 timed out (silent) on Architect | P1 | review | - |
| architect | T-0005 · Root cause: T-0003 timed out (silent) on Architect | P1 | todo | - |
| developer | T-0087 · New team and model auto must not silently pick the host premium default | P2 | selfcheck | - |
| developer | T-0088 · A finished or lost lane leaves its worktree, its merged branch and its temp files behind, and a stalled lane is only killed when someone runs reap | P1 | review | - |
| developer | T-0091 · pulse pins a review claim that swarm run will not adopt, so a review sits idle for its whole lease | P1 | review | - |
| developer | T-0094 · model auto must refuse a premium host default even when only part of the config is named | P1 | review | - |
| reviewer | T-0008 · Verify AC-M19-6 and AC-M20-5 on the landed revision | P1 | blocked | - |
| reviewer | T-0010 · Encode L-0058 as a tw- skill: reviewing a destructive path (enumerate what it deletes and the key, run terminal+live on the same key before trusting the concurrency paragraph) | P2 | todo | - |
| reviewer | T-0011 · Root cause: T-0090 timed out (silent) on Reviewer-2 | P1 | todo | - |
| reviewer | T-0012 · Root cause: T-0091 timed out (silent) on Reviewer | P1 | todo | - |
| reviewer | T-0013 · Root cause: T-0094 timed out (silent) on Reviewer-3 | P1 | todo | - |
| reviewer | T-0014 · Root cause: T-0089 timed out (silent) on Reviewer | P1 | todo | - |
| reviewer | T-0015 · Root cause: T-0091 timed out (silent) on Reviewer-2 | P1 | todo | - |
| team-leader | T-0002 · Own the lane-runtime stream: staff a squad, decompose the defect backlog, dispatch and report | P0 | blocked | - |

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
