# ARCHIVE - accepted results

Owner: CEO. Appended automatically when a task passes independent review. The
team's evidence ledger: what shipped, by whom, verified how, at which revision.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md)

Gate order: owner self-check -> Reviewer verdict -> entry below.
## T-0001 · Portability test + engine change verification  (architect)
- date: 2026-10-17
- priority: P0
- owner: architect role (work by: Architect)
- reviewer: Reviewer-2
- task / issue: -
- area: -
- self-check: [pass] re-read the portability suite: newline + Python 3.9 guards, pid_alive, resource resolution | test: PYTHONPATH=src ./.venv/bin/python -m pytest tests/unit/test_portability.py tests/unit/test_portable.py -q @710e68d -> 26 passed in 0.30s
- author evidence: -
- reviewer evidence: PYTHONPATH=src ./.venv/bin/python -m pytest tests/unit/test_portability.py tests/unit/test_portable.py -q @710e68d -> 26 passed in 0.30s
- findings history: -
- branch / merge: - / pending
## T-0002 · Add architecture-guide back-link to Architecture.md (link reciprocity)  (architect)
- date: 2026-10-17
- priority: P1
- owner: architect role (work by: Architect)
- reviewer: Reviewer-2
- task / issue: -
- area: -
- self-check: [pass] re-ran the link check after adding the guide back-link | test: python3 scripts/teamwork.py links @710e68d -> # issues: 0
- author evidence: -
- reviewer evidence: python3 scripts/teamwork.py links @710e68d -> # issues: 0
- findings history: -
- branch / merge: - / pending
## T-0001 · README + visual assets + docs/Team/Design.md  (designer)
- date: 2026-10-17
- priority: P0
- owner: designer role (work by: Designer-1)
- reviewer: Reviewer-1
- task / issue: -
- area: -
- self-check: [pass] reviewed the asset record, the improvement log and the user-first design principles | test: PYTHONPATH=src ./.venv/bin/python -m pytest tests/unit/test_imaging.py tests/unit/test_skill_contracts.py -q @710e68d -> 41 passed in 0.05s
- author evidence: -
- reviewer evidence: PYTHONPATH=src ./.venv/bin/python -m pytest tests/unit/test_imaging.py tests/unit/test_skill_contracts.py -q @710e68d -> 41 passed in 0.05s
- findings history: -
- branch / merge: - / pending
## T-0001 · Packaging: pyproject.toml (hatchling), Makefile, scripts/verify_release.py, .editorconfig  (developer)
- date: 2026-10-17
- priority: P0
- owner: developer role (work by: developer-1)
- reviewer: Reviewer-2
- task / issue: -
- area: -
- self-check: [pass] re-ran the release verification: wheel payload vs source bundle, clean-venv install, full loop | test: ./.venv/bin/python scripts/verify_release.py @710e68d -> verify_release: OK - release verified
- author evidence: pyproject.toml+Makefile+.editorconfig+scripts/verify_release.py delivered; PYTHON=.venv/bin/python make verify @worktree -> 'verify_release: OK - release verified' exit 0 (build sdist+wheel, wheel 50 entries incl teamwork/data/SKILL.md + teamwork/data/templates/AGENTS.md, no ungated Requires-Dist, SHA256SUMS written+sha256sum -c OK, clean venv install, teamwork --version/selftest 5/5/init all pass). Not committed: task forbade git checkout.
- reviewer evidence: ./.venv/bin/python scripts/verify_release.py @710e68d -> verify_release: OK - release verified
- findings history: -
- branch / merge: - / pending
## T-0002 · Tests: tests/unit + tests/integration + conftest.py  (developer)
- date: 2026-10-17
- priority: P0
- owner: developer role (work by: Developer-2)
- reviewer: Reviewer-2
- task / issue: -
- area: -
- self-check: [pass] re-ran unit + integration after the CRLF and 3.9 fixes | test: PYTHONPATH=src ./.venv/bin/python -m pytest tests/unit tests/integration -q @710e68d -> 208 passed in 1.14s
- author evidence: -
- reviewer evidence: PYTHONPATH=src ./.venv/bin/python -m pytest tests/unit tests/integration -q @710e68d -> 208 passed in 1.14s
- findings history: -
- branch / merge: - / pending
## T-0001 · CI/CD: .github/workflows/ci.yml, release.yml, docs.yml, dependabot.yml  (release-engineer)
- date: 2026-10-17
- priority: P0
- owner: release-engineer role (work by: release-engineer)
- reviewer: Reviewer-1
- task / issue: -
- area: -
- self-check: [pass] confirmed the CI matrix and the docs workflow on the pushed revisions | test: gh run list --repo VisionPZ/Teamwork --workflow CI --limit 10 --json conclusion @710e68d -> CI/Docs runs quoted in the task evidence
- author evidence: -
- reviewer evidence: gh run list --repo VisionPZ/Teamwork --workflow CI --limit 10 --json conclusion @710e68d -> CI/Docs runs quoted in the task evidence
- findings history: -
- branch / merge: - / pending
## T-0001 · Privacy scanner + security audit report  (security-auditor)
- date: 2026-10-17
- priority: P0
- owner: security-auditor role (work by: security-auditor)
- reviewer: Reviewer-1
- task / issue: -
- area: -
- self-check: [pass] Re-read both deliverables and the frozen contract (Architecture sections 2/9, Project AC-5/AC-12). Verified stdlib-only import, mutually-combining flags, all eight rule families (20 findings on a synthetic fixture), allow-list suppression, masked-by-default output, redacted root, ruff check+format clean, report has 0 findings when scanned. Residual: history commit identity is a CEO-owned rewrite (report R5). | test: python3 scripts/privacy_scan.py --staged @staged -> exit 0 (self-scan: scripts/privacy_scan.py + docs/Team/AuditReport.md both clean); fixture --tree -> 20 findings across api-token/env-secret/high-entropy-secret/home-path/personal-email/private-domain/private-key/todo-credential || [pass] re-scanned tree and full history after the rewrite and the FP fix | test: python3 scripts/privacy_scan.py --tree --history @710e68d -> privacy_scan: PASS - 0 finding(s) in tree, history
- author evidence: -
- reviewer evidence: python3 scripts/privacy_scan.py --tree --history @710e68d -> privacy_scan: PASS - 0 finding(s) in tree, history
- findings history: -
- branch / merge: - / pending
## T-0001 · Docs site + community files: mkdocs.yml, docs/*.md, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, CHANGELOG, CITATION  (technical-writer)
- date: 2026-10-17
- priority: P1
- owner: technical-writer role (work by: technical-writer)
- reviewer: Reviewer-2
- task / issue: -
- area: -
- self-check: [pass] rebuilt the site in strict mode and re-ran the link check | test: ./.venv/bin/python -m mkdocs build --strict @710e68d -> INFO    -  Documentation built in 0.25 seconds
- author evidence: python -m mkdocs build --strict @working-tree -> exit 0, 0 warnings; python3 scripts/teamwork.py links @working-tree -> exit 1: 3 pre-existing broken links in docs/Team + 7 pre-existing missing back-links + 1 required docs/guide/architecture.md->docs/Team/Architecture.md back-link filed as architect T-0002
- reviewer evidence: ./.venv/bin/python -m mkdocs build --strict @710e68d -> INFO    -  Documentation built in 0.25 seconds
- findings history: -
- branch / merge: - / pending
## T-0001 · Acceptance tests: tests/acceptance/**  (tester)
- date: 2026-10-17
- priority: P0
- owner: tester role (work by: Tester-1)
- reviewer: Reviewer-1
- task / issue: -
- area: -
- self-check: [pass] re-ran acceptance locally and compared with the CI matrix on the pushed SHA | test: PYTHONPATH=src ./.venv/bin/python -m pytest tests/acceptance -q @710e68d -> 12 passed, 1 skipped in 1.17s
- author evidence: -
- reviewer evidence: PYTHONPATH=src ./.venv/bin/python -m pytest tests/acceptance -q @710e68d -> 12 passed, 1 skipped in 1.17s
- findings history: -
- branch / merge: - / pending

## T-0001 · Full-project audit: integrity, gate, ledger, path and CI fixes  (ceo)
- date: 2026-10-18
- priority: P0
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] re-read the full diff: parser boundary, lock order, ledger chain, path components, review/merge gates, privacy scanner, CI workflows and docs | test: pytest -q --cov=teamwork @ebaeb66 -> 333 passed, coverage 39.8%; make ci @ebaeb66 -> all gates passed
- author evidence: commit ebaeb66
- reviewer evidence: pytest -q --cov=teamwork @ebaeb66 -> 333 passed; privacy_scan --tree --history -> PASS; links -> 0; verify_release -> OK
- findings history: -
- branch / merge: - / pending

## T-0002 · Scope the audit-manifest anchor to the workspace id  (ceo)
- date: 2026-10-18
- priority: P1
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] re-read the manifest anchor path and the new test | test: pytest tests/unit/test_ledger.py @1ee691a -> 17 passed
- author evidence: commit 1ee691a
- reviewer evidence: pytest tests/unit/test_ledger.py @1ee691a -> 17 passed; teamwork audit -> 0 problems
- findings history: -
- branch / merge: - / pending

## T-0003 · Address final review notes: local git identity, CLI docs, changelog  (ceo)
- date: 2026-10-19
- priority: P2
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] re-read the bootstrap identity, CLI docs and changelog | test: pytest -q @1e646a9 -> 336 passed
- author evidence: commit 1e646a9
- reviewer evidence: pytest -q @1e646a9 -> 336 passed; identity --audit -> 0 problems; links -> 0
- findings history: -
- branch / merge: - / pending

## T-0004 · Correct exit-code docs and cover the local-identity guard  (ceo)
- date: 2026-10-19
- priority: P2
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] re-read the exit-code census, identity guard and new tests | test: pytest -q @043d483 -> 338 passed
- author evidence: commit 043d483
- reviewer evidence: pytest -q @043d483 -> 338 passed; links -> 0; privacy -> PASS
- findings history: -
- branch / merge: - / pending

