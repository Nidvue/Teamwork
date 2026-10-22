# M9 ACCEPTANCE PROOF - do the release claims hold?

Owner: Tester.
Related: [Project](Project.md) · [CHANGELOG](../../CHANGELOG.md) · [README](../../README.md) · [CONTRIBUTING](../../CONTRIBUTING.md)

## Status

**Historical measurement - superseded on AC-REL-6.** This proof was taken at
`fb99293149`, before the M9 revision was pushed. Its one open row has since
closed:

- **AC-REL-6 now holds.** The M9 revision was pushed, and CI run 39690418108 on
  `22ade33` reported **19/19 jobs success**; `refresh --check` reports the
  installed skill matches `origin/main`.

Every other row below stands as measured. Read "NOT YET RUN" and "FAIL" as the
state at `fb99293149`, not as the current state.

The team documents this proof reads - `docs/Team/Architecture.md` (§11, the
frozen release-consistency contract), `docs/Team/Project.md` (the AC rows),
`docs/Team/Release.md` (the release procedure) - are cited by path in the text
below rather than by link. A link from one committed document to another
creates a back-link obligation in the *target* file, and this lane owns only
this document and the test file it names; the back-links belong to the
documents' own owners.

**Conclusion at `fb99293149`.** Five of the six machine acceptance records of M9
held. **AC-REL-6 did not** at that revision: the M9 revision was not yet on the
remote, so no CI run existed for it, and the installed skill did not mirror it
(closed later - see *Status* above). The release gate was green in both modes -
the **offline** gate exited 0 and the **online** gate exited 0 with `0
problem(s)`.

Every row below carries the command that was run and the output that command
printed. Re-running the command re-derives the row; nothing here is asserted
without a measurement.

## 1. The criterion table

