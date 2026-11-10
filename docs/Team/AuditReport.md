# AUDIT REPORT - privacy and personal data

Owner: Security Auditor.
Related: [Project](Project.md) · [Architecture](Architecture.md) · [Risks](Risks.md).

**Conclusion.** The repository is clean on the shipped gate. `privacy_scan.py
--tree --history --allow .github/privacy-allow.txt` -> `PASS - 0 finding(s)`;
every commit identity reachable from `main` is a role mailbox
(`<role>@agents.nidvue.com`), so no personal author identity is published. The
earlier `R5` request for a history rewrite is **withdrawn, not deferred**: the
commit it targeted is not an object in this repository.

Without the allowlist the scanner still reports findings, and the difference is
exactly the allowlist. Every exempted value is one of two kinds, both documented
by shape in `.github/privacy-allow.txt`: a **path** (the harness install tree, the
harness session directory, one operator user name) or a **fabricated probe value**
a reviewer invented in order to prove the gate catches credentials, then quoted
into the archive as evidence. The probe values are credential-shaped on purpose -
that is what made them a good test - so this report does not claim the raw scan is
credential-free; it claims that nothing the scanner reports is a **live** secret,
and that no allowlist entry can hide one: a real token, key or password on an
exempted line is still reported by its own rule. The count is read from the run
and never pinned here, because the commit that documents a count raises it.

## 1. Scope and revision

| In scope | Out of scope |
|---|---|
| Tracked tree, git index, every blob reachable from every ref, commit author/committer/message metadata | The operator's global git config and machine (read, never published) |
| Packaging metadata, CITATION, CI workflows, community files | External services and accounts |
| A read-only walk of the whole working tree (untracked files included) | Third-party content inside ignored build caches |

- Revision audited: `main` at the tip `git rev-parse main` reported when this
  report was refreshed; the counts below are re-read on every refresh rather than
  pinned, because the commit that documents a count raises it.
- Scanned: every tracked file (`git ls-files | wc -l`), every blob reachable from
  every ref plus commit metadata, and a manual walk of the working tree excluding
  `.git`, `.pi`, `.venv` and caches.
- The repo path, home paths and mailbox domains are redacted here; the raw
  evidence is held in the gitignored team workspace (`.pi/…/Global/GlobalMemory.md`,
  `Ledger.jsonl`) and in the CI log of the failing `privacy` job.

## 2. Method and tool

- `scripts/privacy_scan.py` - stdlib only, three combining sources: `--tree`
  (`git ls-files`), `--staged` (`git ls-files -s` + `git cat-file`), `--history`
  (`git rev-list --objects --all` + `git cat-file --batch`, plus commit metadata).
  `--all` combines them; `--allow FILE` exempts documented patterns; `--json`
  emits machine-readable output.
- Nine rule families, plus one separate yield: personal email, retired private
  domain, absolute home path, agent-config paths, API token/known prefix,
  `.env`-style secret assignment, JSON/config secret value, standalone
  high-entropy secret, and a PEM private-key header (`TODO`/`FIXME` carrying a
  credential is yielded outside `RULES`).
- **The tool is itself published**, so it masks matched values by default,
  redacts the absolute repo root, and keeps the private domains out of plain
  text (reconstructed at runtime; extend with `TEAMWORK_PRIVATE_DOMAINS`). A
  privacy scanner must not become the leak. It has **no flag that prints a
  secret**: `--reveal` adds a stable `sha256:<12 hex>` fingerprint per finding,
  and `--reveal-to PATH` exports the raw values to a `0600` file the operator
  names (created `O_EXCL`, never overwritten, warned about on stderr). See
  section 7.1.
