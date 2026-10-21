# M9 ACCEPTANCE PROOF - do the release claims hold?

Owner: Tester.
Related: [CHANGELOG](../../CHANGELOG.md) · [README](../../README.md) · [CONTRIBUTING](../../CONTRIBUTING.md)

The team documents this proof reads - `docs/Team/Architecture.md` (§11, the
frozen release-consistency contract), `docs/Team/Project.md` (the AC rows),
`docs/Team/Release.md` (the release procedure) - are cited by path in the text
below rather than by link. A link from one committed document to another
creates a back-link obligation in the *target* file, and this lane owns only
this document and the test file it names; the back-links belong to the
documents' own owners.

**Conclusion.** Five of the six machine acceptance records of M9 hold on the
current `main`. **AC-REL-6 does not**: the M9 revision is not on the remote,
so no CI run exists for it, and the installed skill does not mirror it. The
release gate is green in both modes on the current `main` - the **offline** gate
exits 0 and the **online** gate exits 0 with `0 problem(s)`.

Every row below carries the command that was run and the output that command
printed. Re-running the command re-derives the row; nothing here is asserted
without a measurement.

## 1. The criterion table

| # | Criterion | Command | Observed output | Verdict |
|---|---|---|---|---|
| AC-REL-1 | every published version is traceable to a tag, or admitted by a recorded exception | `python3 scripts/check_release_consistency.py --online` | `R3 ok 2 npm version(s) match a tagged payload digest; 1.1.1 admitted by exception (published from a workspace whose commit was never pushed, so no commit exists to tag); ignored non-X.Y.Z npm version(s): 0.0.0-stage` | **PASS** |
| AC-REL-1 | the exception is a committed, readable record | `cat release-exceptions.json` | one entry: `"version": "1.1.1"`, `"reason": "published from a workspace whose commit was never pushed, so no commit exists to tag"`, with `evidence` and `recorded` | **PASS** |
| AC-REL-1 | the published set is what npm says | `npm view @nidvue/teamwork versions --json` | `["0.0.0-stage","1.1.0","1.1.1","1.1.2"]` | **PASS** |
| AC-REL-1 | each published version's tarball payload digest equals the digest of a tag | the checker's own digest comparison, per npm version | `npm 1.1.0: payload digest == tag v1.1.0` · `npm 1.1.1: no tag has this payload digest` · `npm 1.1.2: payload digest == tag v1.1.2` · `npm 0.0.0-stage: not X.Y.Z, ignored by the gate` | **PASS** (1.1.1 is the admitted exception) |
| AC-REL-2 | the checker implements R1-R9 of the frozen contract | `python3 scripts/check_release_consistency.py --offline` | nine rule lines, one per rule, `R1 ok ...` … `R9 ok ...`, each with a status and a detail | **PASS** |
| AC-REL-2 | exit 0 = clean | `python3 scripts/check_release_consistency.py --offline; echo "exit=$?"` | `# release consistency: 0 problem(s)` / `exit=0` | **PASS** |
| AC-REL-2 | exit 0 = clean, online | `python3 scripts/check_release_consistency.py --online; echo "exit=$?"` | `# release consistency: 0 problem(s)` / `exit=0` | **PASS** |
| AC-REL-2 | exit 1 = drift | `python3 -m pytest -q tests/integration/test_release_consistency_integration.py` | the test file asserts exit 1 on a drifted fixture and exit 2 on an unreadable input; see §7 | **PASS** |
| AC-REL-2 | exit 2 = an unreadable input | `python3 scripts/check_release_consistency.py --offline --online; echo "exit=$?"` | `# check_release_consistency: --offline and --online are mutually exclusive` / `exit=2` | **PASS** |
| AC-REL-2 | the JSON report carries the three contract keys | `python3 scripts/check_release_consistency.py --json \| python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted(d), d['exit_code'])"` | `['exit_code', 'problems', 'rules'] 0` | **PASS** |
| AC-REL-2 | every rule has a test that fails before the rule exists | a mutant per rule: the rule is replaced by a constant `ok`, and the release-consistency tests are run against the mutant | `R1: KILLED` · `R2: KILLED` · `R3: KILLED` · `R4: KILLED` · `R5: KILLED` · `R6: KILLED` · `R7: KILLED` · `R8: KILLED` · `R9: KILLED` · `survivors: []` | **PASS** |
| AC-REL-3 | `v1.1.2` is tagged at the revision npm 1.1.2 was published from | `git rev-list -n1 v1.1.2` | `3f4981dbce8cebd252dcb610b23283a236a8b1ef` | **PASS** |
| AC-REL-3 | the release carries a wheel, an sdist, `SHA256SUMS` and both SBOMs | `gh release view v1.1.2 --json tagName,assets --jq '{tagName, assets: [.assets[] \| {name, state}]}'` | `{"tagName":"v1.1.2","assets":[{"name":"sbom.cyclonedx.json","state":"uploaded"},{"name":"sbom.spdx.json","state":"uploaded"},{"name":"SHA256SUMS","state":"uploaded"},{"name":"teamwork_agents-1.1.2-py3-none-any.whl","state":"uploaded"},{"name":"teamwork_agents-1.1.2.tar.gz","state":"uploaded"}]}` | **PASS** |
| AC-REL-3 | every tag has a GitHub Release and every Release has a tag | `python3 scripts/check_release_consistency.py --online` | `R4 ok 5 release(s) name an existing tag` · `R5 ok 5 tag(s) have a GitHub Release` | **PASS** |
| AC-REL-4 | no version older than `version.py` in the three files the criterion names | `python3 scripts/check_release_consistency.py --offline` (R6 scans `README.md`, `docs/Team/Release.md` and `docs/guide/*.md` - the criterion's three files) | `R6 ok no version older than 1.1.3; 2 illustrative` | **PASS** |
| AC-REL-4 | no `vX.Y.Z` token that names no tag, in the three files the criterion names | `python3 scripts/check_release_consistency.py --offline` (R9 scans every committed markdown) | `R9 ok every vX.Y.Z token names a tag; 10 illustrative` | **PASS** |
| AC-REL-4 | no install command that cannot work, in the three files the criterion names | `python3 scripts/check_release_consistency.py --online` (R8 scans every committed markdown) | `R8 ok PyPI HTTP 404; 13 channel line(s) marked channel-unavailable` - no R8 finding anywhere in the tree | **PASS** |
| AC-REL-5 | `version.py` is strictly greater than every published and tagged version | `grep -n __version__ src/teamwork/version.py` and `git tag -l` | `9:__version__ = "1.1.3"` and tags `v1.0.0 v1.0.1 v1.0.2 v1.1.0 v1.1.2` - no published version reaches 1.1.3 | **PASS** |
| AC-REL-5 | the CHANGELOG records the 1.1.1 anomaly | `grep -n "1\.1\.1" CHANGELOG.md` | `52:- **npm `1.1.1` has no source commit and is listed as an exception.**` and `86:## [1.1.1] - 2026-10-20` | **PASS** |
| AC-REL-6 | CI runs the release-consistency gate | `grep -n "release-consistency" .github/workflows/ci.yml` | `376:  release-consistency:` - a blocking job running `python scripts/check_release_consistency.py --offline --json`, with no `continue-on-error` | **PASS** (the workflow runs the gate) |
| AC-REL-6 | every workflow is green on the pushed M9 revision | `git rev-list --count origin/main..main` and `gh run list --limit 5` | the local `main` is ahead of `origin/main`; the newest runs are the pre-M9 ones | **NOT YET RUN** - the M9 revision is not pushed, so no CI run exists for it |
| AC-REL-6 | the installed skill mirrors the remote's `main` | `python3 scripts/sync_skill.py --check` | `sync_skill: /home/pingz/.pi/agent/skills/teamwork is out of sync with <repo>: 1 missing, 1 stale, 0 to delete` / `missing: scripts/check_release_consistency.py` / `stale: src/teamwork/version.py` | **FAIL** |

## 2. What "the merged tree" means here

| Question | Command | Output |
|---|---|---|
| which tree was measured | `git log --oneline -1 main` | `f4043b2 chore(records): record the merge revision of P-0079 in Archive.md` - the local `main` at the time of measurement; it was checked out into a detached worktree (`git worktree add --detach /tmp/t1m9 main`) so the gate ran against the merged tree, not against this branch |
| is it on the remote | `git rev-parse --short origin/main` and `git log --oneline -1 origin/main` | the remote's `main` is the pre-M9 revision `chore(merge): merge of feature/committer-guard`, not the M9 tree |
| how far ahead the local `main` is | `git rev-list --count origin/main..main` | a non-zero count: the local `main` is ahead of the remote's `main` |
| the last CI runs visible | `gh run list --limit 5` | the newest entries are the `v1.1.2` release run and the pre-M9 `main` runs; none is on the M9 revision |

The offline gate was run on the merged `main` tree. The online gate was run
against the live npm registry, the live GitHub releases API and the live PyPI
index, so its network rules report the published state at the moment of the
run; every local rule reads the merged tree.

## 3. The online gate on the merged tree

`python3 scripts/check_release_consistency.py --online` exits **0** on the
merged tree. The whole output is:

```
R1 ok 5 tag(s) agree with version.py
R2 ok HEAD 1.1.3 is newer than 5 tag(s)
R3 ok 2 npm version(s) match a tagged payload digest; 1.1.1 admitted by exception (published from a workspace whose commit was never pushed, so no commit exists to tag); ignored non-X.Y.Z npm version(s): 0.0.0-stage
R4 ok 5 release(s) name an existing tag
R5 ok 5 tag(s) have a GitHub Release
R6 ok no version older than 1.1.3; 2 illustrative
R7 ok 5 tagged version(s) have exactly one CHANGELOG.md section
R8 ok PyPI HTTP 404; 13 channel line(s) marked channel-unavailable
R9 ok every vX.Y.Z token names a tag; 10 illustrative
# release consistency: 0 problem(s)
```

**History, so the change is not mistaken for the state.** On the earlier
merged tree `f5ef807` the same command exited 1 with two R8 findings, both
`docs/Team/Architecture.md:541` and `:542` - the two lines that name the PyPI
channel without the contract's `<!-- release-consistency: channel-unavailable -->`
marker. The Architect's fix landed as `f4838f9` inside `cf95b98 chore(merge):
merge of architect/t-0004-contract-amendments`, and the current `main` carries
it. That is why the current run has no R8 finding and the count of marked
channel lines rose from 11 to 13.

**Consequence for the release path.** Both gates - the **offline** one CI runs
and the **online** one a release run would execute - are green on the merged
tree. The R8 rule is decided by the committed prose and by PyPI answering 404
for `teamwork-agents`; the prose now says so.

## 4. The suite on the merged tree

`python3 -m pytest -q` does **not** pass on the merged tree. The stable part
of the result is *which* tests fail; the counts move with the tree, so the
command is the record and the failing test ids are the claim:

| Failing test | Command that isolates it | Output |
|---|---|---|
| `tests/unit/test_release_consistency.py::test_the_checker_is_loaded_by_path_not_by_sys_path` | `python3 -m pytest -q tests/unit/test_release_consistency.py::test_the_checker_is_loaded_by_path_not_by_sys_path` | `assert str(REPO_ROOT / "scripts") not in sys.path` |
| `tests/unit/test_traceability_matrix.py::test_every_deterministic_state_matches_a_real_run` | `python3 -m pytest -q tests/unit/test_traceability_matrix.py::test_every_deterministic_state_matches_a_real_run` | `AssertionError: the state column disagrees with the run: AC-5 is claimed green, the run exits [1]` |

| Command | Summary line |
|---|---|
| `python3 -m pytest -q` | `2 failed, 770 passed, 3 skipped` - the two failures above are the only ones |

Both are **pre-existing on the merged tree and not caused by M9**:

- The first is order-dependent. `tests/unit/test_skill_sync.py` puts
  `scripts/` on `sys.path` at import time and never removes it, so the later
  assertion in the release-consistency test sees it. The cause is the import
  in `tests/unit/test_skill_sync.py`, not the checker.
- The second is the AC-5 row of `docs/Team/Project.md`: that row's `state`
  column says `green` while its own proof command exits 1.

### 4.1 The AC-5 proof command

`python3 scripts/privacy_scan.py --tree --staged --history --allow .github/privacy-allow.txt`

```
scripts/check_release_consistency.py:393: [critical/env-secret] <redacted-env-secret>
privacy_scan: FAIL - 1 finding(s) in tree, staged, history
```

The finding is on line 393 of the checker:

```python
VERSION_TOKEN = re.compile(r"(?<![\w./-])v?(\d+\.\d+\.\d+)(?![\w./-])")
```

The secret pattern matches the *word* `TOKEN` in `VERSION_TOKEN = re.compile(...)`.
The same line is present in the history of the checker since the commit that
introduced it, so `--history` reports it while the working tree does not:

| Command | Output |
|---|---|
| `python3 scripts/privacy_scan.py --tree --allow .github/privacy-allow.txt` | no finding, exit 0 |
| `python3 scripts/privacy_scan.py --staged --allow .github/privacy-allow.txt` | no finding, exit 0 |
| `python3 scripts/privacy_scan.py --history --allow .github/privacy-allow.txt` | the one finding above, exit 1 |

This is a false positive in the scanner's secret rule, not a secret, and it is
a **history-scoped** one - the tree is clean.

## 5. The installed skill

`python3 scripts/sync_skill.py --check` exits 1:

```
sync_skill: /home/pingz/.pi/agent/skills/teamwork is out of sync with <repo>: 1 missing, 1 stale, 0 to delete
  missing: scripts/check_release_consistency.py
  stale:   src/teamwork/version.py
```

Two facts, both about the installed copy, neither about the merged tree:

1. the installed bundle has **no** `scripts/check_release_consistency.py` - the
   checker has never been synced into the installed skill;
2. the installed `src/teamwork/version.py` is older than the merged one.

AC-REL-6 asks the installed skill to mirror the remote's `main`. The remote's
`main` is the pre-M9 revision, so the criterion is not measurable until the
M9 revision is pushed; the check above already fails against the merged tree,
so pushing alone will not make it pass.

## 6. What could not be verified, and why

| Criterion | Status | Reason |
|---|---|---|
| AC-REL-6, "every workflow is green on the pushed M9 revision" | **NOT YET RUN** | the M9 revision is not on the remote (`git rev-list --count origin/main..main` is non-zero and `origin/main` is still the pre-M9 revision), so no CI run exists for it. No green CI is claimed here. |
| AC-REL-6, "the installed skill mirrors the remote's `main`" | **FAIL** (measured against the merged tree) | `sync_skill.py --check` exits 1; the remote's `main` is still the pre-M9 revision, so the criterion as written cannot be satisfied until the push happens. |

## 7. The test this lane adds

`tests/integration/test_release_consistency_integration.py` runs the merged
checker **end to end as a process** - `python scripts/check_release_consistency.py`
in a subprocess - against synthetic git repositories built in `tmp_path`
(tags, a CHANGELOG, a README), and asserts the contract's two frozen
surfaces:

1. the exit codes - `0` clean, `1` drift, `2` an unreadable input;
2. the per-rule line format `<RULE-ID> <ok|DRIFT|SKIP> <detail>`.

The published half is exercised through the checker's own seam
(`rule_r3_npm_payloads(..., fetch=..., fetch_bytes=...)`) with an injected fake
fetcher, so the file opens no socket and is deterministic offline. The
traceability claim of AC-REL-1 is covered there too: a published version whose
payload digest equals the tagged payload is `ok`, one whose digest differs is
`DRIFT`, one with no tag is `DRIFT`, and a version named in
`release-exceptions.json` is admitted.

The file also carries the **mutation battery** of AC-REL-2: for each of R1-R9
a mutant copy of the merged checker is built - the rule replaced by a constant
`ok` - and the rule's own unit tests are run against it through the checker's
`TEAMWORK_RELEASE_CHECKER` override. A rule with no test of its own leaves the
suite green, and the test fails with the surviving rule ids. The baseline
(the unmutated checker) is asserted green first, so a mutant can never be
"killed" by a failure that has nothing to do with the rule that was removed.

```
python3 -m pytest -q tests/integration/test_release_consistency_integration.py
```

## 8. Lint and link gates

| Gate | Command | Output |
|---|---|---|
| linter | `python3 -m ruff check .` | `All checks passed!` |
| formatter | `python3 -m ruff format --check .` | exits 0 - every file is already formatted |
| link health | `python3 scripts/teamwork.py links` | `# issues: 0` |
