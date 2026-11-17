# M26 docs audit - false claims proved by command

Owner: Technical Writer. Task: T-0001. Audit only: no page was edited.
Related: [Evidence](../../../references/Evidence.md), [Roles](../../../references/Roles.md).
Revision audited: `d6ab6d23` (branch `technicalwriter/t-0001-...`, forked from `main`).
Scope: the committed documentation a reader or operator acts on - `README.md`,
`CHANGELOG.md`, `SKILL.md`, `references/*.md`, `roles/*.md`, `docs/*.md`,
`docs/guide/*.md`, and `docs/Team/*.md` except the append-only `Archive.md`.

Ranking is by how badly a reader is misled. Each finding carries the command that
disproves the page and the smallest correction, not a rewrite.

## 1. Findings

### F1 - `docs/Team/Release.md:394` `### Open drift` omits R2, which is red at this head

- Claim: the live drift table (`:394-400`) lists three open items - the R8 marker,
  `required_linear_history=false`, the unpinned ruff - and no R2. R2 appears only in
  the dated history paragraph under `### Closed: R2 was red off the release tag`
  (`:402`), whose sentence at `:404` reads "Not current drift any more ... `R2`
  reports `ok` on a branch", with its measured block marked
  `release-consistency: illustrative` (`:414`).
- Disproof: `/usr/bin/python3 scripts/check_release_consistency.py --offline` @`d6ab6d23`
  -> `R2 DRIFT HEAD version 1.5.9 is not greater than tag v1.5.9`,
  `# release consistency: 1 problem(s)`, exit `1`. `git rev-list --count v1.5.9..HEAD`
  -> `82`: the version was not bumped after the tag, so R2 is red at this head and
  absent from the table an operator reads for open drift.
- Corrected sentence: add a row to `### Open drift` (`Release.md:394`) reading "R2 red
  at head: `DRIFT HEAD version 1.5.9 is not greater than tag v1.5.9` - the next
  release bumps `version.py` before it tags"; the closed paragraph at `:402-409` is
  dated history and stays.
- Why it ranks first: this is the page an operator reads before cutting a release,
  and its live table does not carry the one red check.

### F2 - the install story ships 82 unreleased commits as version 1.5.9

- Claim: `docs/guide/install.md:24` "Every channel below ships the engine in
  `src/teamwork/` from the same tagged revision"; `README.md:85`, `docs/guide/install.md:42`,
  `docs/releases.md:44`, `docs/guide/quickstart.md:18`, `docs/guide/for-agents.md:28`
  all install with `git clone --depth 1 https://github.com/Nidvue/Teamwork.git`.
- Disproof: `git rev-list --count v1.5.9..HEAD` -> `82`; `grep -n __version__ src/teamwork/version.py`
  -> `1.5.9`; `npm view @nidvue/teamwork dist-tags --json` -> `{"latest": "1.5.9"}`;
  `gh release view --json tagName --jq .tagName` -> `v1.5.9`. The clone channel
  resolves the default branch, so a user receives 82 commits that no tag, no npm
  tarball and no GitHub Release contains, while every surface - including
  `teamwork --version` - prints `1.5.9`.
- Corrected sentence: "The clone channel follows `main`, which runs ahead of the
  newest tag; pin the tag with `git clone --branch v1.5.9 --depth 1 ...` when you
  want the released revision."
- Second half: `docs/releases.md:14` says a release publishes "one tagged revision"
  to four faces. That is true of the four faces; it is not true of the skill clone,
  and no page says so.

### F3 - `CITATION.cff:13` names version 1.5.6; the tree is 1.5.9

- Claim: `version: 1.5.6`, `date-released: "2026-11-13"`.
- Disproof: `grep -n __version__ src/teamwork/version.py` -> `9:__version__ = "1.5.9"`;
  `git tag -l --sort=-v:refname | head -1` -> `v1.5.9`. `grep -rn CITATION scripts/check_release_consistency.py`
  -> the checker reads `CITATION.cff` only for its `license:` line (`CITATION_LICENSE`,
  `_citation_claims`), so no rule compares the version.