- Independent pass: the same rules were run over the full working tree
  (excluding `.git`, `.pi`, `.venv`, caches); plus manual review of
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
| F-1 | high | personal-email | author metadata of the pre-rebuild repository | `pin******.no` | **resolved - the commit is not an object in this repository**; `git cat-file -t <rev>` -> `Not a valid object name`, and no ref contains it |
| F-2 | high | private-domain | author metadata of the pre-rebuild repository | `z*****o` | **resolved - same commit**; every identity reachable from `main` is a role mailbox |
| F-3 | medium | hygiene | working tree `site/` | mkdocs build output | resolved - `site/` is ignored and untracked |
| F-4 | low | identity | `github.com` URLs in pyproject/mkdocs/README/workflows/CITATION | account handle `VisionPZ` | resolved - repository moved to `Nidvue/Teamwork` (2026-10-18) |
| F-5 | low | identity | operator global git config (not in repo) | personal name + mailbox | mitigated in-repo |
| F-6 | low | supply-chain | `.github/workflows/*.yml` | actions pinned to mutable major tags (`@v4`, `@v5`, `@v0`, `@v2`) | resolved - every action is pinned to a full commit SHA |
| F-7 | info | hygiene | `.pi/` and `.venv/` (gitignored) | home paths, private domain, personal mailboxes | residual risk |

F-1/F-2 root cause: the initial commit of the pre-rebuild repository was created
outside the team identity policy, so its author was the operator. That commit is
no longer an object here (see section 5), so the rows record a closed history.

`--tree` and `--staged` report nothing at all once
`--allow .github/privacy-allow.txt` is passed, and `--history` with the same flag
is also `0`. Without the flag all three are red, and the residue differs by mode:
`--tree`/`--staged` report only the allowlist file's own text and the scanner's
own tests (which must contain a credential-shaped probe, or they could not prove
the scanner catches one), while `--history` additionally reports the same families
as they appear in *already-committed* blobs - the archived evidence that quotes a
path, and the older revisions of the records that discuss the exemption. Those
blobs cannot be corrected without rewriting published history, which is why the
allowlist exists; the tree is where a new occurrence is fixed at source. The rule
is that a finding is either fixed at source or exempted in that file with a
written reason - never ignored.

## 5. Remediation

### Applied

| # | Action | Evidence |
|---|---|---|
| R1 | Repository-local git identity set to a **role** mailbox (`CEO <ceo@agents.nidvue.com>`) so an accidental plain `git commit` cannot inherit the operator identity; per-commit role identities (`git -c user.name=... -c user.email=...`) still override it | `git config --local user.email` -> `ceo@agents.nidvue.com`; `git log --format='%ae' main \| sort -u` -> every address is a role mailbox on `@agents.nidvue.com` |
| R2 | Engine default identity domain is the `agents.nidvue.com`, overridable with `TEAMWORK_IDENTITY_DOMAIN` | `src/teamwork/engine.py` `IDENTITY_DOMAIN`; `teamwork.py identity --role developer` -> `Developer <developer@agents.nidvue.com>` |
| R3 | Scanner masks all matched values, has no flag that prints a secret (`--reveal` prints a `sha256:` fingerprint; `--reveal-to` exports to a `0600` file), redacts the absolute root, and keeps private domains out of plain text | `scripts/privacy_scan.py`; `tests/unit/test_privacy_scan.py::test_reveal_never_prints_the_unmasked_secret`; see sections 7 and 7.1 |
| R4 | This report redacts every personal value so it cannot re-leak what it documents | this file passes `scripts/privacy_scan.py --tree` |
| R8 | The audit-manifest anchor is scoped to the workspace `TeamId`; a legacy manifest without one is historical and cannot make a new workspace look truncated | `ledger_verify`/`_audit_audit_trail` compare `team_id`; `tests/unit/test_ledger.py` covers same/foreign ids |

### R5 - withdrawn (was: rewrite the initial commit's author identity)

R5 asked the CEO for a history rewrite/force-push to remove a personal author
mailbox. **It is withdrawn rather than executed**: measured at this revision, the
commit it named is not an object in this repository (`git cat-file -t` -> `Not a
valid object name`), no ref contains it, and every author identity
reachable on `main` is a role mailbox. The repository was rebuilt after
the request was written, so the condition the request existed for is gone.