## T-0005 · Fix dispute sign AttributeError and cover it  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] re-read dispute sign and the new regression test | test: pytest tests/unit/test_integrity_fixes.py @61eecc9 -> 30 passed
- author evidence: commit 61eecc9
- reviewer evidence: pytest tests/unit/test_integrity_fixes.py @61eecc9 -> 30 passed; dispute sign by developer -> exit 1, no traceback
- correction: the original entry said exit 2; re-measurement showed the role refusal exits 1. The code and test are unchanged.
- findings history: -
- branch / merge: - / pending

## T-0006 · Correct the exit-code example and cover tribunal sign  (ceo)
- date: 2026-10-19
- priority: P2
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] re-read the example row and the sign/resolve test | test: pytest tests/unit/test_integrity_fixes.py @29dc42f -> 30 passed
- author evidence: commit 29dc42f
- reviewer evidence: pytest tests/unit/test_integrity_fixes.py @29dc42f -> 30 passed; sign by ceo 0; resolve unsigned nonzero
- findings history: -
- branch / merge: - / pending

## T-0007 · Correct the T-0005 archive exit-code evidence  (ceo)
- date: 2026-10-19
- priority: P2
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: archive
- self-check: [pass] re-measured the dispute sign refusal and corrected the archive line | test: dispute sign by developer @b05d04a -> exit 1
- author evidence: commit b05d04a
- reviewer evidence: dispute sign by developer @b05d04a -> exit 1; archive line matches
- findings history: -
- branch / merge: - / pending

## T-0008 · Resolve residual audit items: umask, BOM-less UTF-16, nested repo, coverage, stale board  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] re-read umask, UTF-16 heuristic, nested repo, command-surface tests | test: pytest -q @e7a7d4d -> 350 passed; coverage 62.14%
- author evidence: commit e7a7d4d
- reviewer evidence: pytest -q @e7a7d4d -> 350 passed; coverage 62.14%; ruff/mypy/links/privacy clean
- findings history: -
- branch / merge: ceo/t-0008-resolve-residual-audit-items-umask-bom-l / pending

## T-0009 · Fix the pr-merge commit message acting role  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] re-read the merge message builder and the regression assertion | test: pytest tests/integration/test_workspace_flow.py @9e1ab8f -> 14 passed
- author evidence: commit 9e1ab8f
- reviewer evidence: pytest tests/integration/test_workspace_flow.py @9e1ab8f -> 14 passed; merge trailer Reviewer
- findings history: -
- branch / merge: ceo/t-0009-fix-the-pr-merge-commit-message-acting-r / pending

## T-0010 · Export the current audit manifest with a workspace TeamId  (ceo)
- date: 2026-10-19
- priority: P2
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] re-read the manifest TeamId, record count and checksums | test: ledger export @HEAD -> chain verified 94 records; audit/loop after merge
- author evidence: commit 384df6a
- reviewer evidence: ledger export @384df6a -> 94 records, chain verified; privacy PASS; links 0
- findings history: -
- branch / merge: ceo/t-0010-export-the-current-audit-manifest-with-a / pending

## T-0011 · Split engine.py into typed modules  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: engine
- self-check: [pass] re-read the split, the import DAG and the re-exported API | test: pytest -q @c8fb469 -> 350 passed; mypy clean; make ci all gates passed
- author evidence: commit c8fb469
- reviewer evidence: pytest -q @c8fb469 -> 350 passed; mypy -> clean; make ci -> all gates passed; import DAG config<-names/layout<-records<-engine
- findings history: -
- branch / merge: ceo/t-0011-split-engine-py-into-typed-modules / pending

## T-0012 · Skip the POSIX umask test on Windows  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: engine
- self-check: [pass] re-read the Windows skip and POSIX assertion | test: pytest tests/unit/test_integrity_fixes.py @f2e3b5a -> 32 passed
- author evidence: commit f2e3b5a
- reviewer evidence: pytest tests/unit/test_integrity_fixes.py @f2e3b5a -> 32 passed; Windows skip is platform-scoped
- findings history: -
- branch / merge: ceo/t-0012-skip-the-posix-umask-test-on-windows / pending

## T-0013 · Fix import order in the Windows skip test  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: engine
- self-check: [pass] re-read import order and lint | test: ruff check . @b7fe03b -> clean; pytest tests/unit/test_integrity_fixes.py -> 32 passed
- author evidence: commit b7fe03b
- reviewer evidence: ruff check . @b7fe03b -> clean; pytest tests/unit/test_integrity_fixes.py -> 32 passed
- findings history: -
- branch / merge: ceo/t-0013-fix-import-order-in-the-windows-skip-tes / pending

## T-0015 · Refresh stale governance docs against the merged revision  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: ceo)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] Re-read the four diffs against the merged revision: Plan task ids match the queue, Board figures match measured pytest coverage and the CI run ids, R-12 cites the actual uses-line count, Release drill cites the command just run | test: pytest -q @4c24c02 -> 350 passed, 1 skipped; links -> 0; privacy --tree -> PASS; verify_release -> OK || [pass] Re-read every failed finding against fresh commands: audit/loop classes, ledger n=138 at 6905869, PR heads and check counts from gh, gh auth scopes, task states from the queue, and the CI/Docs trigger behaviour from the workflow files and run 39175948257 | test: pytest -q @9680bad -> 350 passed, 1 skipped; links -> 0; privacy --tree -> PASS; mkdocs --strict -> built; gh pr checks 11/12/13 -> 17 pass each || [pass] Round 3: removed every transient figure (audit count, ledger n) in favour of reproducible statements; task state column now says in-flight with the queue authoritative; Release trigger paths enumerated to match ci.yml exactly; M5 split into done (engine) and in-flight (upkeep); area recorded as audit so no prose-only test area is invented (D-20261019-CEO-2) | test: pytest -q @0e00001 -> 350 passed, 1 skipped; links -> 0; privacy --tree -> PASS; tests plan -> audit unit/int/acc passing; audit -> 2 classes (3 open tasks, 1 unmerged branch)
- author evidence: commit 4c24c02; commit 9680bad; commit 0e00001
- reviewer evidence: PASS @0e00001 every claim re-measured. pytest -q --cov=teamwork -> 350 passed, 1 skipped, 62.38% (floor 55: pyproject.toml:173, ci.yml:148); links -> 0 problems; privacy_scan --tree --history -> PASS, 0 findings; mkdocs build --strict exit 0; verify_release.py -> OK - release verified 6.3s; gh pr checks 16 @0e00001 -> 17 pass + "deploy to GitHub Pages" skipping, all 14 required contexts pass (CI 39177619344, Docs 39177619026 both success at 0e00001); CI 39173857076 -> 16/16 success on b6dea2a; Docs 39176294486 -> success on 6905869; Docs-only push 39175948257 (0cc655d) -> only the Docs run; PR #11/#12/#13 heads 5874825/7cb50af/9c10386 parent 6905869, 17 pass + Pages skipped, their pre-rebase red CI 39173703667 was exactly test_atomic_write_respects_the_umask on windows (fixed f2e3b5a); branch protection: 1 approval, 14 contexts, strict, no force-push, no deletion, linear-history off; releases v1.0.0/v1.0.1/v1.0.2 carry wheel+tar.gz+SHA256SUMS+2 SBOMs; origin/main..main 0/0 and origin branch head 0e00001; ledger 157 records chain intact, exactly 138 records with ts <= 6905869 commit time 01:22:54; task list ceo -> T-0014 doing, T-0015 review area=audit, T-0016 todo; task queue is authoritative and Board now says only "in flight"/"todo" lanes; tests plan -> audit unit+/int+/acc+ and no governance area (D-20261019-CEO-2 accurate); audit -> 4 problems = 3 unfinished tasks + 1 deliverable awaiting review + 1 unmerged branch, no other class, and Board no longer states a count or a return-to-zero; loop -> CONTINUE with the same 3 blockers; R-10 scopes=repo via ssh, no workflow scope; R-12 28/28 uses: 40-hex SHA-pinned, 0 tag refs, top-level contents: read; Release trigger table matches ci.yml:22-32/docs.yml:16-26 incl SKILL.md in the matrix set; commits authored+committed by CEO <ceo@agents.nidvue.com> = the configured identity; .gitignore unchanged (a016fbd), tree clean
- findings history: FAIL @4c24c02 - 4 findings. (1) BLOCKER Board.md:17-18: "teamwork.py loop -> STOP, teamwork.py audit -> 0 problems, ledger chain intact (138 records)" is not reproducible at the revision: `python3 scripts/teamwork.py audit` @4c24c02 -> "# problems found: 8" (T-0015 awaiting review + 3 coverage gaps governance/unit|integration|acceptance + 4 completion-gate blockers) and `python3 scripts/teamwork.py loop` -> "> CONTINUE" with the same 4 blockers; .pi/.../Ledger.jsonl has 146 records now and 143 at this commit own entry (n=143, ts 2026-10-19T01:32:05) - 138 was true only before T-0014/T-0015 were created at 01:30:02. (2) BLOCKER Board.md:38: "#11 open, behind main / rebase requested; branch still carries the retired umask test" was already false at commit time: PR #11 head 5874825 updated 2026-10-18T23:30:58Z (before the 23:32:05Z doc commit) contains origin/main tip 6905869 and f2e3b5a, `git diff --stat origin/main 5874825 -- tests/ .github/` -> only release.yml 2 lines changed (no tests), and `gh pr view 11 --json mergeStateStatus,statusCheckRollup` -> BLOCKED, 18/18 checks SUCCESS. (3) BLOCKER Risks.md:19 (R-10): "executed 16/16 jobs green with the `workflow` scope" - `gh auth status` -> "Token scopes: admin:public_key, gist, read:org, repo", protocol ssh; no workflow scope, so the scope clause is unsupported and contradicted by the very command the row names (the 16/16-green part is true, run 39173857076 = 16 jobs success). (4) MAJOR Board.md:24 and Plan.md:22 record T-0014 as state "doing" / "in flight": `python3 scripts/teamwork.py task list ceo` -> "T-0014 [P0/todo] ... -> READY"; the task queue disagrees. Verified true and needing no change: coverage 62.38% vs floor 55 (pyproject.toml:173, ci.yml:148), pytest -q -> 350 passed 1 skipped, CI 39173857076 (16 jobs, b6dea2a) and Docs 39176294486 (6905869), 28/28 uses: SHA-pinned with 0 tag refs, origin/main..main 0/0, verify_release -> OK - release verified in 6.0 s, links -> 0, privacy --tree -> PASS, mkdocs build --strict exit 0, all 11 cited commit SHAs resolve. Fix 1-4 with re-measured values at the commit revision, then self-check and re-submit. | FAIL @9680bad (round 2) - 2 blocking + 2 minor findings; every other figure re-measured and true. (1) BLOCKER Board.md:22-26: 'teamwork.py audit -> 2 problem classes (3 unfinished tasks, one unmerged branch) ... No other audit class is open. Both return to 0 problems / STOP when the tasks close' is not reproducible at this head: `python3 scripts/teamwork.py audit` -> '# problems found: 8' built from FOUR completion-gate blockers ('BLOCKER 3 required test layer(s) missing or not passing', 'BLOCKER 3 task(s) not finished', 'BLOCKER 1 deliverable(s) not review-passed', 'BLOCKER 1 branch(es) not merged into main') plus '## deliverables awaiting independent review - ceo T-0015 [review] ... review_status=failed' plus three '## layered tests' hits ('coverage gap governance/unit|integration|acceptance: missing') = 4+1+3, so '2 problem classes' understates and 'No other audit class is open' is false. The return-to-zero promise is false too: areas_in_use() (src/teamwork/engine.py:1362-1370) keeps an area in use while any of its tasks is done OR review, and test_gaps() (engine.py:1395-1416) reports every required layer that has no passing record; .pi/Teamwork/Teams/Teamwork/TestPlan.md declares no governance entry and Tests.md has 0 governance records, so the three governance coverage gaps survive T-0015 -> done and audit stays non-zero after T-0014/T-0015/T-0016 close. Same defect class as round-1 finding (1). (2) MAJOR Board.md:33 and Plan.md:31 record T-0015 as 'doing' / 'doing (round 2)'; `task list ceo` -> 'T-0015 [P1/review]' (P-0007 [changes-requested]) - the round-1 instruction that doc states match the queue is still unmet. (3) MINOR Board.md:57 'M5 engine split + Windows green | done' contradicts Board.md:10 and Plan.md:17, which put M5 in flight with T-0014/T-0015/T-0016 open. (4) MINOR Release.md:38,56 shorthand '*.md' is wider than the ci.yml paths-ignore set (ci.yml:22-32 lists README/CHANGELOG/CONTRIBUTING/SECURITY/CODE_OF_CONDUCT + AGENTS.md, not SKILL.md) while the same table says SKILL.md runs the full matrix. Verified true at 9680bad and NOT to be churned: pytest -q -> 350 passed, 1 skipped; --cov=teamwork -> 62.38% (pyproject.toml:173 fail_under=55, ci.yml:148 --cov-fail-under=55); links -> 0 problems; privacy_scan --tree --history -> 'PASS - 0 finding(s)'; mkdocs build --strict exit 0; verify_release.py -> 'OK - release verified' (10.5 s wall / 6.8 s CPU here); ledger 152 records chain intact, exactly 138 records with ts<=6905869's commit time 01:22:54, so '138 records at that revision' is right; baseline audit 0 / loop STOP at 6905869 is consistent (T-0014/T-0015/T-0016 created 01:30:02+, all earlier tasks done/selfcheck, no unmerged branch); CI 39173857076 -> 16/16 success on b6dea2a; Docs 39176294486 -> success on 6905869; Docs-only push 39175948257 (0cc655d, docs/ only) ran only Docs; branch protection requires exactly 14 contexts; PR #11/#12/#13 heads 58748257/7cb50aff/9c103861 each have parent 6905869, mergeable, 17 pass + 'deploy to GitHub Pages' skipped; labels ci + dependencies exist; releases v1.0.0/v1.0.1/v1.0.2 with wheel, sdist, SHA256SUMS, 2 SBOMs; 28/28 'uses:' refs are 40-hex SHA with 0 tag refs; all three workflows set top-level permissions contents: read; gh auth status -> scopes admin:public_key, gist, read:org, repo in protocol ssh, so R-10's 'no workflow scope, SSH pushes do not need it' is correct; origin/main..main 0/0; PR #16 (docs only) triggered both CI 39177253014 and Docs 39177253016. Fix (1)-(4), self-check and re-submit.
- branch / merge: ceo/t-0015-refresh-stale-governance-docs-against-th / pending

