# AUDIT REPORT - privacy and personal data

Owner: Security Auditor.
Related: [Project](Project.md) · [Architecture](Architecture.md) · [Risks](Risks.md).

**Conclusion.** The tracked tree is clean: 111 working-tree files and the one
tracked history blob contain no personal data, credential or secret. The single
real leak is the **author identity of the initial commit** (`commit:e5efc5f`,
author email is a personal mailbox on a retired private domain). It cannot be
removed by editing files; it requires a history rewrite, which is a red-line
action owned by the CEO and is requested in section 5. The scanner therefore
exits `1` on `--history` until that rewrite lands. Sensitive values are redacted
in this published report (see the note before the findings table).

## 1. Scope and revision

| In scope | Out of scope |
|---|---|
| Tracked tree, git index, every blob reachable from every ref, commit author/committer/message metadata | The operator's global git config and machine (read, never published) |
| Packaging metadata, CITATION, CI workflows, community files | External services and accounts |
| A read-only walk of the whole working tree (untracked files included) | Third-party content inside ignored build caches |

- Revision audited: `main` at `e5efc5fcb6a6f94cd21fd752660a25d592fcf6b1` (single commit).
- Scanned: 3 tracked files, 1 history blob, 1 commit, plus 111 working-tree files in the manual walk.
- The repo path, home paths and mailbox domains are redacted here; the raw
  evidence is held in the gitignored team workspace (`.pi/…/Global/GlobalMemory.md`,
  `Ledger.jsonl`) and in the CI log of the failing `privacy` job.

## 2. Method and tool

- `scripts/privacy_scan.py` - stdlib only, three combining sources: `--tree`
  (`git ls-files`), `--staged` (`git ls-files -s` + `git cat-file`), `--history`
  (`git rev-list --objects --all` + `git cat-file --batch`, plus commit metadata).
  `--all` combines them; `--allow FILE` exempts documented patterns; `--json`
  emits machine-readable output.
- Eight rule families: personal email, retired private domain, absolute home
  path, API token/known prefix, `.env`-style secret assignment, standalone
  high-entropy secret, PEM private-key header, `TODO`/`FIXME` carrying a credential.
- **The tool is itself published**, so it masks matched values by default,
  redacts the absolute repo root, and keeps the private domains out of plain
  text (reconstructed at runtime; extend with `TEAMWORK_PRIVATE_DOMAINS`). A
  privacy scanner must not become the leak. It has **no flag that prints a
  secret**: `--reveal` adds a stable `sha256:<12 hex>` fingerprint per finding,
  and `--reveal-to PATH` exports the raw values to a `0600` file the operator
  names (created `O_EXCL`, never overwritten, warned about on stderr). See
  section 7.1.
- Independent pass: the same rules were run over the full working tree (111
  files, excluding `.git`, `.pi`, `.venv`, caches); plus manual review of
  `pyproject.toml`, `CITATION.cff`, `mkdocs.yml`, `.github/**` and the community files.

## 3. Threat model

| Datum | What a leak exposes |
|---|---|
| Personal email + private domain | Real identity, cross-account correlation, spear-phishing and credential-stuffing targets, PII under GDPR-style regimes |
| Commit author metadata | Permanent record in every clone/fork/mirror; deleting the file does not remove it; often harvested by scrapers |
| Absolute home path | OS username and machine layout; enables targeted local attacks and confirms the author's environment |
| API key / token (`sk-`, `ghp_`, `AIza`, `wandb_`, Slack, JWT `Bearer`) | Immediate account compromise, billing abuse, repository write access (supply-chain injection), data exfiltration |
| PEM private key | Host/TLS impersonation and traffic decryption |
| `.env`-style secret | Credential reuse across services; the classic forgotten-secret path |
| Credential in a `TODO`/`FIXME` | Usually a live secret left in code review notes |

Severity scale: **critical** credential/key, **high** identity/PII, **medium**
latent hygiene, **low** hardening. A high finding blocks the public release until
dispositioned (Architecture §9, `privacy` CI job).