Recorded rather than deleted because a withdrawn request is still a fact about
the repository's history, and because the guard it asked for is the one that
matters: R1 sets the repository-local identity to a role mailbox, so a plain
`git commit` cannot inherit an operator identity, and the `privacy` CI job refuses
a push that introduces one. No future rewrite should be performed for this reason
alone; if a personal identity ever does reach a published commit, the request is
re-opened with the new object id as evidence.

### Recommended to the file owners

- **R6 (`.gitignore`, owner of repository hygiene): closed.** `site/` (mkdocs
  build output: third-party minified JS whose text carries other people's
  mailboxes) is ignored: `git check-ignore site` -> `site`, rc 0
  (`.gitignore` carries the rule). `dist/`, `.pytest_cache/`, `.mypy_cache/`,
  `.ruff_cache/`, `.venv/` and `.pi/` are ignored for the same reason. An earlier
  revision of this report said `site/` was *not* ignored; that was measured before
  the rule was added and is corrected here, matching F-3 in the findings table.
- **R7 (Release Engineer): done.** Every `uses:` in the three workflow files is
  pinned to a full 40-hex commit SHA with its `# vN` comment beside it, so a moved
  tag cannot inject code into the release job that holds `contents: write` and
  `id-token: write`; Dependabot's `github-actions` group keeps the pins current.
  This is the item F-6 records as resolved, and it is struck from the residual-risk
  table below so the report cannot say both.

## 6. Residual risk

| risk | owner | status |
|---|---|---|
| ~~Personal author metadata stays in history until R5 lands~~ - measured closed: no personal identity is reachable from any ref | CEO | **closed** (R5 withdrawn) |
| `.venv/` and `.pi/` contain the operator's home path, private domain and mailboxes; they are gitignored but a `git add -f` or a `.gitignore` edit would expose them | COO / all agents | accepted, monitored by `--tree` |
| ~~CI actions on mutable tags~~ - every `uses:` is pinned to a full commit SHA (F-6, R7) | Release Engineer | **closed** |
| A future commit made outside `teamwork.py commit` could use the global personal identity | all agents | mitigated by R1; the `privacy` CI job catches it on push |
| A genuine secret typed into a PR before CI runs is briefly public in the PR diff | all agents | use `--staged` before committing; GitHub push protection is external |

## 7. Verification

Exact commands and their real output at this revision (values masked by the
scanner by design; the count is never pinned because documenting it raises it):

```
$ python3 scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt
privacy_scan: PASS - 0 finding(s) in tree, history
$ echo $?
0

$ python3 scripts/privacy_scan.py --tree --allow .github/privacy-allow.txt
privacy_scan: PASS - 0 finding(s) in tree
$ echo $?
0

# without the allowlist, the residual families are visible and enumerated:
$ python3 scripts/privacy_scan.py --tree --history
privacy_scan: FAIL - <n> finding(s) in tree, history

$ git log --format='%ae' main | sort -u
<one role mailbox per role, every one @agents.nidvue.com>
```

The gap between the two runs is exactly the allowlist, and the allowlist is
readable: `.github/privacy-allow.txt` carries one anchored, fully escaped literal
per exempted value family, each with the reason it cannot be fixed at source. No
entry exempts a credential - a token, key or password on the same line is still
reported, and `tests/unit/test_privacy_scan.py` proves both the narrowness of each
entry and that a neighbouring value is still caught.

### 7.1 Code-scanning triage: `py/clear-text-logging-sensitive-data` (#2, #3)

Alerts **#2** and **#3** (severity `error`, rule
`py/clear-text-logging-sensitive-data`) were triaged at `main` @ `6f96366` and are
**false positives**: the value reaching stdout is the mask, not the secret.

| Alert | Reported line | Code path | Verdict |
|---|---|---|---|
| 3 | `scripts/privacy_scan.py:1132` | `print(json.dumps(report, ...))` in the `--json` branch | **false positive** |
| 2 | `scripts/privacy_scan.py:1143` | the `print(...)` in the human-readable report loop | **false positive** |