## T-0014 · Rebase and merge the three open Dependabot action bumps after CI is green  (ceo)
- date: 2026-10-19
- priority: P0
- owner: ceo role (work by: ceo)
- reviewer: Reviewer-1
- task / issue: -
- area: -
- self-check: [pass] Re-read the one-file diff: three SHA swaps, comments updated for anchore, no other line changed; the target SHAs match the three rebased Dependabot heads; every uses: ref is still a 40-hex SHA | test: yaml.safe_load(release.yml) @b5d0687 -> ok; grep 'uses:' -> 28 refs, all SHA-pinned; pytest -q -> 350 passed, 1 skipped; gh pr checks 17 -> 17 pass
- author evidence: commit b5d0687
- reviewer evidence: git diff main...HEAD @b5d0687 -> only .github/workflows/release.yml, 4 lines (2x anchore 66cbf4bc + attest 4d101475 + gh-release efb35369); main + the 3 origin/dependabot diffs applied == PR head release.yml byte-identical; grep 'uses:' -> 28 refs, all 40-hex, 0 tag refs; yaml.safe_load(release.yml) -> ok; gh pr checks 17 @b5d0687 -> 14/14 required contexts pass (CI 39178008415, Docs 39178008409, Pages deploy skipped); privacy_scan --tree --history -> PASS; links -> 0 issues; pytest -q -> 350 passed, 1 skipped
- findings history: -
- branch / merge: ceo/t-0014-rebase-and-merge-the-three-open-dependab / pending

## T-0016 · Fix ensure_gitignore orphan headers and glob-covered entries  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: ceo)
- reviewer: Reviewer-1
- task / issue: -
- area: engine
- self-check: [pass] Re-read the diff: coverage is per-pattern via fnmatch, headers are section-scoped, the empty-file newline bug is fixed, and the tests cover empty/full, idempotent, glob-covered, partial-section and dangling-header cases | test: pytest tests/unit/test_gitignore_bootstrap.py @d3c40aa -> 5 passed; pytest -q -> 355 passed, 1 skipped; ruff check+format -> clean; mypy -> clean; teamwork.py repo on this repo -> no .gitignore change; gh pr checks 18 -> 17 pass
- author evidence: commit d3c40aa
- reviewer evidence: PASS @d3c40aa independent re-verification. Scope: git diff --stat main...HEAD -> only src/teamwork/engine.py (+37/-7) and tests/unit/test_gitignore_bootstrap.py (new, 70 lines); origin/main == main == 9b56f1b, PR #18 MERGEABLE, 0 behind. Logic read: sections are grouped header+entries, headers are appended only inside if missing (no orphan header), covered() tests pattern in (entry, entry.rstrip("/")) plus fnmatch both ways so .env.* covers .env.local, and the rewrite drops the leading blank line. Tests: pytest tests/unit/test_gitignore_bootstrap.py -q -> 5 passed; pytest -q -> 356 passed; pytest tests/unit/test_hygiene.py tests/unit/test_portability.py tests/unit/test_privacy_scan.py -q -> 75 passed; ruff check -> All checks passed; ruff format --check -> 109 files already formatted; mypy src/teamwork -> Success, no issues in 14 source files. Regression value proved: the same 5 new tests run against the pre-fix engine (main 9b56f1b checkout) -> 3 failed, 2 passed. Real-world A/B reproduction (same fixtures, both engines): .gitignore already carrying .env.* -> @d3c40aa added=[] on both runs, 0 dangling headers, 0 duplicate .env.local lines, file byte-identical between runs vs @9b56f1b added=[".env.local", ".env.*.local"]; fixture with every entry present and no teamwork headers -> @d3c40aa added=[] vs @9b56f1b 4 headers appended with 0 entries (the reported orphan-header defect); brand-new repo -> full block, no leading blank line, second run adds nothing; only .pi/ present -> second run adds nothing. Live repo: teamwork.py repo -> git status --short empty before and after, .gitignore md5 a016fbd2b0440250c4db3f4275d0a84f unchanged (untouched). CI: gh pr checks 18 @d3c40aa -> 17 pass + deploy-to-Pages skipping, all 14 required contexts green (lint, build, privacy, docs, links+privacy+strict build, test 3 OS x py3.9/3.11/3.13). Identity: identity --audit main..HEAD -> 1 commit ok, CEO <ceo@agents.nidvue.com> = git config user.name/email, 0 problems; message style fix(engine): matches history. No PR comments or reviews outstanding; no unrelated files; audit -> T-0016 as the only awaiting-review deliverable, no other problem class. Non-blocking notes: a section header that already exists is not deduplicated when one of its entries is still missing, and there is no test for the all-entries-present-without-header fixture (verified manually instead); docs/Team/Plan.md:32 and Board.md:35 still list T-0016 as todo and T-0014/T-0015 as in flight - a pre-existing governance snapshot for the CEO docs pass, not introduced by this diff (precedent: T-0012 f2e3b5a and T-0013 b7fe03b merged with no doc change).
- findings history: -
- branch / merge: ceo/t-0016-fix-ensure-gitignore-orphan-headers-and / pending