- Corrected sentence: `version: 1.5.9`, `date-released: "2026-11-15"` (the
  `CHANGELOG.md:12` date), plus a rule or a bump step, otherwise it drifts again.
- Class note: this is the one version surface the release gate cannot see, and it is
  two releases stale.

### F4 - `docs/Team/Board.md:10` names M12 as the live milestone

- Claim: "Milestone: M12 (release parity: GitHub, npm, Pages) is the engagement that
  is live".
- Disproof: `grep -n '^## M' docs/Team/Project.md | tail -8` -> the newest milestone
  is `## M24` (`:418`); this task is `M26`. `grep -c '(this engagement)' docs/Team/Project.md`
  -> `10`, so ten sections simultaneously claim to be the live engagement
  (`:161 M12`, `:189 M13`, `:218 M14`, `:239 M15`, `:265 M17`, `:313 M18`, `:346 M20`,
  `:369 M21`, `:393 M22`, `:418 M24`).
- Corrected sentence: "Milestone: read the live one with `teamwork.py board`; the
  `(this engagement)` marker in `Project.md` is history and names ten milestones."
- Why it matters: the board is the first page a reader opens for "where is this
  project", and it is 14 milestones behind.

### F5 - the tree census pins 214 tracked files; the tree has 379

- Claim: `docs/Team/Board.md:18` "Tree census (project-manager T-0001): 214 tracked
  files classified, 206 live"; `docs/Team/Plan.md:326` "214 tracked files, each
  classified"; `Plan.md:332` the measurement row `| tracked files | git ls-files \| wc -l | 214 |`
  (`:328` is the prose line "be re-run:", not the row).
- Disproof: `git ls-files | wc -l` @`d6ab6d23` -> `379`.
- Corrected sentence: drop the number and keep the command, as the same board does
  four lines earlier for release state ("each fact read by its own command - no value
  is pinned here, because every one of them moves").
- Class note: `Plan.md:334` pins the test count too (`1256 tests in 83 modules`); the
  same defect, not counted separately. `UNVERIFIED` at this head - `pytest` is absent
  from the system interpreter - so it is reported as the same class, not as a finding.

### F6 - `docs/Team/Plan.md:536` lists `tests/unit/test_portable.py` as live; no such file

- Claim: "`tests/unit/test_portable.py` | live | pytest collects it (1256 tests
  collected) | kept".
- Disproof: `git ls-files | grep -E 'test_portab'` -> `tests/acceptance/test_portability_acceptance.py`,
  `tests/integration/test_portability_flow.py`, `tests/unit/test_portability.py`; no
  `test_portable.py`.
- Corrected sentence: delete the row - the module it means is `tests/unit/test_portability.py`,
  which already has its own row at `Plan.md:535`.

### F7 - `docs/Team/Plan.md:489` lists `tests/integration/test_ci_scope_classifier.py`; it was renamed

- Claim: "`tests/integration/test_ci_scope_classifier.py` | live | pytest collects it".
- Disproof: `git ls-files | grep test_ci_scope` -> `tests/integration/test_ci_scope_flow.py`,
  `tests/unit/test_ci_scope.py`; the classifier module no longer exists under that name.
- Corrected sentence: `tests/integration/test_ci_scope_flow.py`.

### F8 - `docs/Team/Release.md:398` points the open R8 item at a line that is not a channel claim

- Claim: row 1 of `### Open drift` (`Release.md:398`, owner `ceo` T-0004): "the R8
  marker is missing at `docs/Team/Decisions.md:1284` - blocks every release".
  (`Release.md:400` is row 3, the unpinned ruff, owner `release-engineer` T-0002.)
- Disproof: `sed -n '1282,1286p' docs/Team/Decisions.md` -> `:1284` is `- task: T-0010`
  and `:1285` is the `context:` line of the T-0010 CI-branch-name decision, with no
  install channel in it. The markers R8 wants are present elsewhere
  (`grep -c 'channel-unavailable' docs/Team/Decisions.md` -> `2`, e.g. `:125`), and
  `check_release_consistency.py --offline` reports
  `R8 SKIP offline: ... 18 channel line(s), 11 marked channel-unavailable`, so the
  row's line number is stale whatever its state.