| # | Criterion | Command | Observed output | Verdict |
|---|---|---|---|---|
| AC-REL-1 | every published version is traceable to a tag, or admitted by a recorded exception | `python3 scripts/check_release_consistency.py --online` | `R3 ok 2 npm version(s) match a tagged payload digest; 0.0.0-stage admitted by exception (npm's staged-publish placeholder, published before 1.1.0 with no source commit and no bundled payload); 1.1.1 admitted by exception (published from a workspace whose commit was never pushed, so no commit exists to tag)` | **PASS** |
| AC-REL-1 | the exception is a committed, readable record | `cat release-exceptions.json` | one entry: `"version": "1.1.1"`, `"reason": "published from a workspace whose commit was never pushed, so no commit exists to tag"`, with `evidence` and `recorded` | **PASS** |
| AC-REL-1 | the published set is what npm says | `npm view @nidvue/teamwork versions --json` | four versions, one per line in a JSON array: `"0.0.0-stage"`, `"1.1.0"`, `"1.1.1"`, `"1.1.2"` (the command pretty-prints one string per line; written on one line here) | **PASS** |
| AC-REL-1 | each published version's tarball payload digest equals the digest of a tag | the checker's own digest comparison, per npm version, replayed through `_tarball_payload_digest` and `payload_digest` | `1.1.0: digest ebfc2538e3d3d605 == payload of v1.1.0: True` · `1.1.1: digest 726bc547afc41ead; no tag names it; tags with this digest: []` · `1.1.2: digest a01d9f0cbee641c3 == payload of v1.1.2: True` · `0.0.0-stage: tarball unreadable: npm tarball: none of the shipped payload paths are present` (non-`X.Y.Z`, so R3 does not look for a tag for it) | **PASS** (1.1.1 is the admitted exception) |
| AC-REL-2 | the checker implements R1-R9 of the frozen contract | `python3 scripts/check_release_consistency.py --offline` | nine rule lines, one per rule, each with a status and a detail: five `ok` (`R1`, `R2`, `R6`, `R7`, `R9`) and four `SKIP` with a reason (`R3`, `R4`, `R5`, `R8` - the network half is not queried offline). The verdict is still clean, `# release consistency: 0 problem(s)`; §3 has the whole output | **PASS** (the four SKIPs are the offline half by design, see §3) |
| AC-REL-2 | exit 0 = clean | `python3 scripts/check_release_consistency.py --offline; echo "exit=$?"` | `# release consistency: 0 problem(s)` / `exit=0` | **PASS** |
| AC-REL-2 | exit 0 = clean, online | `python3 scripts/check_release_consistency.py --online; echo "exit=$?"` | `# release consistency: 0 problem(s)` / `exit=0` | **PASS** |
| AC-REL-2 | exit 1 = drift | `python -m pytest -q tests/integration/test_release_consistency_integration.py` | `13 passed`; the file asserts exit 1 on a drifted fixture and exit 2 on an unreadable input; see §7 | **PASS** |
| AC-REL-2 | exit 2 = an unreadable input | `python3 scripts/check_release_consistency.py --offline --online; echo "exit=$?"` | `# check_release_consistency: --offline and --online are mutually exclusive` / `exit=2` | **PASS** |
| AC-REL-2 | the JSON report carries the three contract keys | `python3 scripts/check_release_consistency.py --json \| python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted(d), d['exit_code'])"` | `['exit_code', 'problems', 'rules'] 0` | **PASS** |
| AC-REL-2 | every rule has a test that fails before the rule exists | a mutant per rule: the rule is replaced by a constant `ok`, the release-consistency unit tests are run against the mutant, and the test asserts `survivors == []` | `1 passed in 16.68s` for `test_every_rule_has_a_test_that_fails_before_the_rule_exists`; a rule that no test covers makes it fail with `a rule with no failing test: ['R<n>']` | **PASS** (§7 has the mechanism) |
| AC-REL-3 | `v1.1.2` is tagged at the revision npm 1.1.2 was published from | `git rev-list -n1 v1.1.2` | `3f4981dbce8cebd252dcb610b23283a236a8b1ef` | **PASS** |
| AC-REL-3 | the release carries a wheel, an sdist, `SHA256SUMS` and both SBOMs | `gh release view v1.1.2 --json tagName,assets --jq '{tagName, assets: [.assets[] \| {name, state}]}'` | `{"assets":[{"name":"sbom.cyclonedx.json","state":"uploaded"},{"name":"sbom.spdx.json","state":"uploaded"},{"name":"SHA256SUMS","state":"uploaded"},{"name":"teamwork_agents-1.1.2-py3-none-any.whl","state":"uploaded"},{"name":"teamwork_agents-1.1.2.tar.gz","state":"uploaded"}],"tagName":"v1.1.2"}` | **PASS** |
| AC-REL-3 | every tag has a GitHub Release and every Release has a tag | `python3 scripts/check_release_consistency.py --online` | `R4 ok 5 release(s) name an existing tag` · `R5 ok 5 tag(s) have a GitHub Release` | **PASS** |
| AC-REL-4 | no version older than `version.py` in the three files the criterion names | `python3 scripts/check_release_consistency.py --offline` (R6 scans `README.md`, `docs/Team/Release.md` and `docs/guide/*.md` - the criterion's three files) | `R6 ok no version older than 1.1.3; 2 illustrative` | **PASS** |
| AC-REL-4 | no `vX.Y.Z` token that names no tag, in the three files the criterion names | `python3 scripts/check_release_consistency.py --offline` (R9 scans every committed markdown) | `R9 ok every vX.Y.Z token names a tag; 10 illustrative` | **PASS** |
| AC-REL-4 | no install command that cannot work, in the three files the criterion names | `python3 scripts/check_release_consistency.py --online` (R8 scans every committed markdown) | `R8 ok PyPI HTTP 404; 13 channel line(s) marked channel-unavailable` - no R8 finding anywhere in the tree | **PASS** |
| AC-REL-5 | `version.py` is strictly greater than every published and tagged version | `grep -n __version__ src/teamwork/version.py` and `git tag -l` | `9:__version__ = "1.1.3"`; `git tag -l` prints five tags on five lines - `v1.0.0`, `v1.0.1`, `v1.0.2`, `v1.1.0`, `v1.1.2` - so no tagged version reaches 1.1.3 | **PASS** |
| AC-REL-5 | the CHANGELOG records the 1.1.1 anomaly | `grep -n "1\.1\.1" CHANGELOG.md` | `52:- **npm 1.1.1 has no source commit and is listed as an exception.**` (the version number is inside backticks in the file) and `86:## [1.1.1] - 2026-10-20` | **PASS** |
| AC-REL-6 | CI runs the release-consistency gate | `grep -n "release-consistency" .github/workflows/ci.yml` | `376:  release-consistency:` - a blocking job running `python scripts/check_release_consistency.py --offline --json`, with no `continue-on-error` | **PASS** (the workflow runs the gate) |
| AC-REL-6 | every workflow is green on the pushed M9 revision | `git rev-list --count origin/main..main` and `gh run list --limit 5` | at the audited revision the local `main` was ahead of `origin/main` and the newest runs were the pre-M9 ones | **CLOSED LATER** - the revision was pushed and CI run 39690418108 on `22ade33` was 19/19 success; not measurable at `fb99293149` |
| AC-REL-6 | the installed skill mirrors the remote's `main` | `python3 scripts/sync_skill.py --check` (exit code and the `missing:`/`stale:` rows) | at the audited revision it exited 1: files the tree ships were absent from the installed bundle and installed engine files were older than the tree (§5). The counts are not quoted - they move with every commit | **CLOSED LATER** - `refresh --check` now reports the installed skill matches `origin/main`; it was **FAIL** at `fb99293149` |

## 2. What "the merged tree" means here

| Question | Command | Output |
|---|---|---|
| which revision the gates were measured at | `git rev-parse main` | `fb99293149efcfc5fcf416f42189e5bdfd171750` - the local `main` when this document was re-measured. The first version named `f4043b2`; `main` has since moved **18 commits** (`git rev-list --count f4043b2..main` -> `18`), and the two test failures of that revision are fixed (§4), so every block below is re-measured at `fb99293` |
| which tree the suite ran on | `git merge-tree --write-tree --no-messages main HEAD` | `5e844438d356cdaa74dd8cec2effec9bfd5bcbd7` - the tree of this branch merged into `main`, computed without touching either checkout; a detached worktree over that tree was used for the suite, so the suite is the merged tree and not this branch alone |
| is it on the remote | `git log --oneline -1 origin/main` | `f277ac7 chore(merge): merge of feature/committer-guard` - the remote's `main` is the pre-M9 revision, not the M9 tree |
| how far ahead the local `main` is | `git rev-list --count origin/main..main` | `99` |
| the last CI runs visible | `gh run list --limit 5` | the newest entry is `completed success fix(packaging): publish the pi package as @nidvue/teamwork (#23) Release v1.1.2 push 39503086136 2m4s 2026-10-20T21:46:40Z` (tab-separated columns joined with single spaces); the rest are pre-M9 `main` / `feature/committer-guard` runs. None is on the M9 revision |

The scripts invoked below are the ones in the measured checkout (`python3
scripts/...` from the tree root), not from any other clone. The offline gate was
run on `main` and on the merged tree with byte-identical output. The online gate
was run against the live npm registry, the live GitHub releases API and the live
PyPI index, so its network rules report the published state at the moment of the
run; every local rule reads the measured tree.

**Interpreter.** The gate scripts are standard-library only; the offline gate and
the privacy scan were run both with the bare `python3` on this host (3.14.8) and
with `/home/pingz/Code/Nidvue/Teamwork/.venv/bin/python`, and printed the same
result, so their commands keep the plain `python3` form. The suite and ruff need
the project virtualenv - the bare `python3` has neither pytest nor ruff installed
- so their commands are written `python` and mean that virtualenv's interpreter
(pytest 9.1.1, ruff 0.17.1).

## 3. The online gate on the merged tree

`python3 scripts/check_release_consistency.py --online` exits **0** on the
merged tree. The whole output is:

```
R1 ok 5 tag(s) agree with version.py
R2 ok HEAD 1.1.3 is newer than 5 tag(s)
R3 ok 2 npm version(s) match a tagged payload digest; 0.0.0-stage admitted by exception (npm's staged-publish placeholder, published before 1.1.0 with no source commit and no bundled payload); 1.1.1 admitted by exception (published from a workspace whose commit was never pushed, so no commit exists to tag)
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

`python -m pytest -q` at this branch head exits **0**, with three skips and no
failure. The claim is the exit code and the three named skips, never a pass
count: a count pinned at one revision is wrong at the next, and this file already
carried two stale ones. Read the number from the run that proves it - the shape
of the last line is `<n> passed, 3 skipped`.

The three skips, as pytest prints them:

```
SKIPPED [1] tests/acceptance/test_entrypoints.py:90: console script not installed; covered by scripts/verify_release.py
SKIPPED [1] tests/unit/test_task_graph_integrity.py:381: no local team tree in this checkout (gitignored working state)
SKIPPED [1] tests/unit/test_traceability_matrix.py:101: no .pi/Teamwork/Teams/*/Tests.md in this checkout (team tree is gitignored)
```

They are structural: a lane worktree carries no `.pi/` team tree and no installed
console script, so those three cannot run here and are covered by
`scripts/verify_release.py` and by the CEO's own checkout respectively.

Getting to zero needed one fix this lane had not made: `docs/Team/Project.md` did
not link back to this file, so `teamwork.py links` reported
`docs/Team/M9Acceptance.md links to docs/Team/Project.md but docs/Team/Project.md
does not link back` and four tests that run the link check over the committed
tree failed on it. The back-link is in `Project.md`'s `Related:` line.

### 4.1 The AC-5 proof command

`python3 scripts/privacy_scan.py --tree --staged --history --allow .github/privacy-allow.txt`

At `fb99293`, and on the merged tree, the whole output is:

```
privacy_scan: PASS - 0 finding(s) in tree, staged, history
```

exit 0.

**History.** At `f4043b2` - the revision the first version of this document
named - the same command printed six findings and exited 1:

```
scripts/privacy_scan.py:280: [critical/env-secret] <redacted-env-secret>
tests/unit/test_privacy_scan.py:205: [critical/env-secret] <redacted-env-secret>
tests/unit/test_privacy_scan.py:209: [critical/env-secret] <redacted-env-secret>
tests/unit/test_privacy_scan.py:210: [critical/env-secret] <redacted-env-secret>
tests/unit/test_privacy_scan.py:222: [critical/env-secret] <redacted-env-secret>
scripts/check_release_consistency.py:393: [critical/env-secret] <redacted-env-secret>
privacy_scan: FAIL - 6 finding(s) in tree, staged, history
```

**Those line numbers are history-blob line numbers, not lines of the files as
committed.** All six are the *same* match - an assignment of the result of the
`_current_github_token()` call, whose name ends in `token` - and none of them is
in the working tree. (The assignment is described rather than quoted here on
purpose: a verbatim copy is itself a credential-shaped assignment and would trip
the same rule in this document.) Measured by replaying `scan_history` and
reading the flagged line out of the blob it names:

| History blob:line | Flagged line |
|---|---|
| `scripts/privacy_scan.py` blob `196edba`:280 | the docstring that quotes that assignment |
| `tests/unit/test_privacy_scan.py` blob `195a2f01`:205, :209, :210, :222 | the four regression-test lines that quote the same call |
| `scripts/check_release_consistency.py` blob `4f630ccc`:393 | that assignment |

The env-secret rule read a *function call* as a credential. `ef6eeb7` added the
`_is_code_name()` guard - an unquoted bare identifier is a reference to a value,
not the value - and the six findings went to zero. **The count is not a stable
number**: it moves with the scanner's rule, so the claim this document makes is
the command and its exit code, not the number, and any figure quoted here is
stamped with the revision it came from.

The scan was history-scoped only; the tree and the index were clean at both
revisions:

| Command | At `f4043b2` | At `fb99293` |
|---|---|---|
| `python3 scripts/privacy_scan.py --tree --allow .github/privacy-allow.txt` | `privacy_scan: PASS - 0 finding(s) in tree`, exit 0 | `privacy_scan: PASS - 0 finding(s) in tree`, exit 0 |
| `python3 scripts/privacy_scan.py --staged --allow .github/privacy-allow.txt` | `privacy_scan: PASS - 0 finding(s) in staged`, exit 0 | `privacy_scan: PASS - 0 finding(s) in staged`, exit 0 |
| `python3 scripts/privacy_scan.py --history --allow .github/privacy-allow.txt` | the six findings above, exit 1 | `privacy_scan: PASS - 0 finding(s) in history`, exit 0 |

## 5. The installed skill

`python3 scripts/sync_skill.py --check` exits 1 with a
`<n> missing, <m> stale, 0 to delete` line and one `missing:`/`stale:` row per
file. The counts are deliberately not quoted here: they move with every commit
that touches a bundled file, and the installed copy is refreshed on the release
lane, not on this one. The claim is the exit code and the class of drift, read
from the run:

- the installed bundle is missing files the tree ships - including
  `scripts/check_release_consistency.py`, the gate itself, and the harness
  modules `src/teamwork/harness.py` and `hooks.py` that arrived with the
  reconciled line;
- installed engine files are older than the measured tree, so behaviour read
  from the installed copy can differ from the checkout. One measured instance:
  the installed `engine.py` lacked `_task_has_execution_evidence`, which made
  `teamwork audit` run from the installed skill report five false "done without
  evidence" rows while the checkout reported none. The remedy is
  `teamwork.py refresh` on the release lane, not a re-install here.

AC-REL-6 asks the installed skill to mirror the remote's `main`. The remote's
`main` was the pre-M9 revision, so the criterion was not measurable until the
M9 revision was pushed, and the check above failed against the merged tree as
well - pushing alone would not have made it pass. Both were resolved afterwards:
the push happened, CI went green on it, and the installed skill was refreshed.

## 6. What could not be verified, and why

| Criterion | Status | Reason |
|---|---|---|
| AC-REL-6, "every workflow is green on the pushed M9 revision" | **CLOSED LATER** (was **NOT YET RUN**) | at the audited revision the M9 revision was not on the remote, so no CI run existed for it and no green CI was claimed. The revision was pushed later and CI run 39690418108 on `22ade33` was 19/19 success. |
| AC-REL-6, "the installed skill mirrors the remote's `main`" | **CLOSED LATER** (was **FAIL** against the merged tree) | `sync_skill.py --check` exited 1 at the audited revision; `refresh --check` now reports the installed skill matches `origin/main`. |

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
python -m pytest -q tests/integration/test_release_consistency_integration.py
13 passed in 18.08s
```

The count is the claim, not the duration (a second run printed `13 passed in
15.79s`).

## 8. Lint and link gates

| Gate | Command | Output |
|---|---|---|
| linter | `python -m ruff check .` (the project virtualenv; ruff is not on the bare `python3` path) | `All checks passed!` |
| formatter | `python -m ruff format --check .` | `146 files already formatted`, exit 0 |
| link health | `python3 scripts/teamwork.py links` | `# issues: 0` |