## T-0017 · Close M5: mark the board done and export the audit manifest  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: ceo)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] Re-read the four diffs: every task status matches the queue and the merge commits, M5a/M5b rows agree with the milestone table, the snapshot cites real run ids and measured coverage, the manifest reports 184 records with the chain verified | test: ledger export @73ec217 -> 184 records, chain verified True; links -> 0; privacy --tree -> PASS; pytest -q -> 355 passed, 1 skipped; gh pr checks 19 -> 17 pass || [pass] Round 2: corrected the skip attribution (console-script acceptance test locally, POSIX umask on Windows cells, 356 on Linux CI) and re-exported the manifest from a clean tree so git.dirty is false | test: pytest -q @762fdb8 -> 355 passed, 1 skipped with the cited test as the only skip; ledger export -> 191 records, chain verified True, dirty False; links -> 0; privacy --tree -> PASS
- author evidence: commit 73ec217; commit 762fdb8; commit 4eeda70
- reviewer evidence: @4eeda70: pytest -q -rs -> 355 passed, 1 skipped (skip tests/acceptance/test_entrypoints.py:90 console script); coverage 62.49% floor 55; CI 39179186345 on 4cd8afc 16/16 success, ubuntu py3.12 log 356 passed 0 skipped, windows py3.11 log skips test_integrity_fixes.py:538 umask; Docs 39179186471 success on 4cd8afc; gh pr checks 19 -> 17 pass + Pages skipping on 4eeda70 (run 39180024683 success); AuditManifest.json dirty=false head 762fdb8 191 records verified=true problems=[]; 5/5 artifact sha256 match, 22 local_state files present; ledger verify chain intact; merges 9b56f1b/1d49c21/4cd8afc on main; links 0; privacy_scan PASS 0 findings; v1.0.2 latest; T-0014..T-0016 done T-0017 review; author+committer CEO <ceo@agents.nidvue.com> = git config
- findings history: Board.md:11-13 mis-attributes the local test skip. Evidence @73ec217: the local run is Linux (python 3.14.8) and its single skip is tests/acceptance/test_entrypoints.py:90 "console script not installed; covered by scripts/verify_release.py"; the POSIX umask test is skipped only on Windows (tests/unit/test_integrity_fixes.py:538 skipif os.name=="nt"), which is the skip reported by CI run 39179186345 windows py3.13 (355 passed, 1 skipped), while Linux py3.13 in that same run is 356 passed, 0 skipped. So "(356 on Linux CI, where the POSIX umask assertion is not skipped)" is false as written and internally inconsistent (local is Linux). Fix: attribute the local skip to the console-script acceptance test, and note the umask skip as Windows-only. Non-blocking: AuditManifest.json records git.dirty=true (exported before commit) though artifact digests do match HEAD; consider a post-commit re-export.
- branch / merge: ceo/t-0017-close-m5-mark-the-board-done-and-export / pending

## T-0018 · Record the M5 fix and dependency bumps in the changelog  (ceo)
- date: 2026-10-19
- priority: P2
- owner: ceo role (work by: ceo)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] Re-read the two changelog hunks: the Fixed entry names the real failure mode and the test file, the Changed entry names the three pinned SHAs; no other file touched | test: pytest -q @715dd48 -> 355 passed, 1 skipped; links -> 0; privacy --tree -> PASS; gh pr checks 20 -> 17 pass
- author evidence: commit 715dd48
- reviewer evidence: @715dd48 independent re-verification: git diff --stat main...HEAD -> only CHANGELOG.md +10/-0 (two hunks, no deleted or changed line); Fixed entry re-checked against the merged fix 4cd8afc (diff 4cd8afc^1..4cd8afc: fnmatch-based pattern coverage, section-grouped headers appended only with a missing entry, empty file no longer rewritten with a leading blank line - old text was "\n"+entries) and the 5 tests in tests/unit/test_gitignore_bootstrap.py (empty repo, idempotent, glob-covered, partial section, no dangling header); Changed entry re-checked against .github/workflows/release.yml -> anchore/sbom-action@66cbf4bc # v0.24.3 (x2), actions/attest-build-provenance@4d101475 # v4, softprops/action-gh-release@efb35369 # v3, all four refs introduced by the single reviewed merge 9b56f1b (P-0008), and 28/28 uses: refs are 40-hex SHAs with 0 tag refs; Keep-a-Changelog shape intact - one ## [Unreleased] with a single ### Changed and single ### Fixed, entries under the existing headings, no duplicate heading, no trailing whitespace, no line >82 chars; python3 scripts/teamwork.py links -> 66 files / 321 links, issues 0; privacy_scan.py --tree -> PASS 0 findings; pytest -q -> 355 passed, 1 skipped; gh pr checks 20 @715dd48 -> 17 pass + "deploy to GitHub Pages" skipping, every required context green (CI run 39180346777, Docs+links/privacy run 39180346721); teamwork.py identity --audit --range main..HEAD -> 1 commit, CEO <ceo@agents.nidvue.com> author+committer = git config user.name/email, 0 problems; main == origin/main == ff419fa, branch 1 ahead / 0 behind, no newer remote change; gh issue list empty so there is no issue to link; no unrelated file in the diff
- findings history: -
- branch / merge: ceo/t-0018-record-the-m5-fix-and-dependency-bumps-i / pending

## T-0019 · Publish the closing audit manifest for the merged main  (ceo)
- date: 2026-10-19
- priority: P2
- owner: ceo role (work by: ceo)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] Re-read the diff: only the two generated manifest files; head 394c19b matches the reviewed merge, dirty=false, 210 records, every digest recomputed from a clean tree | test: ledger export @6cfebad -> 210 records, chain verified True, dirty False; links -> 0; privacy --tree -> PASS; pytest -q -> 355 passed, 1 skipped; gh pr checks 21 -> 17 pass
- author evidence: commit 6cfebad
- reviewer evidence: PASS @6cfebad independent re-verification. Scope: git diff --stat main...HEAD -> only docs/Team/AuditManifest.json (11 lines changed) and docs/Team/AuditManifest.md (5 changed), no source/test/build file; branch 1 ahead / 0 behind origin/main == main == 394c19b (fetched, no newer remote change); MERGEABLE. Data checks: manifest git.head = 394c19b18b9cb8f5c7b7befe7666b5976106a537 == git rev-parse main, git.branch = main, git.dirty = false, lfs_files 0; team_id 431b5b8b1bc04db58a4f13ef114cf5c1 == workspace TeamId (engine.team_identity); no absolute path (/home/, /Users/, /tmp/) in the file. Ledger: python3 scripts/teamwork.py ledger verify -> chain intact; independent recompute of all 217 records (sha256(prev+canon)) -> 0 chain problems; the manifest ledger.records=210 / head=20057b94f98dfc93197da41724cb009f9109d2e645c3c14f7cfc18b3d9fc1670 / verified=true / problems=[] match ledger record n=210 exactly (action ledger.export, ts 2026-10-19T02:27:12 == generated_at), so the stated checkpoint is self-consistent although the live ledger has since grown to 217. Artifacts: 5/5 sha256+bytes pairs recomputed from git show HEAD:<path> and from git show 394c19b:<path> -> all match (Architecture 10157, Archive 34499, Decisions 24155, Plan 4229, Project 10766); Archive.md is the only artifact whose digest moved vs the superseded export, matching the only committed team-doc change between 762fdb8 and 394c19b; 22/22 local_state entries present (Reviews.md and CEO/TaskQueue.md drifted at 02:30:09 after the 02:27:12 export - expected working-state drift, documented by the how_to_verify note). Markdown: every md field recomputed from the json -> generated/team/ledger/head/git/counts and all 5 table rows (path, bytes, sha256 prefix) match the json exactly, balanced code fences, no trailing whitespace. Gates @6cfebad: python3 scripts/teamwork.py links -> 0 issues; privacy_scan.py --tree -> PASS 0 findings; pytest -q -> 355 passed 1 skipped; gh pr checks 21 -> all 14 required contexts + Docs pass, only "deploy to GitHub Pages" skipping, every check_run head_sha = 6cfebad. Identity: git config user.name/email = CEO <ceo@agents.nidvue.com> = author = committer of 6cfebad; identity --audit --range main..HEAD -> 1 commit ok, 0 problems; message style chore(audit): matches history. Non-blocking: PR body claim "audit 0 problems / loop STOP" is a pre-review snapshot and now reports the expected pending-deliverable gates; the generator artifact list still omits Board.md/Risks.md/Release.md/CHANGELOG.md (pre-existing T-0010 scope, unchanged by this diff); docs/Team/Plan.md and Board.md still show T-0017 in flight at main 4cd8afc - pre-existing governance staleness already recorded on T-0016/T-0017 reviews, not introduced here and not affecting manifest correctness (the manifest records their true digests).
- findings history: -
- branch / merge: ceo/t-0019-publish-the-closing-audit-manifest-for-t / pending

