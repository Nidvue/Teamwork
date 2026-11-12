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
| architect | T-0001 | architecture | done | P-0003 | bef4e02 |
| architect | T-0002 | - | dropped | - | - |
| architect | T-0003 | - | done | P-0036 | 90eb61c |
| architect | T-0004 | architecture | done | P-0042 | be2c868 |
| architect | T-0005 | architecture | done | P-0067 | bb7c34f |
| architect | T-0006 | - | done | P-0082 | f4cd70f |
| architect | T-0007 | - | done | P-0081 | 0340949 |
| architect | T-0008 | memory | done | P-0144 | 09acc97 |
| ceo | T-0001 | review | done | P-0001 | 2f44f00 |
| ceo | T-0002 | docs | done | P-0008 | 28c1133 |
| ceo | T-0003 | - | done | - | - |
| ceo | T-0004 | - | dropped | - | - |
| ceo | T-0005 | records | done | P-0010 | f91bf1b |
| ceo | T-0006 | - | dropped | - | - |
| ceo | T-0007 | - | dropped | - | - |
| ceo | T-0008 | records | done | P-0016 | 51b8235 |
| ceo | T-0009 | audit | done | P-0019 | bbbe525 |
| ceo | T-0010 | - | done | - | - |
| ceo | T-0011 | - | done | - | - |
| ceo | T-0012 | audit | done | P-0029 | e74cde1 |
| ceo | T-0013 | - | done | - | - |
| ceo | T-0014 | audit | done | P-0034 | 67e0b0a |
| ceo | T-0015 | plan | done | P-0056 | 22c817d |
| ceo | T-0016 | - | dropped | - | - |
| ceo | T-0017 | review | done | P-0057 | 13fb170 |
| ceo | T-0018 | org | done | P-0069 | 911c064 |
| ceo | T-0019 | plan | done | P-0091 | bff7c80 |
| ceo | T-0020 | records | done | P-0058 | bcf48e7 |
| ceo | T-0021 | org | done | P-0063 | 20e12ae |
| ceo | T-0022 | records | done | P-0060 | e7e4768 |
| ceo | T-0023 | records | done | P-0061 | 7c96192 |
| ceo | T-0024 | records | done | P-0062 | 394a386 |
| ceo | T-0025 | records | done | P-0064 | 3a489fb |
| ceo | T-0026 | records | done | P-0065 | 2fab37e |
| ceo | T-0027 | release | done | P-0071 | 786041c |
| ceo | T-0028 | release | done | P-0074 | 38bcef8 |
| ceo | T-0029 | skill | done | P-0078 | c571e2b |
| ceo | T-0030 | skill | done | P-0084 | aa98609 |
| ceo | T-0031 | records | done | P-0085 | 7bc4f15 |
| ceo | T-0032 | docs | done | P-0087 | 3179a8a |
| ceo | T-0033 | memory | done | P-0092 | 6143378 |
| ceo | T-0034 | memory | done | P-0101 | 26cff20 |
| ceo | T-0035 | pi-package | done | P-0098 | 9a61ca8 |
| ceo | T-0036 | pi-package | done | P-0102 | e49e8b0 |
| ceo | T-0037 | lane-proof | done | P-0110 | 91dec22 |
| ceo | T-0038 | pi-packaging | done | P-0105 | 227af23 |
| ceo | T-0039 | memory | done | P-0119 | 697203b |
| ceo | T-0040 | records | done | P-0125 | 346256a |
| developer | T-0001 | harness | done | P-0004 | b33120c |
| developer | T-0002 | hooks | done | P-0007 | 49cd42e |
| developer | T-0003 | - | dropped | - | - |
| developer | T-0004 | tests | done | P-0012 | 1380163 |
| developer | T-0005 | records | done | P-0013 | 1592195 |
| developer | T-0006 | privacy | done | P-0015 | 0343b28 |
| developer | T-0007 | records | done | P-0014 | ba947c0 |
| developer | T-0008 | audit | done | P-0018 | 6d090aa |
| developer | T-0009 | governance | done | P-0025 | 5a705ba |
| developer | T-0010 | tests | done | P-0031 | f405c4e |
| developer | T-0011 | harness | done | P-0032 | 5177a25 |
| developer | T-0012 | - | done | P-0033 | 7f2184e |
| developer | T-0013 | - | done | P-0035 | 90eb61c |
| developer | T-0014 | - | dropped | - | - |
| developer | T-0015 | ci | done | P-0039 | d18a1b8 |
| developer | T-0016 | review | done | P-0038 | f849f2a |
| developer | T-0017 | release | done | P-0037 | 3f8b6dc |
| developer | T-0018 | coordination | done | P-0050 | cb232e5 |
| developer | T-0019 | records | dropped | P-0044 | - |
| developer | T-0020 | engine | done | P-0041 | 171b2cf |
| developer | T-0021 | tooling | done | P-0047 | 2f8be75 |
| developer | T-0022 | - | dropped | - | - |
| developer | T-0023 | - | dropped | - | - |
| developer | T-0024 | security | done | P-0040 | 343941f |
| developer | T-0025 | - | dropped | - | - |
| developer | T-0026 | records | done | P-0046 | 53ed4f1 |
| developer | T-0027 | release | done | P-0043 | a3aab49 |
| developer | T-0028 | board | done | P-0045 | a74aee4 |
| developer | T-0029 | - | dropped | - | - |
| developer | T-0030 | hooks | dropped | P-0049 | - |
| developer | T-0031 | - | dropped | - | - |
| developer | T-0032 | release | done | P-0048 | abbb067 |
| developer | T-0033 | - | dropped | - | - |
| developer | T-0034 | security | done | P-0053 | b1eabef |
| developer | T-0035 | security | done | P-0054 | 937d0d0 |
| developer | T-0036 | release | done | P-0052 | 7c1e2a5 |
| developer | T-0037 | hooks | done | P-0051 | d71a5ee |
| developer | T-0038 | - | dropped | - | - |
| developer | T-0039 | - | dropped | - | - |
| developer | T-0040 | records | done | P-0055 | 5d93c2c |
| developer | T-0041 | - | dropped | - | - |
| developer | T-0042 | t-0042 | done | P-0068 | fb8eae0 |
| developer | T-0043 | board | done | P-0066 | 321d0c4 |
| developer | T-0044 | deliver | done | P-0059 | e9eaacf |
| developer | T-0045 | records | done | P-0075 | f1aec91 |
| developer | T-0046 | records | done | P-0076 | 0e3f5f8 |
| developer | T-0047 | records | done | P-0077 | 4445f52 |
| developer | T-0048 | privacy | done | P-0070 | fc6da3a |
| developer | T-0049 | release | done | P-0072 | 982dfa6 |
| developer | T-0050 | release | done | P-0073 | bce6f07 |
| developer | T-0051 | release | done | P-0079 | d2e7f62 |
| developer | T-0052 | harness | done | P-0080 | ff62638 |
| developer | T-0053 | deliver | done | P-0088 | 82241bb |
| developer | T-0054 | memory | done | P-0095 | a42b13b |
| developer | T-0055 | memory | done | P-0096 | 81dcf8f |
| developer | T-0056 | memory | done | P-0099 | f644054 |
| developer | T-0057 | memory | done | P-0100 | 7bd7a68 |
| developer | T-0058 | preflight | done | P-0104 | dfad857 |
| developer | T-0059 | privacy | done | P-0103 | f706d5e |
| developer | T-0060 | records | done | P-0108 | 2570cec |
| developer | T-0061 | links | done | P-0109 | b9caf26 |
| developer | T-0062 | memory-verify | done | P-0111 | 046cb40 |
| developer | T-0063 | tests | done | P-0112 | f6bcc5b |
| developer | T-0064 | - | done | - | - |
| developer | T-0065 | ledger | done | P-0114 | ec2caef |
| developer | T-0066 | memory-index | done | P-0115 | a241963 |
| developer | T-0067 | worktree | done | P-0106 | 9c27344 |
| developer | T-0068 | - | dropped | - | - |
| developer | T-0069 | cli | done | P-0113 | 8f48845 |
| developer | T-0070 | pi-status | done | P-0118 | 40c8645 |
| developer | T-0071 | - | done | P-0116 | 2da10cd |
| developer | T-0072 | - | dropped | - | - |
| developer | T-0073 | - | dropped | - | - |
| developer | T-0074 | gate | done | P-0120 | 2fa4dee |
| developer | T-0075 | - | done | P-0123 | c714345 |
| developer | T-0076 | preflight | done | P-0122 | 4f034b3 |
| developer | T-0077 | gate | done | P-0124 | 10dd51b |
| developer | T-0078 | messaging | done | P-0126 | ee66695 |
| developer | T-0079 | records | done | P-0127 | dc36df0 |
| developer | T-0080 | identity | done | P-0128 | 2b19c07 |
| developer | T-0081 | records | done | P-0129 | b9dc113 |
| developer | T-0082 | identity | done | P-0130 | 077044f |
| developer | T-0083 | identity | done | P-0131 | c643103 |
| developer | T-0084 | identity | done | P-0132 | ec681f7 |
| developer | T-0085 | records | done | P-0133 | 871847f |
| developer | T-0086 | records | done | P-0134 | 874e76d |
| developer | T-0087 | identity | done | P-0135 | c345df0 |
| developer | T-0088 | tests | done | P-0136 | 1d79500 |
| developer | T-0089 | - | dropped | - | - |
| developer | T-0090 | tests | done | P-0137 | 37e1e29 |
| developer | T-0091 | ci | done | P-0138 | a01a6c3 |
| developer | T-0092 | ci | done | P-0139 | 11d3d1c |
| developer | T-0093 | ci | done | P-0140 | 442c829 |
| developer | T-0094 | windows-portability | done | P-0142 | 251a30e |
| developer | T-0095 | tests | done | P-0141 | 6e5aa6a |
| developer | T-0096 | tests | done | P-0143 | 702449c |
| developer | T-0097 | memory | done | P-0145 | 19246a0 |
| developer | T-0098 | memory | done | P-0147 | 318fb28 |
| developer | T-0099 | - | dropped | - | - |
| developer | T-0100 | - | todo | - | - |
| developer | T-0101 | - | doing | P-0146 | - |
| developer | T-0102 | identity | done | P-0152 | 1591449 |
| developer | T-0103 | ci-matrix | done | P-0148 | d1d11b6 |
| developer | T-0104 | privacy-scan | done | P-0149 | 41f2b97 |
| developer | T-0105 | ci | done | P-0150 | d4e5f59 |
| developer | T-0106 | memory | done | P-0151 | 03267a8 |
| developer | T-0107 | tests-unit-test-ci-contr | doing | P-0164 | - |
| developer | T-0108 | - | todo | - | - |
| developer | T-0109 | memory | done | P-0154 | 04b4983 |
| developer | T-0110 | - | todo | - | - |
| developer | T-0111 | ci | done | P-0155 | 422733c |
| developer | T-0112 | memory | done | P-0165 | c9c233f |
| developer | T-0113 | privacy | done | P-0156 | 36c0ca5 |
| developer | T-0114 | git-timeout | done | P-0157 | dee48ae |
| developer | T-0115 | identity | done | P-0158 | 762a40f |
| developer | T-0116 | privacy | done | P-0159 | c65dc84 |
| developer | T-0117 | identity | done | P-0160 | 5c963f1 |
| developer | T-0118 | identity | done | P-0161 | 00b62fd |
| developer | T-0119 | lane-proof | done | P-0162 | bc508dc |
| developer | T-0120 | portability | done | P-0163 | d1ed0f6 |
| developer | T-0121 | ci | review | P-0166 | - |
| developer | T-0122 | - | todo | - | - |
| product-manager | T-0001 | research | done | P-0005 | 73be637 |
| product-manager | T-0002 | records | done | P-0009 | 148c3de |
| product-manager | T-0003 | records | done | P-0017 | 49ad40e |
| product-manager | T-0004 | records | done | P-0020 | fe0afb9 |
| product-manager | T-0005 | records | done | P-0021 | 80f0cfa |
| product-manager | T-0006 | records | done | P-0027 | cd516f1 |
| product-manager | T-0007 | records | done | P-0028 | bd52cb8 |
| product-manager | T-0008 | records | done | P-0030 | 6a8a072 |
| product-manager | T-0009 | - | dropped | - | - |
| product-manager | T-0010 | memory | done | P-0093 | 91adb70 |
| reviewer | T-0001 | records | dropped | P-0023 | - |
| reviewer | T-0002 | records | done | P-0026 | e3fa290 |
| reviewer | T-0003 | - | done | - | - |
| reviewer | T-0004 | - | done | - | - |
| reviewer | T-0005 | - | done | - | - |
| reviewer | T-0006 | acceptance | done | P-0117 | 2174360 |
| security-auditor | T-0001 | audit | dropped | P-0022 | - |
| security-auditor | T-0002 | audit | done | P-0024 | 72c56ca |
| security-auditor | T-0003 | - | dropped | - | - |
| security-auditor | T-0004 | - | done | - | - |
| security-auditor | T-0005 | - | done | - | - |
| security-auditor | T-0006 | audit | done | P-0083 | 98232a8 |
| security-auditor | T-0007 | security | done | P-0094 | 90c5ecf |
| security-auditor | T-0008 | security | done | P-0107 | 97919b1 |
| tester | T-0001 | harness | done | P-0011 | 47db23d |
| tester | T-0002 | tests | done | P-0002 | 090910a |
| tester | T-0003 | tests | done | P-0006 | cc86e6d |
| tester | T-0004 | - | done | - | - |
| tester | T-0005 | harness | done | P-0086 | 41b38f6 |
| tester | T-0006 | tests | done | P-0089 | 2c4ad7e |
| tester | T-0007 | t-0042 | done | P-0090 | 6750ea7 |
| tester | T-0008 | memory | done | P-0097 | e34d6f7 |
| tester | T-0009 | - | done | - | - |
| tester | T-0010 | status | done | P-0121 | 9e8c3b3 |
| tester | T-0011 | memory | done | P-0153 | f5cb0d4 |
| tester | T-0012 | - | todo | - | - |

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
| developer | T-0100 · refresh stops on an unrelated mirror history and leaves every lane on a stale engine, with no warning | P1 | todo | - |
| developer | T-0101 · record the unit layer for the windows-portability area from the T-0094 run | P1 | doing | - |
| developer | T-0107 · close the census-guard class by inversion instead of enumerating word orders | P1 | doing | - |
| developer | T-0108 · T-0004 lane work | P2 | todo | - |
| developer | T-0110 · pr merge pins identity with -c only, so an exported GIT_AUTHOR_NAME can still author a merge commit | P2 | todo | - |
| developer | T-0121 · the Windows integration-m-z and unit-p-z shards are the last long jobs at 14m02s and 12m34s | P1 | review | - |
| developer | T-0122 · ledger_append has no cross-process serialisation, so a concurrent lane can make the head cache lead the file and raise a false truncation alarm | P1 | todo | - |
| tester | T-0012 · record the layer matrix for the twelve areas this milestone created, at one revision | P1 | todo | - |

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