## 4. Findings

> Evidence is masked (`pin******.no`) because this report ships publicly. The
> unmasked values are in the gitignored team workspace only.

| id | severity | rule | source / location | masked evidence | status |
|---|---|---|---|---|---|
| F-1 | high | personal-email | `history:commit` `commit:e5efc5f` (author email) | `pin******.no` | **open - history rewrite required** |
| F-2 | high | private-domain | `history:commit` `commit:e5efc5f` (author email) | `z*****o` | **open - history rewrite required** |
| F-3 | medium | hygiene | working tree `site/` | build output, 3.3 MB | resolved - `site/` is ignored |
| F-4 | low | identity | `github.com` URLs in pyproject/mkdocs/README/workflows/CITATION | account handle `VisionPZ` | resolved - repository moved to `Nidvue/Teamwork` (2026-10-18) |
| F-5 | low | identity | operator global git config (not in repo) | personal name + mailbox | mitigated in-repo |
| F-6 | low | supply-chain | `.github/workflows/*.yml` | actions pinned to mutable major tags (`@v4`, `@v5`, `@v0`, `@v2`) | resolved - every action is pinned to a full commit SHA |
| F-7 | info | hygiene | `.pi/` and `.venv/` (gitignored) | home paths, private domain, personal mailboxes | residual risk |

F-1/F-2 root cause: the initial commit was created outside the team identity
policy, so its author is the operator. The committer is `GitHub <noreply@github.com>`
(a service address, correctly allowlisted). The blob itself (LICENSE) is clean.

`--tree` and `--staged` report **0 findings**: the tracked tree and the index are
clean. `--history` reports the 2 findings above.

## 5. Remediation

### Applied

| # | Action | Evidence |
|---|---|---|
| R1 | Repository-local git identity set to a **role** mailbox (`CEO <ceo@agents.nidvue.com>`) so an accidental plain `git commit` cannot inherit the operator identity; per-commit role identities (`git -c user.name=... -c user.email=...`) still override it | `git config --local user.email` -> `ceo@agents.nidvue.com`; `git log --format='%an <%ae>'` -> `ceo@agents.nidvue.com`, `teamwork@agents.nidvue.com` |
| R2 | Engine default identity domain is the `agents.nidvue.com`, overridable with `TEAMWORK_IDENTITY_DOMAIN` | `src/teamwork/engine.py` `IDENTITY_DOMAIN`; `teamwork.py identity --role developer` -> `Developer <developer@agents.nidvue.com>` |
| R3 | Scanner masks all matched values, has no flag that prints a secret (`--reveal` prints a `sha256:` fingerprint; `--reveal-to` exports to a `0600` file), redacts the absolute root, and keeps private domains out of plain text | `scripts/privacy_scan.py`; `tests/unit/test_privacy_scan.py::test_reveal_never_prints_the_unmasked_secret`; see sections 7 and 7.1 |
| R4 | This report redacts every personal value so it cannot re-leak what it documents | this file passes `scripts/privacy_scan.py --tree` |
| R8 | The audit-manifest anchor is scoped to the workspace `TeamId`; a legacy manifest without one is historical and cannot make a new workspace look truncated | `ledger_verify`/`_audit_audit_trail` compare `team_id`; `tests/unit/test_ledger.py` covers same/foreign ids |

### Requested from the CEO (red-line, not executed by the Security Auditor)

**R5 - rewrite the initial commit to remove the personal author identity.** Only
the CEO may perform a history rewrite/force-push, and only under the recorded
governance decision `D-20261017-CEO` (Project assumption 1). Recommended safe
sequence, because the repository has a single commit that contains only `LICENSE`:

```sh
# 1. re-create the same tree with the neutral identity
git -c user.name="Reviewer" -c user.email="reviewer@agents.nidvue.com" \
    commit --amend --no-edit --reset-author
# 2. verify, then authorise the force-push as CEO
python3 scripts/privacy_scan.py --tree --history   # must print 0 findings
# git push --force-with-lease origin main          # CEO-only, after authorisation
```