## T-0020 · Structured evidence packets and the repro-first gate  (ceo)
- date: 2026-10-19
- priority: P1
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: evidence
- self-check: [pass] Re-read the diff: artifact_digest resolves inside project_of(root), hashes 16 hex chars + byte size, refuses missing/outside paths; tests repro validates both sides, distinct revisions, fail/pass wording and git ancestry; selfcheck bug gate reads kind=bug and accepts a record matched by area or task id; review stores review_artifacts and appends it to review_evidence; records.py allowlist extended so kind and the two artifact fields survive a roundtrip. | test: pytest -q @8694073 -> 375 passed, 1 skipped; ruff check + ruff format --check -> clean; mypy src/teamwork -> no issues; teamwork selftest @8694073 -> 5/5; teamwork links -> 0 issues | artifacts: docs/Team/Research.md:7c526a5c01425c53:12805 | replay: python -m pytest tests/unit/test_evidence_packets.py tests/integration/test_evidence_flow.py -q || [pass] Re-read the review finding and the fix: every new flag is now in docs/guide/cli.md (tests repro section, packet flags on run/selfcheck/review, --bug on task add); review hashes artifacts inside the pass branch only, so a failing review no longer needs an artifact; the audit finding has an integration test that force-passes a bug task and asserts audit reports it. Deleted the reviewer's stray Reports/ probe files (untracked scratch) so the hygiene test is green. | test: pytest -q @1d6a9aa -> 376 passed, 1 skipped; ruff check + format --check -> clean; mypy src/teamwork -> no issues; teamwork links @1d6a9aa -> 0 issues; review-fix diff main...HEAD -> 4 files | artifacts: docs/guide/cli.md:69cacee4f8fdc3fb:20332 | replay: python -m pytest tests/integration/test_evidence_flow.py -q
- author evidence: commit 1377dbd; commit b2eb99a
- reviewer evidence: Re-reviewed P-0013 from scratch at 1d6a9aa (main e8da9ce...1d6a9aa, 14 files). Round-1 blocker closed: cli.md now matches --help for tests {+repro}, tests run --baseline/--artifact/--replay, task add --bug, review --artifact, selfcheck --baseline/--artifact/--replay, and a scripted cross-check finds 0 undocumented flags. Round-1 non-blocking a) fixed (review hashes artifacts inside the pass branch only: review --result fail --artifact Reports/does-not-exist.log -> exit 0, review_status=failed) and b) fixed (test_audit_reports_a_bug_task_closed_without_a_repro). Behaviour probes in .pi/worktrees/reviewer/probe/proj: missing/dir/../traversal//etc/symlink artifacts all refused; repro refuses same rev, reversed and unknown ancestry, non-failing pre, non-passing post, wrong layer owner, unknown record; repro accepted with a correct ancestor pair and both digests in the ledger; --bug self-check refused (exit 2) then accepted after the repro record; non-bug task not gated; old Tests.md/TaskQueue.md (new fields stripped) still drive list/plan/queue/audit/loop. @1d6a9aa: pytest -q -> 376 passed, 1 skipped; ruff check . -> passed; ruff format --check . -> 111 formatted; mypy src/teamwork -> 14 files, no issues; links -> 0; identity --audit main..HEAD -> 2 commits 0 problems (CEO <ceo@agents.nidvue.com>); selftest -> 5/5; ledger verify -> 230 records chain intact; privacy_scan --tree --history -> PASS; mkdocs build --strict -> exit 0 no warnings; verify_release -> OK. NON-BLOCKING, follow-up: i) references/Evidence.md says tests run/selfcheck/review all record baseline+replay, but review accepts only --evidence/--artifact (review --baseline -> unrecognized arguments); ii) tests repro accepts --artifact but not --baseline/--replay; iii) repro_records_for also matches on the task area, so one repro record satisfies other bug tasks in that area (probe: area=parser task passed the gate on an unrelated parser repro); iv) review --result fail --artifact <existing file> is silently ignored; v) Decisions.md D-20261019-CEO-3 evidence is bound to '@working-tree', not a revision. PROCESS: no tests record exists for the new area 'evidence', so audit reports coverage gap evidence/unit|integration|acceptance and loop blocks STOP - unit/integration records are Developer-1/Tester-1 work. | artifacts: .pi/worktrees/reviewer/Artifacts/P-0013-review-1d6a9aa.txt:3c02a4e31ea42b23:7280, docs/guide/cli.md:69cacee4f8fdc3fb:20332
- findings history: BLOCKING (docs do not match the shipped CLI surface) - docs/guide/cli.md was not touched by 8694073, so the published reference now contradicts the code and the doc surfaces that index it: 1) docs/guide/cli.md:377 `teamwork tests {add,run,require,rm,plan,list} ...` omits `repro`; there is no `#### tests repro` section. Evidence @8694073: `python3 scripts/teamwork.py tests repro --help` -> exit 0, positional ID + --by/--pre-rev/--pre-evidence/--post-rev/--post-evidence/--artifact/--force; my probe: `# TS-0001 unit/parser repro proved: fail @1559fd5 -> pass @add7dea`. 2) cli.md:394 `tests run ID --by BY --result {pass,fail} --evidence EVIDENCE [--rev REV] [--command COMMAND] [--force REASON]` omits the new packet flags. Evidence: `tests run --help` -> "[--baseline BASELINE] [--artifact PATH] [--replay REPLAY] [--force REASON]". 3) cli.md:119-123 `task add` synopsis + options table omit `--bug`. Evidence: `task add --help` -> "[--bug] [--evidence EVIDENCE]"; probe wrote `- kind: bug` (proj2 TaskQueue.md:18). 4) cli.md:438-441 `review` omits `--artifact`. Evidence: `review --help` -> "[--evidence EVIDENCE] [--artifact PATH]". 5) cli.md:450-452 `selfcheck` omits `--baseline/--artifact/--replay`. Evidence: `selfcheck --help` -> "[--baseline BASELINE] [--artifact PATH] [--replay REPLAY]". Why it matters: the page header (cli.md:7) says "Every option below was produced from `teamwork <cmd> --help`" and docs/index.md:82 advertises "Every command, subcommand, flag and exit code", while AGENTS.md/templates/AGENTS.md/SKILL.md/references/Evidence.md/references/Testing.md/CHANGELOG.md now document flags this page does not list. Repo precedent: the T-0003 review-note fix (commit 1e646a9) added `--strict-authors` to this same page, so a new flag landing without it regresses an already-closed finding. The roster has no Technical Writer instance (Agents/: CEO, Developer-1, Reviewer-1, Tester-1), so the update is the author's. Fix: add the `repro` entry to cli.md:374-430 and the missing flags to the four synopses/option tables; no code change is required. NON-BLOCKING (fix in the same pass if cheap): a) engine.py:5650 `artifacts = artifact_digests(...)` runs before the pass/fail split, so `review --result fail --artifact Reports/does-not-exist.log` exits 1 "artifact not found" instead of recording the fail (probe proj3), and on a fail the hashed value is discarded. Move it inside the `if args.result == "pass"` branch. b) `_audit_bug_fixes_without_a_repro_record` (engine.py:6235) has no automated test (`grep -rn "defect fixes without|_audit_bug_fixes|repro_records_for" tests/` -> 0 hits); only my manual probe exercised it (`audit` -> "- developer T-0002: flaky ui bug (review) has no `tests repro` record"). Add a unit test. c) `repro_records_for` (engine.py:1468) also matches on the task *area*, so one repro record satisfies every bug task sharing that area; the audit gate inherits the looseness. Consider task-id-only matching. d) The `--force` escape and the audit disagree: a bug task self-checked with `--force 'cannot reproduce: no logs'` is accepted (probe proj2, exit 0) yet `audit` still reports it as "the defect was never shown to fail first" forever, because the audit ignores `forced`. VERIFIED GREEN on 8694073 (no action needed): `.venv/bin/python -m pytest -q` -> 375 passed, 1 skipped; `ruff check src tests scripts` -> all checks passed; `ruff format --check src tests scripts` -> 45 files formatted; `mypy src/teamwork` -> success, 14 files; `selftest` -> 5/5; `links` -> 0 issues; `identity --audit --range main..HEAD` -> 1 commit, 0 problems; `ledger verify` -> 227 records, chain intact; `privacy_scan --tree` -> PASS 0 findings; `mkdocs build --strict` -> built in 0.19s. Behaviour probes: artifact outside project refused ("artifact outside the project", exit 1, incl. `../outside.log` traversal), missing artifact refused, repro refused for same revision / reversed ancestry ("--pre-rev 4fa6b5e is not an ancestor of --post-rev 6e0d59e") / unknown revision, repro accepted with a correct ancestor pair and digests recorded in Ledger.jsonl ("artifacts: Reports/pre.log:70a5500d81dcdf60:18, Reports/post.log:d367a494a1f42c20:10"); bug-task self-check refused with exit 2 and accepted after the repro record (status -> review, self_check -> passed); non-bug task not gated; pre-change Tests.md/TaskQueue.md (new fields stripped) still parse and drive `tests list`/`task list`/`review pass`/`audit`/selfcheck gate. Commit identity: repo-local identity CEO <ceo@agents.nidvue.com> == author == committer, `Acting role: CEO` trailer present, message style matches history.
- branch / merge: ceo/t-0020-structured-evidence-packets-and-the-repr / pending

## T-0021 · Review parity: --baseline and --replay on the Reviewer verdict  (ceo)
- date: 2026-10-19
- priority: P2
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: evidence
- self-check: [pass] Re-read the diff: review now takes --baseline/--replay and appends them to review_evidence only on a pass, matching tests run and selfcheck; cli.md lists the flags; the new integration test asserts both tokens in the stored verdict. | test: pytest -q @58dc20c -> 377 passed, 1 skipped; ruff check + format --check -> clean; mypy -> no issues; links -> 0 | replay: python -m pytest tests/integration/test_evidence_flow.py -q
- author evidence: commit 58dc20c
- reviewer evidence: Reviewed main...d7bbf33 (4 files; 58dc20c->d7bbf33 is metadata-only, git diff empty) on 2026-10-19. pytest -q @d7bbf33 -> 377 passed, 1 skipped; ruff check . -> passed; ruff format --check . -> 111 files formatted; mypy src/teamwork -> 14 files, no issues; links -> 0; identity --audit main..HEAD -> 1 commit 0 problems; audit -> only the open-work gates (T-0021 awaiting review, branch unmerged); selftest -> 5/5; ledger verify -> 248 records chain intact; privacy_scan --tree -> PASS; mkdocs build --strict -> exit 0. Probes (throwaway project, deleted): review --result pass --evidence ... --baseline 'empty cache' --replay 'pytest -q' -> review_evidence='pytest @abc123 -> 3 passed | baseline: empty cache | replay: pytest -q'; + --artifact Reports/run.log -> '... | artifacts: Reports/run.log:7b01e2c3e1d34295:9 | baseline: ... | replay: ...' (hashing still inside the pass branch); review --result fail --baseline B --replay R --artifact Reports/run.log --findings 'defect x' -> exit 0, status=doing, review_status=failed, review_evidence empty, review_artifacts empty, findings only (fail behaviour unchanged); pass without --evidence still refused ('a pass needs the REVIEWER own evidence'). Docs: scripted cross-check of review --help flags vs docs/guide/cli.md review section -> 0 missing (only global --project/--team/--help, documented once globally). P-0013 note (i) closed; P-0013 non-blocking a) and b) still fixed; notes (iii)+(b) tracked as T-0022, (v) as T-0023.
- findings history: -
- branch / merge: ceo/t-0021-review-parity-baseline-and-replay-on-the / pending

