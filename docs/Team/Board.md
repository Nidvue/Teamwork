# BOARD - live status

Owner: Project Manager. Machine view: `teamwork.py board`. This file is the human
summary plus the blocker list.

Related: [Project](Project.md) · [Plan](Plan.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## Snapshot

- Milestone: M11 (solid review and tree truth) is live; M9 (release truth) and
  M10 (release truth on every OS) are closed. Live state is read with
  `teamwork.py board` and `teamwork.py task list <role>`; the rows of this board
  are rendered from those queues and are a human summary of the same records.
- Tree census (project-manager T-0001): 214 tracked files classified, 206 live,
  2 superseded-in-part records, 0 duplicates, 6 unreferenced in-tree and kept
  with a written reason, 0 deleted - see [Plan](Plan.md) M11.
- Release state, each fact read by its own command - no value is pinned here,
  because every one of them moves:
  - npm `latest`: `npm view @nidvue/teamwork dist-tags`
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


## M11 - solid review and tree truth (live)

The milestone is described in [Plan](Plan.md) M11. This table is rendered from
`Roles/*/TaskQueue.md` at the commit that carries it, so it is the queues' state
and not an opinion about it; read the same cells with
`teamwork.py task list <role>`, and the PR and merged revision with
`teamwork.py pr list`. Task ids are allocated per role queue, so the same id
under two roles is two tasks.

| role | id | area | state | pr | merged revision |
|---|---|---|---|---|---|
| architect | T-0001 | code-review | done | P-0008 | e47f5d5 |
| ceo | T-0001 | intake | doing | - | - |
| ceo | T-0002 | - | doing | - | - |
| ceo | T-0003 | - | todo | - | - |
| ceo | T-0004 | - | todo | - | - |
| ceo | T-0005 | - | todo | - | - |
| ceo | T-0006 | - | todo | - | - |
| ceo | T-0007 | - | done | P-0002 | 991dff1 |
| ceo | T-0008 | - | todo | - | - |
| ceo | T-0009 | - | todo | - | - |
| developer | T-0001 | - | done | P-0001 | fdd95a6 |
| developer | T-0002 | - | done | P-0011 | 5648f4c |
| developer | T-0003 | test-portability | done | P-0004 | dfb4d64 |
| developer | T-0004 | - | selfcheck | - | - |
| developer | T-0005 | - | dropped | - | - |
| developer | T-0006 | plan | done | P-0017 | 15e5988 |
| developer | T-0007 | engine | done | P-0010 | 0071014 |
| developer | T-0008 | - | doing | - | - |
| developer | T-0009 | - | doing | - | - |
| developer | T-0010 | - | doing | - | - |
| developer | T-0011 | - | doing | - | - |
| developer | T-0012 | plan | done | P-0015 | 17927a5 |
| developer | T-0013 | plan | doing | P-0018 | - |
| product-manager | T-0001 | traceability | done | P-0009 | 96160cf |
| project-manager | T-0001 | plan | done | P-0005 | 1bf629a |
| project-manager | T-0002 | - | doing | - | - |
| project-manager | T-0003 | plan | done | P-0016 | cfba521 |
| release-engineer | T-0001 | ci | done | P-0003 | c781596 |
| release-engineer | T-0002 | - | doing | - | - |
| release-engineer | T-0003 | - | todo | - | - |
| release-engineer | T-0004 | - | todo | - | - |
| release-engineer | T-0005 | - | doing | - | - |
| release-engineer | T-0006 | - | todo | - | - |
| release-engineer | T-0007 | ci | done | P-0013 | 183cf0d |
| reviewer | T-0001 | - | todo | - | - |
| reviewer | T-0002 | - | todo | - | - |
| reviewer | T-0003 | - | todo | - | - |
| security-auditor | T-0001 | - | done | P-0007 | f31b26e |
| security-auditor | T-0002 | - | review | - | - |
| security-auditor | T-0003 | - | todo | - | - |
| technical-writer | T-0001 | docs-truth | done | P-0006 | 641e610 |
| technical-writer | T-0002 | - | review | - | - |
| technical-writer | T-0003 | docs-truth | done | P-0014 | 8b9fac8 |
| tester | T-0001 | ci-release | done | P-0012 | aabff63 |

Rows whose PR is not merged carry no merged revision; the revision is read from
the PR record, not from this table. A task with no PR is a task whose deliverable
landed by commit without a PR record.

## In flight

| agent | task | prio | state | artifact |
|---|---|---|---|---|
| ceo | T-0001 · Own M11: intake, criteria, goal-layer tests, arbitration, close-out (manifest + final report) | P0 | doing | - |
| ceo | T-0002 · Register the two include: matrix lanes as required checks (py3.10, py3.12 run but do not block) | P1 | doing | - |
| ceo | T-0003 · Protect the v* tag pattern (no ruleset, no tag protection rule today) | P1 | todo | - |
| ceo | T-0004 · Clear the R8 drift at docs/Team/Decisions.md:1284 - it blocks the online release gate, so no tag can be released | P1 | todo | - |
| ceo | T-0005 · Decide required_linear_history on main (off; policy says no merge commits on the default branch) | P2 | todo | - |
| ceo | T-0006 · Make CodeQL a merge gate, and either enforce SHA pinning on actions or record why not | P2 | todo | - |
| ceo | T-0008 · Remove the two stale tier-init instance dirs .pi/Teamwork/Teams/Teamwork/Agents/Developer and Agents/Tester | P2 | todo | - |
| ceo | T-0009 · Project.md AC-5 row says green while the shipped privacy gate is FAIL at 7db810a | P1 | todo | - |
| developer | T-0004 · Remove the personal absolute path from commit a4c726f (message + resources.py docstrings) before it can merge | P0 | selfcheck | - |
| developer | T-0008 · harness.py:248 duplicates hooks_dir from hooks.py:76 with a divergent contract: None vs die, and unresolved repo/located vs .resolve | P1 | doing | - |
| developer | T-0009 · portable.py:53 stale type-ignore makes mypy red: 1 error on the tree | P2 | doing | - |
| developer | T-0010 · gitutil.py:132 ensure_lfs records a failed git lfs install silently, while the probe failure at 120-127 warns | P2 | doing | - |
| developer | T-0011 · identity --audit --range resolves against the primary checkout, so a worktree lane cannot audit its own branch | P0 | doing | - |
| developer | T-0013 · Board gate: a landing task cannot be stable; exclude it from both invariants | P0 | doing | - |
| project-manager | T-0002 · Reconcile the two M11 sections in Plan.md after the intake merges (one section, tool-derived state, no duplicated milestone) | P0 | doing | - |
| release-engineer | T-0002 · Pin the lint job's ruff to the project pin instead of installing the newest release | P1 | doing | - |
| release-engineer | T-0003 · ci.yml skips the privacy job (and every code job) on a prose-only push to main | P2 | todo | - |
| release-engineer | T-0004 · privacy-allow.txt: correct the exemption-mechanism sentence and record that the file is self-exempting | P3 | todo | - |
| release-engineer | T-0005 · CITATION.cff pins version 1.0.0 while version.py is 1.1.3 and the newest tag is v1.1.2 | P1 | doing | - |
| release-engineer | T-0006 · The commit-identity gate conflicts with the role mailbox: agents whose producer role differs from the repo-configured identity must fake 'Acting role:' | P1 | todo | - |
| reviewer | T-0001 · Serve the review queue and own the acceptance layer for the M11 deliverables | P0 | todo | - |
| reviewer | T-0002 · Second review seat: fan out the review queue, merge on pass, and cover the acceptance layer independently | P0 | todo | - |
| reviewer | T-0003 · Resolve the contradiction between AGENTS.md (commit as the acting role mailbox) and the Tester/Reviewer charter clause (use the locally configured identity) | P1 | todo | - |
| security-auditor | T-0002 · Re-commit P-0007 under the Security Auditor role identity and refresh the gate line now that the leak is fixed | P0 | review | - |
| security-auditor | T-0003 · AuditReport.md:23 restated 1 finding where the measured pair at 7db810a is 2 | P0 | todo | - |
| technical-writer | T-0002 · Remove the consumer email illustration and the matching commit-message line from P-0006 (privacy gate red) | P0 | review | - |

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
| purge of the pre-rewrite commit object | GitHub garbage collection or Support | CEO | owner decision: leave it, recreate the repository, or file a Support purge request. It is unreachable from any branch and was already unreachable when the history was rewritten |

## Duplicate or conflicting work

| what | owners | resolution |
|---|---|---|
| none | - | the frozen ownership table in [Architecture](Architecture.md) assigns exactly one writer per file |