- Corrected sentence: re-derive the line with the online gate
  (`python3 scripts/check_release_consistency.py --online`) and cite the file, not a
  line number that moves.

### F9 - the install block is restated in eight places, with no single source

- Claim: eight pages print the same clone command as authoritative, and three of
  them as one `mkdir && clone && rm -rf .git` chain.
- Disproof: `grep -rn 'git clone --depth 1 https://github.com/Nidvue/Teamwork.git .agents/skills/teamwork' README.md CHANGELOG.md SKILL.md references docs | grep -v Reviews/M26-docs-audit | wc -l`
  -> `8`: `README.md:85`, `README.md:102`, `docs/releases.md:44`,
  `docs/guide/quickstart.md:18`, `docs/guide/install.md:42`, `docs/guide/for-agents.md:28`,
  `docs/guide/usage.md:27`, `docs/index.md:53`. `README.md` prints it twice. Three of
  the eight print the one-line chain (`README.md:102`, `docs/guide/usage.md:27`,
  `docs/index.md:53`); the other five print the clone and a separate
  `rm -rf .agents/skills/teamwork/.git` line, so all eight do remove the nested `.git`.
- Corrected sentence: keep the block in `docs/guide/install.md` and make the other
  seven a link to it - today a change to the command has eight places to land.

## 2. Verified clean at `d6ab6d23` (do not redo)

- **Every documented command and flag resolves.** 67 distinct `teamwork <cmd> <sub>`
  paths extracted from `README.md`, `SKILL.md`, `CHANGELOG.md`, `docs/*.md`,
  `docs/guide/*.md` and `references/*.md` were replayed against
  `scripts/teamwork.py ... --help`: 0 rejected subcommands, 0 unknown flags. The two
  hits the scan reported are prose (`cli.md:103` "managed teamwork block",
  `CHANGELOG.md:814` a Python import), not commands.
- **Links and cross-references in the audited pages.** `scripts/teamwork.py links
  --project .` -> `# issues: 0` (no broken link, no invalid external URL, no bare
  URL, no missing back-link). This page keeps that at 0 because its `Related:`
  targets sit under `references/`, which the reciprocity rule exempts: pointing
  `Related:` at `docs/Team/Board.md` and `docs/Team/Decisions.md` instead adds 2
  missing back-links (the reviewed failure at `c1fa6839`), so the page links those
  two only inline.
- **The version surfaces that are checked agree.** `version.py` `1.5.9` =
  newest tag `v1.5.9` = npm `latest` `1.5.9` = newest GitHub Release `v1.5.9`;
  `check_release_consistency.py --offline` -> `R1 ok 20 tag(s)`, `R6 ok no version
  older than 1.5.9`, `R7 ok 20 tagged version(s) have exactly one CHANGELOG.md section`,
  `R9 ok every vX.Y.Z token names a tag`, `R10 ok 5 licence surface(s)`. The only red
  is R2 (F1).
- **`CHANGELOG.md:12`** names `[1.5.9] - 2026-11-15`, matching `version.py`.
- **The one-skill story is stated correctly.** `grep -rn teamwork-pi` over the
  in-scope pages returns only `CHANGELOG.md:954`, inside the historical 1.0.x entry;
  no current page offers a second skill.
- **`docs/Team/Release.md:9`** `python3 scripts/teamwork.py selftest` -> `5/5 checks
  passed`, exit 0, exactly as the page promises.

## 3. What this audit did not do

- No page was edited; the corrections above are one line each, for their owners.
- `docs/Team/Archive.md` was excluded by design (append-only history, not a claim).
- External claims (npm, GitHub, PyPI) were read live on 2026-11-15 via `npm view`,
  `gh release view` and the offline checker; no page's external prose was taken on
  trust.
- Not verified: `Plan.md:334`'s pinned test count (no `pytest` in the system
  interpreter), and the `--online` rules R3/R4/R5/R8, which need the network and were
  left to the release gate.