## T-0024 · Extract the CEO audit close-out flow as a team skill  (ceo)
- date: 2026-10-19
- priority: P2
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] Re-read the skill: it names the exact gate commands in order, requires a clean tree and a merged revision, exports the manifest last, sends it through the normal PR gate, and lists the five failure modes we actually hit (stale todo tasks, forced overrides, manifest head drift, dirty export, digest mismatch). It states it cannot replace AGENTS.md or bypass a gate. | test: python3 scripts/teamwork.py links @453475f -> 0 issues; skill create @453475f -> S-0001; skill share -> status shared | replay: python3 scripts/teamwork.py skill candidates || [pass] Re-read the skill against the engine: every command is a real teamwork.py invocation (no placeholder), and the manifest rows now state the invariant the export actually satisfies - head recorded at export, ancestor of the commit carrying it, stale after any later merge. Verified against a real manifest: git.head 394c19b is an ancestor of its commit. | test: python3 scripts/teamwork.py links @443339f -> 0 issues; grep '<script>' .agents/skills/ceo-audit-close/SKILL.md -> 0 hits | replay: git log -1 --format=%H -- docs/Team/AuditManifest.json
- author evidence: commit 53932ec; commit f15517b
- reviewer evidence: Re-reviewed P-0016 from scratch at 443339f. BLOCKING closed: step 2 now uses real teamwork.py invocations (ledger verify/loop/audit/links/tests plan - all exist in teamwork.py --help) and the '<script>' placeholder is gone (grep -> 0 hits); the manifest invariant now states head recorded at export, ancestor of the commit carrying it, stale after any later merge. Verified against the real docs/Team/AuditManifest.json: git.head=394c19b is an ancestor of e8da9ce, the commit that carries it (git merge-base --is-ancestor -> exit 0), and engine.ledger_export records git.head=rev-parse HEAD at export time (engine.py:2500-2515), which is why equality was unsatisfiable; both new failure rows are consistent with that. No gate bypass: step 5 + guardrails still require branch, self-check, PR and Reviewer-only merge, and state the skill never replaces AGENTS.md or weakens a test layer @443339f: python3 scripts/teamwork.py links -> # issues: 0; skill list -> S-0001 ceo-audit-close [shared] owner=ceo file=ok; identity --audit --range main..HEAD -> 2 commits, 0 problems (author==committer==CEO <ceo@agents.nidvue.com> == git config); diff main...HEAD is one file, .agents/skills/ceo-audit-close/SKILL.md
- findings history: BLOCKING - the failure-mode row in .agents/skills/ceo-audit-close/SKILL.md ("manifest head != `git rev-parse HEAD` -> the export predates the merge; regenerate") describes a condition that can never be satisfied, so the skill tells every close-out to loop forever. `ledger export` records `git.head = rev-parse HEAD` at export time (engine.py:2504-2515) and writes the manifest, which is then committed in a later commit (step 5 of the same skill), so the recorded head is always an ancestor of the commit that carries the manifest. Evidence from this repository: the commit that first added the manifest, 384df6a (parent a531fb8), carries `docs/Team/AuditManifest.json` with `git.head = a531fb8` = its own parent; today the committed manifest says `git.head = 394c19b` while `git rev-parse main` = 2297adc, and `git merge-base --is-ancestor 394c19b main` succeeds. Following the row, the CEO must "regenerate", which reproduces the same one-commit offset on every attempt - an unsatisfiable gate in a skill whose whole value is that its steps are exact. `audit` does not check this either (engine.py:6467-6484 only compares the recorded ledger record count against the current count), so the row is also not engine-derived behaviour. Fix: state the invariant that actually holds - the manifest `git.head` must be the reviewed milestone merge and an ancestor of the current HEAD (`git merge-base --is-ancestor <manifest.git.head> HEAD`), never equality - and drop "regenerate" or scope it to "the export predates the milestone merge" with that ancestor test. Re-check step 4/6 wording at the same time so "export last" and this check do not contradict each other. NON-BLOCKING - `SKILL.md` step 2 uses an undefined `<script>` placeholder (`<script> ledger verify`); the rest of the repository's agent-facing commands spell it `python3 $S ...` (SKILL.md:606-609) or `teamwork.py ...`. Pick one so the copied commands run. VERIFIED @453475f (no action needed): `python3 scripts/teamwork.py links` -> "# issues: 0"; `skill list` -> "S-0001 ceo-audit-close [shared] owner=ceo file=ok" and the description matches the committed file; the file is committed on the branch (79 added lines, nothing else); frontmatter is the generator's shape (`name` kebab-case matching the directory, one-line quoted `description`, `# <name>`, owner line, "Use this skill when"); every command in the ordered steps exists and does what the step says (`ledger verify`, `loop` STOP gate, `audit` with its forced-override / ownership / duplicates / LFS / link-health sections, `links`, `tests plan` with `GAP` lines, `ledger export` writing `AuditManifest.json` + `AuditManifest.md` with head, record count, team id and artifact digests - engine.py:2462-2600); the other four failure-mode rows match engine behaviour (loop continues on queued work, audit prints forced overrides, `dirty` is captured, artifact digests are sha256); no gate bypass and no contradiction with AGENTS.md/SKILL.md - step 5 and the guardrails require branch + self-check + PR + Reviewer-only merge and say the skill never replaces AGENTS.md or weakens a test layer; identity --audit --range main..HEAD -> 1 commit, 0 problems (author==committer==CEO <ceo@agents.nidvue.com> == repo config); commit body has the fixed shape + `Acting role: CEO`.
- branch / merge: ceo/t-0024-extract-the-ceo-audit-close-out-flow-as / pending

## T-0025 · Fix the root-hygiene allowlist for the tracked .agents skill directory (P-0016 post-merge)  (ceo)
- date: 2026-10-19
- priority: P0
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: test
- self-check: [pass] Re-read: .agents is required project output (team skills live in .agents/skills/<name>/SKILL.md) and is tracked, so the allowlist was the defect, not the directory. The allowlist stays an allowlist; nothing else was loosened and the test still fails on untracked debris. Included the Reviewer's fix-forward decision record. | test: pytest -q @a4ead34 -> 377 passed, 1 skipped | replay: python -m pytest tests/unit/test_hygiene.py -q
- author evidence: pytest -q @b662faf (main) -> 1 failed, 376 passed, 1 skipped: tests/unit/test_hygiene.py::test_repository_root_contains_only_expected_entries -> unexpected entries in the repository root: ['.agents']; git ls-files .agents -> .agents/skills/ceo-audit-close/SKILL.md (tracked), git check-ignore .agents -> exit 1; commit 9f92bac
- reviewer evidence: Re-reviewed P-0017 from scratch at a4ead34 (tree-identical to ledger commit 9f92bac). Repro real: pytest -q @b662faf -> 1 failed, 376 passed (unexpected ['.agents']); pytest -q @a4ead34 -> 377 passed, 1 skipped. .agents/skills/ceo-audit-close/SKILL.md tracked; allowlist adds only .agents; probe: untracked root dir -> test fails (still strict). ruff check -> passed; ruff format --check -> 112 files; mypy src/teamwork -> no issues; lines -> 0; identity b662faf..a4ead34 -> 1 commit, 0 problems (CEO <ceo@agents.nidvue.com> == git config). T-0025 kind=bug: gate at this rev reads test records; TS-0011 task=T-0025 repro pre @b662faf -> 1 failed | post @a4ead34 -> 377 passed. Diff 2 files, no scope creep.
- findings history: -
- branch / merge: ceo/t-0025-fix-the-root-hygiene-allowlist-for-the-t / pending