**What the analyzer sees.** CodeQL tracks a taint path from the matched text to a
`print` sink, because `main()` keeps a raw value in memory while looping over
findings (`match = finding.pop("match", None)`,
`scripts/privacy_scan.py:1088`). It then reports every `print` in the function
that is reachable from the same tainted dataflow - both alert lines are in the
reporting block, not at the taint source.

**Why that taint is not a leak.** The only value the report ever holds is
`finding["evidence"]`, and `make_finding` (`scripts/privacy_scan.py:570-582`)
sets it to `_mask(value)`:

```python
masked = _mask(value)
...
    "evidence": masked,
    "match": value,
```

`_mask` (`scripts/privacy_scan.py:498`) keeps at most 3 leading and 3 trailing
characters and replaces every other character with `*`. The raw value is stored
in a *separate* key, `match`, which is removed from every finding before the
report is built (`finding.pop("match", None)`, `scripts/privacy_scan.py:1088`),
so neither the `--json` branch (alert #3) nor the print loop (alert #2) can reach
it. `--reveal` adds only `_fingerprint(match)` - an unsalted truncated SHA-256
(`sha256:<12 hex>`) - and `--reveal-to PATH` is the only path that emits raw
values, into a `0600` file the operator names, never into the log.

**Measured proof.** In a scratch extraction of `HEAD`
(`git archive HEAD | tar -x -C .pi/SecScratch/fp`, re-initialised as a git repo
so `git ls-files` works) a synthetic credential was planted at runtime from parts
and committed:

```
$ python scripts/privacy_scan.py 2>&1 | grep leak_probe
leak_probe.txt:1: [critical/api-token] ghp*******************************WdE
leak_probe.txt:1: [critical/env-secret] ghp*******************************WdE
leak_probe.txt:1: [high/high-entropy-secret] Zx8***************************WdE
privacy_scan: FAIL - 3 finding(s) in tree

$ python scripts/privacy_scan.py --reveal 2>&1 | grep leak_probe
leak_probe.txt:1: [critical/api-token] ghp*******************************WdE (sha256:73bf57e5fcda)
leak_probe.txt:1: [critical/env-secret] ghp*******************************WdE (sha256:73bf57e5fcda)
leak_probe.txt:1: [high/high-entropy-secret] Zx8***************************WdE (sha256:c0681a3ace65)

$ python scripts/privacy_scan.py 2>&1            | grep -c '<planted value>'   -> 0
$ python scripts/privacy_scan.py --reveal 2>&1   | grep -c '<planted value>'   -> 0
$ python scripts/privacy_scan.py --json --reveal | grep -c '<planted value>'   -> 0

$ python scripts/privacy_scan.py --reveal-to .pi_reveal.txt
  stdout raw hits -> 0, stderr raw hits -> 0, file mode -> 600, file raw hits -> 2
```

`_mask` on the 37-character planted value yields a 37-character string with 31
`*` and 6 visible characters (`ghp`, `WdE`) - a prefix suffix pair that is still
`ghp_` followed by 31 unknown characters, i.e. not usable and not invertible.
The count is not reproduced here for the planted value because the scanner
correctly reports this file too.

**Dismissal reason.** The reported expressions print `finding["evidence"]`, which
`make_finding` has already replaced with `_mask(value)` while the raw match lives
in a separate key that is popped before either `print` runs - measured: zero
occurrences of a planted credential on stdout, stderr or in `--json` output in all
three modes, including `--reveal`.

## 8. Sources

- [git-filter-repo](https://github.com/newren/git-filter-repo) - accessed 2026-10-17
- [GitHub: removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) - accessed 2026-10-17
- [GitHub: security hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions) - accessed 2026-10-17
- Teamwork risk register R-2/R-3 (internal, `docs/Team/Risks.md`) - accessed 2026-10-17