If more commits ever exist, use
[git-filter-repo](https://github.com/newren/git-filter-repo) with a `--mail-map`
instead of an amend. After any rewrite, every clone/fork must re-clone and the
`privacy` CI job must be green before the `v1.0.0` tag.

### Recommended to the file owners

- **R6 (`.gitignore`, owner of repository hygiene):** add `site/`. It is mkdocs
  build output, currently **not** ignored (`git check-ignore site` -> exit 1).
  Committing it would publish 3.3 MB of third-party minified JS (whose text
  contains other people's mailboxes) and would fail `--tree`. `dist/`,
  `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.venv/` and `.pi/` are
  already ignored.
- **R7 (Release Engineer):** pin GitHub Actions to full commit SHAs (or rely on
  the existing Dependabot `github-actions` group) so a moved tag cannot inject
  code into the release job that holds `contents: write` and `id-token: write`.

## 6. Residual risk

| risk | owner | status |
|---|---|---|
| Personal author metadata stays in history until R5 lands; every current clone keeps it | CEO | open, blocking release |
| `.venv/` and `.pi/` contain the operator's home path, private domain and mailboxes; they are gitignored but a `git add -f` or a `.gitignore` edit would expose them | COO / all agents | accepted, monitored by `--tree` |
| CI actions on mutable tags | Release Engineer | open (R7) |
| A future commit made outside `teamwork.py commit` could use the global personal identity | all agents | mitigated by R1; the `privacy` CI job catches it on push |
| A genuine secret typed into a PR before CI runs is briefly public in the PR diff | all agents | use `--staged` before committing; GitHub push protection is external |

## 7. Verification

Exact command and real output (values masked by the scanner by design):

```
$ python3 scripts/privacy_scan.py --tree --history
commit:e5efc5fcb6a6:1: [high/private-domain] z*****o  author email
commit:e5efc5fcb6a6:1: [high/personal-email] pin******.no  author email
privacy_scan: FAIL - 2 finding(s) in tree, history
$ echo $?
1

$ python3 scripts/privacy_scan.py --tree
privacy_scan: PASS - 0 finding(s) in tree
$ echo $?
0
```

JSON form (same run; `root` is the basename and values are masked):

```json
{
  "scanner_version": "1.0.0",
  "root": "Teamwork",
  "modes": ["tree", "history"],
  "identity_domain": "agents.nidvue.com",
  "scanned": {"tracked_files": 3, "staged_files": 0, "history_blobs": 1, "commits": 1},
  "finding_count": 2,
  "findings": [
    {"rule": "private-domain", "severity": "high", "source": "history:commit",
     "location": "commit:e5efc5fcb6a6:1", "evidence": "z*****o", "detail": "author email"},
    {"rule": "personal-email", "severity": "high", "source": "history:commit",
     "location": "commit:e5efc5fcb6a6:1", "evidence": "pin******.no", "detail": "author email"}
  ],
  "by_severity": {"high": 2},
  "by_rule": {"private-domain": 1, "personal-email": 1}
}
```

After R5, the acceptance command for AC-5 must print `PASS` and exit `0`:

```
python3 scripts/privacy_scan.py --tree --history
```

Rule coverage was proven against a synthetic fixture in the gitignored scratch
tree: 20 findings spanning all eight rule families (`api-token`, `env-secret`,
`high-entropy-secret`, `home-path`, `personal-email`, `private-domain`,
`private-key`, `todo-credential`). `--allow` was proven to suppress exactly one
matched value, and a malformed allow regex exits `2`.

### 7.1 Code-scanning remediation: `py/clear-text-logging-sensitive-data`

Two CodeQL alerts (numbers **1** and **2**, severity `high`, rule
`py/clear-text-logging-sensitive-data`) were open on `refs/heads/main` against
`scripts/privacy_scan.py`. Both were **true positives, not dismissed**.

| Alert | Reported line | Code path |
|---|---|---|
| 1 | `scripts/privacy_scan.py:1008` | `shown = finding.get("match", finding["evidence"]) if args.reveal else finding["evidence"]` in the non-JSON report loop |
| 2 | `scripts/privacy_scan.py:1018` | the `print(...)` that emitted `shown` |

**Why it was a real finding.** The value is masked by `_mask`
(`scripts/privacy_scan.py:489`, `_mask`) so a failing CI log cannot republish a secret -
that intent is stated in the module docstring. `--reveal`
(`scripts/privacy_scan.py:1012` before the fix: line 948) bypassed it and sent the raw `match` to stdout.
stdout is a broadcast sink, not a terminal: `.github/workflows/ci.yml:201` and
`.github/workflows/docs.yml:68` run the scanner in Actions where stdout is a
retained, world-readable log; operators routinely pipe it through `tee`; and
shell scrollback is captured by session recorders. A control that relies on the
operator *not* redirecting output is not a control at all - and the very next
person to debug a CI failure has an incentive to do exactly that.

**Fix (option A).** The unmasked value can no longer reach a log:

- `--reveal` now appends a stable, unsalted `sha256:<12 hex>` fingerprint
  (`_fingerprint`, `scripts/privacy_scan.py:497`) to each finding line.
  Enough to distinguish findings and confirm a rotation; not usable as the
  credential and does not embed any prefix of it.
- `--reveal-to PATH` (`write_reveal_file`, `scripts/privacy_scan.py:509`)
  preserves the remediation workflow: raw values go to a file the operator
  explicitly names, created `O_EXCL` with mode `0600`, one
  `location<TAB>rule<TAB>fingerprint<TAB>value` line per finding, a stderr
  `WARNING` naming the file, an existing path refused as a usage error (exit 2),
  and the partial file unlinked on error. `finding["match"]` is popped from every
  finding before the report is built, so `--json` cannot leak it either.
- `SCANNER_VERSION` bumped `1.2.0` -> `1.3.0`: the output contract changed.

**Regression tests** (4 new, 51 total in `tests/unit/test_privacy_scan.py`):
`test_reveal_never_prints_the_unmasked_secret`,
`test_plain_report_omits_the_fingerprint`,
`test_reveal_to_writes_a_0600_file_and_keeps_the_log_clean`,
`test_reveal_to_refuses_to_clobber_an_existing_file`.

**Mutation proof.** `git show HEAD:scripts/privacy_scan.py` restored in place and
the suite re-run: 3 failed / 48 passed, the primary failure being

```
assert planted not in out, "the unmasked secret must not reach stdout"
E   AssertionError: the unmasked secret must not reach stdout
E   assert 'ghp_0123...opqrstuvwxyz' not in 'leak.py:1: ...s) in tree\n'
E     the planted credential is contained here:
E       leak.py:1: [critical/api-token] <the planted credential>
```

The planted value is synthetic - `ghp_` followed by the lowercase alphabet - and
this report does not reproduce it in full, because the scanner (now correctly)
reports this file too. With the fix restored: 51 passed.

**Residual risk.** `--reveal-to` still creates a plaintext secrets file on disk,
by design - the operator asked for it. Mitigations: mode `0600`, no overwrite,
no default path (it must be named), an explicit warning, and one-line-per-finding
formatting. Backup/snapshot copies and an operator who commits or pastes the file
remain outside the tool's control; the warning and this section are the
compensating controls. CI never passes `--reveal-to`.

## 8. Sources

- [git-filter-repo](https://github.com/newren/git-filter-repo) - accessed 2026-10-17
- [GitHub: removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) - accessed 2026-10-17
- [GitHub: security hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions) - accessed 2026-10-17
- Teamwork risk register R-2/R-3 (internal, `docs/Team/Risks.md`) - accessed 2026-10-17