## T-0022 · Tighten repro matching and cover the audit gate  (ceo)
- date: 2026-10-19
- priority: P3
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: evidence
- self-check: [pass] Re-read the matcher and the four new tests: a record naming the task wins; a record naming another task never matches; the area fallback requires an empty task field; another area is ignored. The P-0013 probe (area-only repro satisfying an unrelated bug task) is now the failing case covered by test_repro_for_a_sibling_bug_does_not_satisfy_the_task. | test: pytest -q @767d8cb -> 381 passed, 1 skipped; ruff check + format --check -> clean; mypy -> no issues | replay: python -m pytest tests/unit/test_evidence_packets.py -q || [pass] Re-read the refactor: tests repro resolves T-id across queues via the existing _find_task_anywhere, re-reads the task under the role lock before writing, and stores repro/repro_artifacts/repro_by on the task; the self-check gate and audit read t['repro']; the test-record repro field and the area fallback are gone, so a sibling bug cannot inherit proof. The reviewer's probe (one area record satisfying T-0002/T-0003/T-0009) now has no matching path at all; new tests cover unknown task, single revision, non-failing pre-run and the gate refusing then accepting. | test: pytest -q @8ad5825 -> 380 passed, 1 skipped; ruff check + format --check -> clean; mypy -> no issues; links -> 0 | replay: python -m pytest tests/integration/test_evidence_flow.py -q || [pass] Re-read: matching_tasks returns every queue hit, and tests repro dies with the queue list instead of taking the first; --role narrows through resolve_role; the task list now prints the repro line so references/Evidence.md is true; tests cover duplicate ids, the role hint, the CLI refusal and the explicit-role success. | test: pytest -q @e2787b7 -> 383 passed, 1 skipped; ruff/format/mypy clean; links 0 | replay: python -m pytest tests/integration/test_evidence_flow.py -q
- author evidence: commit 0fd74e8; commit 8ad5825; commit fd596b0
- reviewer evidence: Re-reviewed P-0015 from scratch at branch HEAD e2787b7 (tree-identical to the task's fd596b0; git diff empty). Round-2 blocker CLOSED, own probe on a throwaway team (ProbeProject, deleted): ceo+developer both hold a --bug T-0001; bare 'tests repro T-0001' -> exit 1, "'T-0001' exists on 2 queues (ceo, developer)... name the defect's owner with --role", both queues' repro stayed empty; 'tests repro T-0001 --role developer' -> exit 0, developer repro set, ceo untouched; '--role reviewer' (no id) -> 'no task T-0001 in any role queue'. task list now prints 'repro: pre @... | post @...' (references/Evidence.md claim true). Unknown T-4040 refused (no ledger event); bug gate refused then accepted after the repro; audit prints '- tester T-0001: fixture leak (review) has no tests repro record'; legacy Tests.md '- repro:' line still parses and lists (TS-0099). Docs cross-check: references/Evidence.md, references/Testing.md, docs/guide/cli.md, AGENTS.md, templates/AGENTS.md, SKILL.md, CHANGELOG all teach the task-keyed form; cli.md synopsis matches 'tests repro --help' (TASK + --role + --artifact + --force). @e2787b7: pytest -q -> 383 passed, 1 skipped; ruff check -> passed; ruff format --check -> 111 files; mypy src/teamwork -> no issues; links -> 0; identity main..e2787b7 -> 3 commits, 0 problems (CEO <ceo@agents.nidvue.com> == git config); merge-tree main/e2787b7 clean. Diff 11 files, all in scope, no weakened tests.
- findings history: BLOCKING 1 - the tightening is opt-in, so the P-0013 (iii) hole is still reachable through the documented workflow. src/teamwork/engine.py:1474-1477 treats an empty `task` field as "legacy" and falls back to area matching, but `tests add` does not require `--task` and no team doc tells an author to pass it (references/Testing.md:66 `tests add --layer unit --area auth --command ...`, SKILL.md:606 same, docs/guide/cli.md:383 lists `--task` in the synopsis only). Probe @767d8cb (throwaway team root, deleted): one record written the documented way (`new_test_record("unit","parser")`, no task) + `repro` set -> `repro_records_for` returns it for T-0002, T-0003 AND T-0009 (all `-> ['(no task)']`). So one repro for bug A still satisfies every sibling bug in the area, which is exactly what the commit message claims is fixed ("One repro for one bug must not satisfy a sibling bug in the same area") and what AGENTS.md requires ("a defect is proved before it is fixed"). The new test test_area_level_repro_covers_a_task_without_an_id_link pins the loophole as intended behaviour. Minimal fix options: (a) refuse `tests repro` on a record whose area holds a `kind: bug` task unless the record names the task, or make `tests add` require `--task` when such a task exists; (b) if genuinely-legacy records must keep working, mark them explicitly (e.g. `legacy: true`) instead of inferring legacy from an empty field; either way document the rule in references/Evidence.md and references/Testing.md so the documented flow produces a task-linked record. BLOCKING 2 - docs not updated for the new semantics: references/Evidence.md:55-68 documents the defect-fix repro without saying the record must name the task, docs/guide/cli.md:394 `tests repro` likewise; a reader following the docs gets the weaker gate from finding 1. AGENTS.md "Documentation and wiki updates are complete" applies. NON-BLOCKING - task evidence handle is stale: `.pi/.../Roles/CEO/TaskQueue.md` T-0022 `evidence: commit 0fd74e8` while the branch head is 767d8cb (`git diff 0fd74e8 767d8cb` -> empty, trees identical, so the evidence stands; the self_note correctly cites @767d8cb). Re-point the handle after the rework. VERIFIED GREEN @767d8cb (no action needed): PYTHONPATH=src pytest -q -> 381 passed, 1 skipped; ruff check . -> All checks passed; ruff format --check . -> 111 files already formatted; mypy src/teamwork -> Success, 14 files; targeted 4 new unit tests + tests/integration/test_evidence_flow.py -> 13 passed (incl. test_bug_task_cannot_self_check_without_a_repro_record: gate refuses without a repro, accepts a record added with `--task T-0001`); identity --audit --range main..HEAD -> 1 commit, 0 problems (author==committer==CEO <ceo@agents.nidvue.com>, matches repo config); commit body carries the fixed shape + `Acting role: CEO`; diff is 2 files, no scope creep, no weakened tests. The matcher logic itself is correct for records that DO name a task: named record wins, sibling task-id never matches, other area ignored. | BLOCKING (cross-queue id collision) - tests repro resolves a bare T-id across every role queue by first match, but task ids are allocated per queue (records.assign_ids keeps ids unique only inside one queue), so a colliding id silently records the proof on the wrong task. Probe @3392255 (throwaway team 'Probe' under .pi/worktrees/reviewer, deleted): task add ceo 'ceo bug' --bug -> CEO T-0001; task add developer 'bug in parser' --bug -> Developer T-0001. tests repro T-0001 --by developer-1 --pre-rev d7f667e --pre-evidence 'pytest -> 2 failed' --post-rev d416c25 --post-evidence 'pytest -> 5 passed' -> exit 0 and the proof landed on Roles/CEO/TaskQueue.md T-0001 (repro: pre @d7f667e -> pytest -> 2 failed | post @d416c25 -> pytest -> 5 passed), while the Developer T-0001 kept only its earlier value; _find_task_anywhere (engine.py:627-636) returns the first role in sorted(list_roles) that has the handle, and validate_actor's role is thrown away (_arole). Why it matters: in this repository the CEO queue already holds T-0001..T-0024, so every new Developer/Tester bug task (ids start at T-0001) collides; the defect being fixed gets no proof while an unrelated task silently gains a false one, and _audit_bug_fixes_without_a_repro_record then stops reporting that unrelated task. The new test test_find_task_anywhere_finds_the_owning_queue (tests/unit/test_evidence_packets.py:210) writes the same T-0001 into two queues and asserts the silent first match, so this is pinned as intended rather than caught. Fix: disambiguate like task/selfcheck do - accept the owning role/agent (or refuse when the handle exists on more than one queue and print the candidates); add a test for the duplicate case. NON-BLOCKING 1 - references/Evidence.md:67 'task list shows the repro line' is false: task list prints id/priority/status/title/deps/shared/area/evidence/body only (engine._print_task, engine.py:4112-4121), never the repro field (probe output shows no repro line). Fix the pointer (TaskQueue.md or the task fields). NON-BLOCKING 2 - stale evidence handles: Roles/CEO/TaskQueue.md T-0022 evidence cites commit 0fd74e8, 8ad5825 while the branch head is 3392255 (git diff 8ad5825 3392255 -> empty, same tree, so the evidence stands); re-point after the rework. NON-BLOCKING 3 - the retired test-record field is dropped on parse: parse_tests keeps only keys present in new_test_record (records.py:373), so a legacy '- repro: ...' value no longer round-trips (it parses, the record lists, and the live Tests.md has only empty repro values, so nothing is lost today - accepted limitation for the retired field). VERIFIED GREEN @3392255 (no action needed): .venv/bin/python -m pytest -q -> 380 passed, 1 skipped; ruff check . -> All checks passed; ruff format --check . -> 111 files already formatted; mypy src/teamwork -> Success, 14 files; teamwork.py links -> # issues: 0; commit identity author==committer==CEO <ceo@agents.nidvue.com> == git config for 767d8cb and 3392255, commit body carries the fixed shape + 'Acting role: CEO'. The P-0013 loophole itself is closed: a repro for T-0001 does not satisfy T-0002 or T-0003 (selfcheck refused with exit 1 for both), selfcheck T-0002 refused then accepted after its own repro, tests repro T-0099 -> 'no task T-0099 in any role queue', audit reports '- developer T-0003: bug in parser third (done) has no tests repro record', old Tests.md with a '- repro:' line still parses and lists. Docs AGENTS.md, templates/AGENTS.md, SKILL.md, references/Evidence.md, references/Testing.md, docs/guide/cli.md, CHANGELOG.md teach the task-keyed form and cli.md matches tests repro --help except the task-list pointer above.
- branch / merge: ceo/t-0022-tighten-repro-matching-and-cover-the-aud / pending

## T-0023 · Bind the D-20261019-CEO-3 evidence to the merged revision  (ceo)
- date: 2026-10-19
- priority: P3
- owner: ceo role (work by: CEO)
- reviewer: Reviewer-1
- task / issue: -
- area: audit
- self-check: [pass] Re-read both artifacts: D-20261019-CEO-6 cites the merged revision 3934690 and the five tasks it closes, and the manifest was exported on a committed tree (dirty=false) with head 5dbc573, which is an ancestor of the commit carrying it - the invariant the close-out skill states. | test: pytest -q @8d6aeb2 -> 383 passed, 1 skipped; ledger export @8d6aeb2 -> 307 records, chain verified True; links @8d6aeb2 -> 0 | artifacts: docs/Team/AuditManifest.json:3f1957b4bc2246dd:6111 | replay: python3 scripts/teamwork.py ledger verify || [pass] Re-read both docs against the records: the snapshot numbers are the ones I measured on 3934690 (383 passed, 1 skipped, 67.52% coverage), the manifest counts come from the export I ran, M6 lists T-0020..T-0025 with their merge commits, and T-0017 is now marked done because e8da9ce merged it. | test: pytest -q @9fd26c5 -> 383 passed, 1 skipped; links -> 0; coverage 67.52% | artifacts: docs/Team/Board.md:c16a1d4db666eb07:3603 | replay: python3 scripts/teamwork.py board || [pass] Re-read: the manifest is exported on the committed tree, its head 9fd26c5 is the parent of the commit that carries it, and I recomputed every artifact digest against the working tree - zero stale. This supersedes the earlier export that pinned Plan.md before the M6 table. | test: pytest -q @44f6107 -> 383 passed, 1 skipped; ledger export @44f6107 -> 313 records, chain verified; recomputed digests -> 0 stale; links -> 0 | artifacts: docs/Team/AuditManifest.json:56b8c3c1d0f12dcf:6111 | replay: python3 scripts/teamwork.py ledger verify || [pass] Re-read: the archive is append-only and gains the entry for this deliverable at review time, so any digest committed beside it is stale by construction; it is now excluded with the reason recorded in how_to_verify, and the other four artifacts plus the ledger head still verify. Re-exported after the change: 316 records, every pinned digest recomputed clean. | test: pytest -q @b82a08d -> 384 passed, 1 skipped; ledger export @b82a08d -> 316 records, 0 stale; links -> 0 | artifacts: docs/Team/AuditManifest.json:c475950ce8f12c80:6100 | replay: sha256sum -c <(jq -r '.artifacts[] | "\(.sha256) \(.path)"' docs/Team/AuditManifest.json) || [pass] Re-read every review finding against the tree: the manifest is exported from a clean tree at ab26dc2 (dirty false, 324 records, 4 artifacts, 0 stale), D-CEO-3 is marked superseded with a pointer, D-CEO-6 cites e8da9ce..3934690 which contains all five merges, Plan names ff419fa for T-0017, and Board no longer claims pre-merge audit results. The duplicate test command is gone (TS-0012 now runs the hygiene test alone) and T-0025 carries its repro on the task. | test: pytest -q @b827d47 -> 384 passed, 1 skipped; ledger export @b827d47 -> 324 records, dirty False, 0 stale; links -> 0; grep 'status: superseded' Decisions.md -> 1 | artifacts: docs/Team/AuditManifest.json:b590568b21482ba3:6101 | replay: python3 scripts/teamwork.py ledger verify
- author evidence: commit 3bccc14; commit a0f46f5; commit 5e1bea1; commit ed9ed06; commit ff3d31d; commit 417b10e; commit 910cd6e
- reviewer evidence: RE-REVIEW @b827d47 (branch head; tree 3ab6016c == the ledger-recorded 910cd6e, an amend with no content change). All five round-1 blockers verified fixed. (1) Dirty export: manifest git.dirty=false, git.head=ab26dc2 (parent of the carrying commit b827d47, git merge-base --is-ancestor -> exit 0), ledger.records=324, verified=true, problems=[]; record #324 hash 00f8834f4654... == manifest ledger.head and its action=ledger.export ts 13:50:28 == generated_at -> self-consistent; sha256sum -c <(jq -r ".artifacts[] | \(.sha256)  \(.path)") -> 4/4 OK (Architecture 10157, Decisions 27266, Plan 5459, Project 10766) and the digests equal git show ab26dc2:<path> for all four. (2) Board no longer claims pre-merge gates: Board.md:17-21 now says "audit -> 0 problems and loop -> STOP once P-0018 merges" with no record count; audit @HEAD -> 4 problems, all of which are the merge-closing ones (1 deliverable awaiting review, 1 task not finished, 1 branch unmerged) + the review row itself; the two non-gate problems I raised are gone: audit "## layered tests" -> none (TS-0012 command is now .venv/bin/python -m pytest tests/unit/test_hygiene.py -q, no longer the TS-0011 duplicate) and audit "## defect fixes without a fail -> pass repro" -> none (task list ceo T-0025 carries repro: pre @b662faf -> 1 failed, 376 passed | post @a4ead34 -> 377 passed, 1 skipped). (3) Plan.md:34 T-0017 evidence = "merge ff419fa"; git log -1 ff419fa -> "chore(merge): merge of ceo/t-0017-close-m5-mark-the-board-done-and-export", ancestor of main. (4) Decisions.md D-20261019-CEO-6 evidence cites git log e8da9ce..3934690; I ran it -> exactly 5 merges 3934690 (T-0022), d72f44b (T-0025), b662faf (T-0024), 2297adc (T-0021), 9d59976 (T-0020), matching the text. (5) D-20261019-CEO-3 status = "superseded by D-20261019-CEO-6 (evidence re-bound to the merged revision)" and D-CEO-6 names D-CEO-20261019-CEO-3 back -> bidirectional. EXPORT CHANGE (b82a08d): narrow - engine.py excludes exactly archive_path(root) plus a 3-line comment, how_to_verify states the reason, and test_ledger_export_does_not_pin_the_append_only_archive asserts Archive absent / Project+Decisions present at CLI level (would fail on the pre-fix engine); Archive.md is the only docs/Team file pr merge/review appends (engine.py:900-955), so no other pinned artifact can drift at merge; its drift is not merely hidden - provenance stays in the hash chain via trace. GATES @b827d47: pytest -q -> 384 passed, 1 skipped (skip tests/acceptance/test_entrypoints.py:90 console script); ruff check . -> All checks passed; ruff format --check . -> 112 files already formatted; mypy src/teamwork -> no issues in 14 source files; teamwork.py links -> # issues: 0; privacy_scan.py --tree -> PASS 0 findings; identity --audit --range main..HEAD -> 7 commits, author AND committer CEO <ceo@agents.nidvue.com> == git config, 0 problems; ledger verify -> 326 records, chain intact, head 255918f2; git diff --check -> clean; git rev-list --left-right --count main...HEAD -> 0 7 (no newer main, merge-tree 0 conflicts). NON-BLOCKING: (a) the branch head was amended after the self-check again - the ledger records commit 910cd6e while the tip is b827d47 (trees identical, so evidence stands); keep the ledger SHA equal to the reviewed head. (b) 7 commits for one P3 record instead of one. (c) PR body / Reviews.md still say "307 records" (P-0018 was opened at the 8d6aeb2 export); the manifest says 324. (d) references/Audit.md:69 still says the manifest carries "a sha256 digest for every state artifact" and that committed docs/Team output is split only into artifacts vs local_state - Archive.md is now in neither list; the exclusion is explained in the manifest how_to_verify but not in that reference doc or the CHANGELOG Unreleased section. (e) local_state CEO/TaskQueue.md has drifted since the export (expected working-state drift, documented). All five previously-blocking findings are closed; no evidence-bearing churn requested. | artifacts: docs/Team/AuditManifest.json:b590568b21482ba3:6101
- findings history: FAIL @b82a08d (branch head; tree-identical to the ledger-recorded ff3d31d). BLOCKING 1 - the published manifest is a dirty-tree export: docs/Team/AuditManifest.json head = git.dirty true, git.head 44f6107, ledger.records 316, while Board.md:21 claims "(307 records, chain verified, dirty: false)" and the task deliverable requires dirty:false. Evidence: jq -> git.dirty true, git.head 44f6107d7edf (parent of the carrying commit b82a08d), generated_at 2026-10-19T13:47:13 = the export ran while src/teamwork/engine.py and tests/integration/test_command_surface.py were still uncommitted for b82a08d. A verifier cannot tell which tree the digests describe. Precedent: T-0017 round 2 was failed for exactly this and fixed by re-exporting from a clean tree. Fix: commit the engine/test change first, re-run ledger export on the clean tree, commit the manifest as its own chore(audit) commit. BLOCKING 2 - Board.md:17-19 "Gate: teamwork.py loop -> STOP and teamwork.py audit -> 0 problems once P-0018 lands" is not reproducible and is false after the merge: python3 scripts/teamwork.py audit @b82a08d -> "# problems found: 6"; 3 are the completion-gate blockers that clear with the merge, but 2 are not gates at all and survive it - "## layered tests ... TS-0011(goal), TS-0012(goal) -> python -m pytest -q (duplicate testing)" and "## defect fixes without a fail -> pass repro record - ceo T-0025 ... (done) has no tests repro record" (TS-0011 in .pi/.../Tests.md:25-31 carries task: T-0025 but no repro field). Nothing in this diff touches Tests.md, the audit classes or those tasks (engine.py diff = ledger_export only), so the same 2 problems hold at main 3934690 and at merged main. Same defect class as the T-0015 round-1/round-2 fails: a closing record may not promise a gate result it cannot reproduce. Fix: state the measured post-merge expectation, or make the two audit classes clean in this or a linked task and say so. BLOCKING 3 - Plan.md:34 records T-0017 "done | commit e8da9ce"; T-0017 actually merged at ff419fa (git log -1 ff419fa -> "chore(merge): merge of ceo/t-0017-close-m5-mark-the-board-done-and-export", Task: T-0017; ledger trace T-0017 -> pr.merge #0197 ff419fa). e8da9ce is the merge of T-0019/P-0012. The only commit the task packet asks to confirm (T-0017 really merged at e8da9ce) is wrong. BLOCKING 4 - Decisions.md:392 (D-20261019-CEO-6 evidence) claims "git log 9d59976..3934690 -> T-0020, T-0021, T-0022, T-0024, T-0025 merged"; the range excludes its own start, so git log 9d59976..3934690 -> t-0021, t-0022, t-0024, t-0025 only (1 each), and T-0020 is the boundary commit 9d59976 itself. Fix: cite 9d59976^..3934690, or "T-0020 at 9d59976; 9d59976..3934690 -> T-0021, T-0022, T-0024, T-0025". BLOCKING 5 - the supersede is one-directional: decisions in this file record supersession in status (D-20261017-CEO and D-20261017-CEO "Only the CEO performs external publishing" are status: superseded), but D-20261019-CEO-3 (Decisions.md:348-362) still says "status: accepted" with the now-known-invalid "evidence: ... @working-tree" and no pointer to D-20261019-CEO-6. Requirement is to supersede that evidence; leaving it "accepted" keeps a non-reproducible evidence line as the live record and breaks the bidirectional-link rule. Fix: set D-20261019-CEO-3 to status: superseded and name D-20261019-CEO-6. VERIFIED TRUE @b82a08d, do NOT churn: pytest -q -> 384 passed, 1 skipped (only skip tests/acceptance/test_entrypoints.py:90 console script); coverage 67.71%; at 3934690 (throwaway worktree, deleted) pytest -q --cov=teamwork -> 383 passed, 1 skipped, 67.52% - Board/Plan snapshot figures are correct; ruff check . -> All checks passed; ruff format --check . -> 112 files already formatted; mypy src/teamwork -> no issues in 14 source files; teamwork.py links -> # issues: 0; identity --audit --range main..HEAD -> 5 commits, author AND committer CEO <ceo@agents.nidvue.com> = git config, 0 problems; ledger verify -> 318 records, chain intact, head 8b183a00, and the manifest checkpoint 316/head d48fad14 equals ledger record #0316 (action ledger.export, ts = generated_at) -> self-consistent; sha256sum -c <(jq -r ".artifacts[] | \"\(.sha256) \(.path)\"" docs/Team/AuditManifest.json) -> 4/4 OK at HEAD (Architecture 10157, Decisions 27141, Plan 5460, Project 10766) and AuditManifest.md matches the json on every field and row. The export change itself is sound and narrow: engine.py:2534 excludes exactly archive_path(root) by relative path, still pins the other 4 docs, and the reason is in how_to_verify + the comment; pr merge only ever commits docs/Team records (engine.py:900-955), and the only docs/Team file a merge/review appends is Archive.md, so no other pinned artifact can drift at merge - the archive exclusion is the right trade-off (its provenance stays in the chain via trace). New test test_ledger_export_does_not_pin_the_append_only_archive is a real CLI-level assertion (Archive absent, Project/Decisions present), not a mirror of the code. M6 table rows match the merges (T-0020 9d59976, T-0021 2297adc, T-0022 3934690, T-0024 b662faf, T-0025 d72f44b), M6 closed row and the M5 "no M5 task open" line are correct, and 3934690 is an ancestor of main. NON-BLOCKING: (a) the branch was rewritten after the self-check - the ledger records commit ff3d31d (#0317) and selfcheck #0318 while head is b82a08d; trees are identical (e86bd29) so the evidence stands, but re-point the task evidence handle and keep the ledger SHA equal to the reviewed head in future; (b) the 5 commits are one logical closing record - squash to one commit per task as the engineering rules require; (c) the PR body and Board both still say 307 records (the 8d6aeb2 export) - use the final measured count; (d) the new integration test asserts the exclusion but not its reason: a test that appends an Archive entry between export and check and shows the other digests still verify would pin the actual risk.
- branch / merge: ceo/t-0023-bind-the-d-20261019-ceo-3-evidence-to-th / pending
