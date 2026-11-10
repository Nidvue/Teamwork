# AUDIT REPORT - privacy and personal data

Owner: Security Auditor.
Related: [Project](Project.md) · [Architecture](Architecture.md) · [Risks](Risks.md).

## Status

**Superseded in part - read this first.** This is a dated measurement, not a
live dashboard. It was written against the revision whose local history still
carried the disclosed commit, and its conclusions have since been closed:

- **R5 (the history rewrite) is DONE, not open.** The CEO performed the
authorized rewrite of the unpublished local history; `docs/Team/Project.md` gap
G-8 records it as **closed**. Section 5's R5 table, and the R5 paragraphs below,
are the pre-rewrite state kept as evidence of what was measured and why.
- **The recorded findings are closed too.** F-1 and F-2 (the disclosed commit)
  closed with R5; F-9 (the ruling's own evidence line) closed when the entry was
  rewritten to name the rule instead of the value.
- **The gate is green now.** `python3 scripts/privacy_scan.py --tree --history
  --allow .github/privacy-allow.txt` -> `PASS - 0 finding(s)`.

The findings, the method and the threat model stand as the record of the audit
that justified the rewrite. Where this file says "is red" or "is open" or
"remains to be done", read it as "was true at the audited revision" - every such
statement is a measurement of that revision, not a task still owed.

**Conclusion at the audited revision.** The **tree** was clean, the **published**
history was clean, and the **local** history was **red**. The red is caused by one commit, and that commit is
in the forge. Three facts, kept separate, because they have different answers
and different remediations:

1. **Reachability.** The commit is **not reachable from any published ref** and
   is **not in the published history**: `git ls-remote origin` -> 40 refs, none
   advertising it; it is not an ancestor of published `origin/main` nor of the
   published `refs/pull/23/head`; a plain anonymous clone does not contain it; a
   truncated-SHA fetch is refused. The published side is clean: a full clone with
   every `refs/pull/*/head` fetched, swept object by object, finds no address, no
   name and no private domain.
2. **Service.** The forge nevertheless **serves the object anonymously**, with no
   authentication, to anyone who asks for that SHA: its API returns it with HTTP
   200 and the **author name and email in the payload**, its commit page returns
   HTTP 200 and renders the author name, and its PR #23 record names it as
   `merge_commit_sha` - a field the ordinary enumerable `GET /pulls` list also
   serves. The object is **retained** by the forge and served by SHA.
3. **Disclosure.** The author identity is therefore **already disclosed to anyone
   who asks for that SHA, and it cannot be un-disclosed**. Discoverability was
   measured **absent** (the forge's commit search returns it by neither author
   nor SHA, a truncated-SHA fetch is refused, a plain clone does not contain it),
   so this report makes no claim of broadcast, of public discovery or of a leak:
   it says the identity is **disclosed to anyone who requests that
   SHA**. What is **not** disclosed, and never was, is the identity of the
   account that opened the pull request: that account's public profile carries the
   display name but a null email, and the commit page renders the name but not the
   address.

**R5 was open at the audited revision - it is now closed.** The local history
rewrite was required because it protects the published history from carrying the
identity forward. It does **not** undo the disclosure, and this report does not
claim it does. The rewrite is a red line that needed the **user's** authorization
through the CEO; it was carried by `ceo T-0003` and performed under that
authorization (`docs/Team/Project.md` gap G-8). The text that follows is the
request as it stood before the rewrite.

**Words.** "Published" is reserved for objects reachable from a published ref. The
word for the object here is **retained** (the forge retains it and serves it by
SHA); the word for the identity is **disclosed** (disclosed at the object level).
The ruling that fixes this wording is `D-20261021-Reviewer-1` (tribunal, dispute
D-0003 round 3/3). It is cited by id and not by link: the decision entry is
carried on the Reviewer's own PR and is not on `main` at the time of writing, so
linking to it here would be a broken link until it lands. The dispute record
itself is in the team's local, gitignored tree
(`.pi/Teamwork/Teams/Teamwork/Disputes.md`, dispute D-0003) and is not a
committed document.

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
and never pinned here, because the commit that documents a count raises it
(D-20261019-CEO-15, in `docs/Team/Decisions.md`).

## 1. Scope and revision

| In scope | Out of scope |
|---|---|
| Tracked tree, git index, every blob reachable from every ref, commit author/committer/message metadata | The operator's global git config and machine (read, never published) |
| Packaging metadata, CITATION, CI workflows, community files | External services and accounts |
| A read-only walk of the whole working tree (untracked files included) | Third-party content inside ignored build caches |

- **Two surfaces are measured separately**, because they have different answers
  and different remediations: the **local** repository (the branch that is about
  to be pushed) and the **published** repository (every ref the forge holds,
  measured in a clone of the forge). The published surface is clean; the local
  history is red. A single "the repository is clean" sentence cannot carry both,
  which is why this report states them in a table.
- Revision audited: `main` at the tip `git rev-parse main` reported when this
  report was refreshed; the counts below are re-read on every refresh rather than
  pinned, because the commit that documents a count raises it. The same applies
  to the commit ids named here: the state is stated, the id is given as the
  evidence for that state, and no id is pinned as a permanent fact.
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
- **The tool is itself published**, so it keeps the matched value **out of the
  report entirely**, redacts the absolute repo root, and keeps the private
  domains out of plain text (reconstructed at runtime; extend with
  `TEAMWORK_PRIVATE_DOMAINS`). A privacy scanner must not become the leak. It
  has **no flag that prints a secret**: the report row names the *rule*, the raw
  value lives in an attribute of the finding that no reporting sink can reach,
  `--reveal` adds a stable `sha256:<12 hex>` fingerprint per finding, and
  `--reveal-to PATH` exports the raw values to a `0600` file the operator names
  (created `O_EXCL`, never overwritten, warned about on stderr). See section 7.1.
- Independent pass: the same rules were run over the full working tree
  (excluding `.git`, `.pi`, `.venv`, caches); plus manual review of
  `pyproject.toml`, `CITATION.cff`, `mkdocs.yml`, `.github/**` and the community files.
- **The published surface is measured in a clone of the forge**, not from the
  local `origin/*` refs, which can be stale: a plain anonymous clone
  (`credential.helper=` empty, pristine `HOME`) with
  `+refs/pull/*/head:refs/remotes/origin/pull/*` fetched, which pulls in every
  `refs/pull/*/head` the forge holds. The shipped gate is run there over the
  whole fetched ref set, and the object store is swept blob by blob for the
  operator's address, name and private domain (the scanner has **no**
  personal-name rule, so a name-only leak would be invisible to it). The clone
  and its scratch are removed when the measurement is done; nothing outside this
  repository's own `.pi/` tree is used as a working directory.
- **The measure states the question it answers.** A clone of the advertised refs
  measures **reachability**: an object no ref advertises is not fetched, so
  `git cat-file -t <rev>` in such a clone answers "is this object reachable from
  a published ref", **not** "does this object exist on the forge". The forge's
  own service is measured separately, by asking it for the object by SHA. An
  earlier revision of this report used the reachability measure to make an
  existence claim, and that claim was false; see section 7.2.

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

> Evidence is written out as a shape, not as a value (`pin******.no`), because
> this report ships publicly. The scanner itself does not mask-and-print: it
> keeps the matched value out of the report entirely (section 7.1). The unmasked
> values are in the gitignored team workspace only.

| id | severity | rule | source / location | masked evidence | status |
|---|---|---|---|---|---|
| F-1 | high | personal-email | author metadata of the forge squash merge of PR #23, on local `main` | `pin******.no` | **CLOSED by R5** (the authorized rewrite, `Project.md` G-8) - three facts, in this order. (1) The commit is **not reachable from any published ref and is not in the published history** (`git ls-remote origin` -> 40 refs, none advertising it; not an ancestor of published `origin/main` nor of the published `refs/pull/23/head`; a plain anonymous clone does not contain it; a truncated-SHA fetch is refused), and the published side is clean. (2) The forge nevertheless **serves it anonymously by SHA**, with no authentication: its API returns HTTP 200 with the **author name and email in the payload**, its commit page returns HTTP 200 and renders the author name, and the PR #23 record names it as `merge_commit_sha` (also served by the ordinary enumerable `GET /pulls` list). (3) The author identity is therefore **already disclosed to anyone who requests that SHA**, and it cannot be un-disclosed. Discoverability was measured absent, so this is not a claim of broadcast, of public discovery or of a leak. Remediation: R5 (below) - the local history rewrite, which protects the published history from carrying the identity forward but does not undo the disclosure; it needs the user's authorization (ceo T-0003) |
| F-2 | high | private-domain | same commit, same author field | `z*****o` | **CLOSED by R5** - same commit and same remediation as F-1 |
| F-3 | medium | hygiene | working tree `site/` | mkdocs build output | resolved - `site/` is ignored and untracked (`git check-ignore -v site/` -> `.gitignore`: `site/`; `git ls-files site` -> nothing) |
| F-4 | low | identity | `github.com` URLs in pyproject/mkdocs/README/workflows/CITATION | account handle `VisionPZ` | resolved - repository moved to `Nidvue/Teamwork` (2026-10-18); no tracked file outside `docs/Team/Archive.md` and this report carries the handle |
| F-5 | low | identity | operator global git config (not in repo) | personal name + mailbox | mitigated in-repo |
| F-6 | low | supply-chain | `.github/workflows/*.yml` | actions pinned to mutable major tags (`@v4`, `@v5`, `@v0`, `@v2`) | resolved - every action is pinned to a full commit SHA (`grep -hoE 'uses: [^ ]+' .github/workflows/*.yml \| grep -vE '@[0-9a-f]{40}$'` -> nothing) |
| F-7 | info | hygiene | `.pi/` and `.venv/` (gitignored) | home paths, private domain, personal mailboxes | residual risk |
| F-8 | info | boundary | the published side of the same object | no address, no name, no private domain | **measured boundary, not a finding of a leak** - the published side is clean and the object is **not reachable from any published ref**, and the content of the offending commit is already published safely under the role mailbox (identical tree, and that role-mailbox commit **is** in `origin/main`). So the published history carries no personal identity, and the disclosure is of the **identity** of the retained object, not of its content. This row is what keeps the risk proportionate: it bounds F-1 and F-2, and it is the reason the report distinguishes *reachability*, *service* and *disclosure* instead of compressing them into one adjective |
| F-9 | high | personal-email + private-domain | the **decision record of the ruling that governs this report** (`D-20261021-Reviewer-1`), on the Reviewer's own unmerged branch | `pin******.no` | **CLOSED** - the decision entry names the rule, not the value. Verified: `grep -nE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' docs/Team/Decisions.md | grep -v 'agents\.nidvue\.com'` prints nothing, while the same pattern over a control line carrying an address prints it (`grep -cE` -> 1). Note the earlier revision of this row cited an ERE with `\w`, which GNU grep does not expand, so that command matched nothing and proved nothing. **Measured at the audited revision, and it is a NEW occurrence, not the old one.** The decision entry quotes the operator's address **literally** in its `evidence:` line, and the commit that carries it quotes the same address in its **commit message**. Measured on that branch's tree: the shipped tree scan is `FAIL` (the address, the private domain and two high-entropy false positives on the same line), where `main` is `PASS`. The occurrence is in the record that documents this very disclosure, so it reproduces the exact failure the gate exists to catch. It is not on `main` and not on any published ref, so it is **not published** and it is **not disclosed** to anyone who does not already have that branch - but it will become published the moment the ruling is merged, and the shipped `privacy` CI job will refuse that push. **Remediation: the decision entry must name the rule, not the value** - the same treatment the archive mask already gives the review records (`docs/Team/Archive.md` carries `[redacted-personal-email]` where it used to carry the value) - and the commit message must do the same. Owner: the Reviewer who wrote the entry, with the CEO as the routing lane. This report does not edit that file; it is not in this lane's scope |

F-1/F-2 root cause: the author of the squash-merged commit is the **account that
was signed in to the forge** when the merge button was pressed, not the role
mailbox the team commits under. A previous revision of this report recorded
these rows as resolved on the measured ground that the commit was "not an object
in this repository", and a later revision recorded them as open on the ground that
the forge did not hold the object. **Both claims were wrong, and both were
reachability claims used as existence claims**: a clone of the advertised refs
does not fetch an object that no ref advertises, so `git cat-file -t <rev>` in
such a clone measures reachability, not existence on the forge. The object
exists on the forge and is served by it (F-1, fact 2). The re-measurement is in
section 7.2, and the request that was withdrawn on the old measurement is
re-opened as R5.

The mode-by-mode residue, re-measured **at the audited revision**: `--tree` and
`--staged` reported nothing at all once `--allow .github/privacy-allow.txt` was
passed. `--history` with the same flag was red then (it is green since R5), and
the residue was the two causes above - older blob revisions of
`docs/Team/Archive.md` that quote the address inside a quoted-evidence field, and
the author field of the squash-merge commit. Without the allowlist the tree is
also red, and its residue is the allowlist file's own text, the scanner's own
tests (which must contain a credential-shaped probe, or they could not prove the
scanner catches one) and two home paths quoted as evidence in
`docs/Team/Decisions.md`. Those blobs cannot be corrected without rewriting
history, which is why the allowlist exists; the tree is where a new occurrence is
fixed at source. The rule is that a finding is either fixed at source or exempted
in that file with a written reason - never ignored.

## 5. Remediation

### Applied

| # | Action | Evidence |
|---|---|---|
| R1 | Repository-local git identity set to a **role** mailbox (`CEO <ceo@agents.nidvue.com>`) so an accidental plain `git commit` cannot inherit the operator identity; per-commit role identities (`git -c user.name=... -c user.email=...`) still override it | `git config --local user.email` -> `ceo@agents.nidvue.com`; `git log --format='%ae' main \| sort -u` -> every address is a role mailbox on `@agents.nidvue.com`, **except** the one author of the squash-merged commit (F-1) |
| R2 | Engine default identity domain is the `agents.nidvue.com`, overridable with `TEAMWORK_IDENTITY_DOMAIN` | `src/teamwork/engine.py` `IDENTITY_DOMAIN`; `teamwork.py identity --role developer` -> `Developer <developer@agents.nidvue.com>` |
| R3 | The scanner keeps the matched value **out of the report entirely** (it lives in an attribute of the finding, never in a report item), has no flag that prints a secret (`--reveal` prints a `sha256:` fingerprint; `--reveal-to` exports to a `0600` file), redacts the absolute root, and keeps private domains out of plain text | `scripts/privacy_scan.py`; `tests/unit/test_privacy_scan.py::test_reveal_never_prints_the_unmasked_secret`; see sections 7 and 7.1 |
| R4 | This report redacts every personal value so it cannot re-leak what it documents | this file passes `scripts/privacy_scan.py --tree` |
| R8 | The audit-manifest anchor is scoped to the workspace `TeamId`; a legacy manifest without one is historical and cannot make a new workspace look truncated | `ledger_verify`/`_audit_audit_trail` compare `team_id`; `tests/unit/test_ledger.py` covers same/foreign ids |

### R5 - CLOSED (was: withdrawn, then re-opened, then performed)

R5 asked the CEO for a **rewrite of the local history** so that a personal author
mailbox stops being reachable from the branch that was about to be pushed. **It
was open at the audited revision and has since been performed** under the user's
authorization (`docs/Team/Project.md` gap G-8). The ruling
`D-20261021-Reviewer-1` changed what the report says about the object; it did not
change whether the rewrite was needed.

**The three facts, restated as the state of the request.** Each row is the
measure and what it answers.

| Measure | Result | What it answers |
|---|---|---|
| `git ls-remote origin` | 40 refs, none advertising the object | no published ref reaches it |
| `git merge-base --is-ancestor <rev> origin/main` | rc 1 | it is not in the published `main` history |
| `git merge-base --is-ancestor <rev> refs/pull/23/head` | rc 1 | it is not in the published pull-request head |
| plain anonymous clone, then `git cat-file -t <rev>` | rc 128 - the object is not in the clone | a clone of the advertised refs does not carry it (**reachability**, not existence) |
| same clone, `git fetch --no-tags origin <full-sha>` | rc 0, the object is present and carries the operator identity | the forge **will serve the object by SHA** |
| same clone, `git fetch origin <truncated-sha>` | refused - "couldn't find remote ref" | the forge will not serve it by a partial SHA |
| `GET /repos/<owner>/<repo>/commits/<full-sha>` | HTTP 200, **author name and email in the payload** | the forge serves the object anonymously, with the identity attached |
| `GET /repos/<owner>/<repo>/pulls/23` and `GET /pulls?state=all` | both carry it as `merge_commit_sha` | the SHA is served by an ordinary, enumerable API call, not only by a direct GET |
| `GET /search/commits` by author, by `sha:` and by bare sha | `total_count 0` each | the object is **not discoverable** by a reader who does not already have the SHA |
| `GET /users/<login>` | display name present, email **null** | the account that opened the pull request is not identified by an address |
| full clone + `+refs/pull/*/head`, object-by-object sweep | no address, no name, no private domain | the **published** side is clean |
| `git rev-parse <rev>^{tree} <role-mailbox-rev>^{tree}` | the same tree id | the **content** is already published under the role mailbox; the disclosure is of the **identity** |

**What the request is for.** Rewrite the local commits so that the personal
address is not reachable from the branch that is about to be pushed: rebase the
local branches onto the **published** tip, rewrite the archive blob revisions
that quote the address so the value is redacted, and re-point the commit ids
that `docs/Team/Archive.md`, `docs/Team/Decisions.md` and the ledger cite. No
published ref, tag or release changes, and nothing is force-pushed.

**What the request is not, and cannot be.** The rewrite **does not undo the
disclosure**. The identity is already disclosed at the object level: the forge
serves the retained object with the name and the address attached, and that fact
cannot be un-disclosed by anything this team does to its own history. What the
rewrite buys is that the **published history does not carry the identity
forward** - it stops the next push from adding the address to the published
refs, and it removes the address from the local archive blob revisions. The
disclosure and the rewrite are two different problems, and only the second one is
in this team's hands.

**Authorization: the user's, through the CEO.** `AGENTS.md`'s red-line list names
"history rewrite" without a *published* qualifier, and the conservative reading
applies; the PUSH POLICY names "force-push, published-history rewrite and
retagging" as needing the CEO's explicit authorization. The request therefore
needs the **user's** authorization, and it is carried by `ceo T-0003`. This
report records the request and the evidence; it does not authorize the rewrite
and does not perform it. The base of the rewrite is fixed by
D-20261020-CEO-8 (in `docs/Team/Decisions.md`): the **published** tip, not the
local tip or the local merge base.

**What holds regardless of the rewrite.** R1 sets the repository-local identity
to a role mailbox, so a plain `git commit` cannot inherit an operator identity;
the published side carries the **committer guard** (a CI job that fails when an
account is stamped into `main`), so a host merge button cannot recreate this
condition unnoticed; and the published history carries no personal identity
today. The `privacy` CI job refuses a push that introduces a personal identity.

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
- **R9 (CEO / operator): the forge's pull-request merge preview.** The forge
  creates a `refs/pull/<n>/merge` preview ref for every open pull request,
  authored with the account that opened it, and that ref is publicly readable -
  so while a pull request opened from the operator's personal account is open,
  its merge preview carries the operator's personal identity. The shipped gate
  deliberately does **not** report it: a forge merge preview is a server-side
  artifact, not a commit the team made, and failing the gate on it would make
  every open pull request red. The remedy is the account the pull requests are
  opened from, not the gate. Read the live state with
  `gh pr list --repo Nidvue/Teamwork --state open --json number,author`; at the
  time of this refresh no pull request is open, so no such ref is live.

## 6. Residual risk

| risk | owner | status |
|---|---|---|
| **The author identity of the retained commit is disclosed at the object level and cannot be un-disclosed.** (1) The commit is **not reachable from any published ref and is not in the published history** (`git ls-remote origin` -> 40 refs, none advertising it; not an ancestor of published `origin/main` nor of `refs/pull/23/head`; a plain anonymous clone does not contain it; a truncated-SHA fetch is refused) and the published side is clean (no address, no name, no private domain in the swept reachable objects). (2) The forge nevertheless **serves the object anonymously by SHA**, with no authentication: its API returns HTTP 200 with the **author name and email in the payload**, its commit page returns HTTP 200 and renders the author name, and the PR #23 record names it as `merge_commit_sha` (also served by the ordinary enumerable `GET /pulls` list). (3) The identity is therefore **already disclosed to anyone who asks for that SHA** and cannot be un-disclosed; discoverability was measured absent, so no claim of broadcast, of public discovery or of a leak is made here. The **local history rewrite (R5) was required** - it protects the published history from carrying the identity forward - **but it does not undo the disclosure**. What the operator decides about the identity itself is outside this team's hands | CEO | **residual** - R5 was performed under the user's authorization (`Project.md` G-8), so the published history will not carry the identity forward; the disclosure already made at the object level is not reversible by the team |
| `.venv/` and `.pi/` contain the operator's home path, private domain and mailboxes; they are gitignored but a `git add -f` or a `.gitignore` edit would expose them | COO / all agents | accepted, monitored by `--tree` |
| ~~CI actions on mutable tags~~ - every `uses:` is pinned to a full commit SHA (F-6, R7) | Release Engineer | **closed** |
| A future commit made outside `teamwork.py commit` could use the global personal identity | all agents | mitigated by R1; the `privacy` CI job and the published-side committer guard catch it on push |
| A genuine secret typed into a PR before CI runs is briefly public in the PR diff | all agents | use `--staged` before committing; GitHub push protection is external |
| The decision record of the ruling that governs this report quoted the operator's address literally (F-9), in the record's own `evidence:` line and in the commit message that carried it | Reviewer (author of the entry), routed by the CEO | **closed** - the entry now names the rule instead of the value, and the shipped `privacy` gate passes on the tree |

## 7. Verification

Exact commands and their real output at this revision (values masked by the
scanner by design; the count is never pinned because documenting it raises it).

### 7.0 The three surfaces, measured separately

**Local tree - clean.**

```
$ python3 scripts/privacy_scan.py --tree --allow .github/privacy-allow.txt
privacy_scan: PASS - 0 finding(s) in tree
$ echo $?
0
```

**Local history - red.** The number is read from the run, never pinned.

```
$ python3 scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt
privacy_scan: FAIL - <n> finding(s) in tree, history
$ echo $?
1
```

The residue is the two causes, and the scanner's own JSON names them:

```
$ python3 scripts/privacy_scan.py --history --allow .github/privacy-allow.txt --json
  history:blob   docs/Team/Archive.md:<line>  personal-email / private-domain
  history:blob   docs/Team/Archive.md:<line>  todo-credential
  history:commit commit:<rev>:1                personal-email / private-domain   <- the author field
```

**Published history - clean.** Measured in a clone of the forge (method in
section 2), over every ref the forge holds, including every `refs/pull/*/head`:

```
$ python3 scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt
privacy_scan: PASS - 0 finding(s) in tree, history
$ echo $?
0

$ git log --all --remotes --format='%ae|%ce' | tr '|' '\n' | sort -u
<one role mailbox per role, every one @agents.nidvue.com, plus the allowlisted
 service mailboxes the forge and dependabot use>
```

A blob sweep of every object reachable from every published ref finds no
operator address, no operator name and no private domain.

**Published `main` in CI - green**, including the `privacy scan (tree + history)`
job: `gh run list --repo Nidvue/Teamwork --branch main`.

### 7.1 The retained object: reachability, service, disclosure

The three facts, each with the command that produces it. **Reachability** and
**service** answer different questions and are measured by different means; a
clone of the advertised refs answers only the first.

**Reachability - the ref fact.**

```
$ git ls-remote origin | wc -l
40
$ git ls-remote origin | grep -c 3f4981d
0

$ git merge-base --is-ancestor <rev> origin/main; echo $?
1
$ git merge-base --is-ancestor <rev> refs/pull/23/head; echo $?
1
```

**Service - the object fact.** Measured by asking the forge for the object, in a
clone with `credential.helper=` empty and a pristine `HOME`:

```
$ git cat-file -t <rev>                          # in a plain anonymous clone
fatal: git cat-file: could not get object info    # rc 128 - the clone does not carry it
$ git fetch --no-tags origin <truncated-sha>
fatal: couldn't find remote ref <truncated-sha>  # rc 128 - a partial SHA is refused
$ git fetch --no-tags origin <full-sha>
rc 0 - the object is now present
$ git log -1 --format='%an <%ae>' FETCH_HEAD
<the operator's name and address>
```

The forge's own endpoints, asked for that SHA without authentication:

```
$ curl -s -o /dev/null -w '%{http_code}' https://api.github.com/repos/<owner>/<repo>/commits/<full-sha>
200
$ curl -s -o /dev/null -w '%{http_code}' https://github.com/<owner>/<repo>/commit/<full-sha>
200
$ curl -s https://api.github.com/repos/<owner>/<repo>/pulls/23 | grep merge_commit_sha
"merge_commit_sha": "<full-sha>"
$ curl -s 'https://api.github.com/repos/<owner>/<repo>/pulls?state=all' | grep -c <full-sha>
1
```

**Disclosure - the consequence, and the limit of discoverability.**

```
$ curl -s https://api.github.com/search/commits?q=author:<name>+repo:<owner>/<repo>
"total_count": 0
$ curl -s https://api.github.com/search/commits?q=sha:<full-sha>+repo:<owner>/<repo>
"total_count": 0
$ curl -s https://api.github.com/search/commits?q=<full-sha>+repo:<owner>/<repo>
"total_count": 0
$ curl -s https://api.github.com/users/<login>
"name": "<display name>", "email": null
```

The commit search returns the object by neither author nor SHA, a truncated-SHA
fetch is refused and a plain clone does not contain it: the object is **not
discoverable** by a reader who does not already have the SHA. The SHA is not a
secret, though - it is a field of the ordinary PR #23 record - so "whoever asks"
is a larger set than "whoever was given the SHA by a third party"; the
qualification is that the reader must know to ask. The account that opened the
pull request is not identified by an address: its public profile carries the
display name and a null email, and the commit page renders the name but not the
address.

**The content, separately.** The content of the retained object is already
published safely:

```
$ git rev-parse <rev>^{tree} <role-mailbox-rev>^{tree}
<the same tree id, twice>
$ git merge-base --is-ancestor <role-mailbox-rev> origin/main; echo $?
0
```

So the published tree ships the same content under the role mailbox, and the
published history carries no personal identity. What is disclosed is the
**identity** of the retained object, not its content.

### 7.2 The measure and the question it answers

The false claim this report previously made - that the forge did not hold the
object at all - came from a measure that answers a different question. A clone of
the advertised refs **does not fetch an object no ref advertises**, so
`git cat-file -t <rev>` in that clone is rc 128 for a reason that says nothing
about the forge's own store. The correction is procedural and is now the method
in section 2: state the measure, state the question it answers, and measure
existence separately by asking the forge for the object.

The words follow the measurements. "Published" is reserved for objects reachable
from a published ref; the object here is **retained**; the identity is
**disclosed** to anyone who asks for that SHA. Three wordings are withdrawn in
this revision, and so are the two risk characterisations the previous revision
used. They are listed here by description, not by quotation, so that a reader
grepping this report for a withdrawn phrase does not find it:

| Withdrawn wording | Why it is withdrawn |
|---|---|
| a claim that the object was not on the forge at all | false - the forge serves it (section 7.1) |
| a claim that the object was never, or not yet, on the forge | a reachability claim used as an existence claim, and it collides with the role-mailbox commit that **is** in `origin/main` and carries the same content |
| wording that read as a broadcast, a public discovery or a leak of the identity | discoverability was measured absent (commit search 0, truncated-SHA fetch refused, plain clone lacks the object) - the identity is disclosed on request, not broadcast |
| a risk row that said the exposure lay ahead of us rather than behind us | the disclosure happened at the object level, when the forge served the object with the identity attached |
| a risk row that reduced this to a containment task rather than a disclosure | the same reason - the disclosure happened; the rewrite does not undo it |

The disclosure happened; the rewrite is still needed; the rewrite does not undo
it.

### 7.2.1 The ruling's own record (F-9)

The decision record of the ruling that governs this report was measured the same
way, and it is where the disclosure is **reproduced in the tree** - which is why
it is a finding of its own and not a footnote to F-1.

Measured on the branch that carries the ruling entry, in a scratch extraction
(`git archive <rev> | tar -x -C <scratch>`, re-initialised as a git repo so
`git ls-files` works), with the shipped scanner and the shipped allowlist:

```
$ python3 scripts/privacy_scan.py --tree --allow .github/privacy-allow.txt
docs/Team/Decisions.md:<line>: [high/private-domain] <redacted-private-domain>
docs/Team/Decisions.md:<line>: [high/personal-email] <redacted-personal-email>
docs/Team/Decisions.md:<line>: [high/high-entropy-secret] <redacted-high-entropy-secret>
docs/Team/Decisions.md:<line>: [high/high-entropy-secret] <redacted-high-entropy-secret>
privacy_scan: FAIL - <n> finding(s) in tree
```

The same scan on `main` is `PASS - 0 finding(s) in tree`. The two
high-entropy hits are the commit SHAs the evidence line quotes - the shape that
rule over-fires on - and the two identity hits are the operator's address and
private domain, quoted literally in the `evidence:` line of the entry that
documents the disclosure. The commit message of the same commit quotes the
address as well.

The two facts that keep this proportionate: the occurrence is **not on `main`
and not on any published ref**, so it is not published and not disclosed to
anyone who does not already have that branch; and the fix is the one the team
already uses elsewhere - **name the rule, not the value**. The archive mask
replaced the quoted address with `[redacted-personal-email]` in exactly this way
(`docs/Team/Archive.md`), and the ruling entry needs the same treatment in both
the record and the commit message. The owner is the author of the entry; this
lane does not edit that file.

### 7.3 Without the allowlist

```
$ python3 scripts/privacy_scan.py --tree --history
privacy_scan: FAIL - <n> finding(s) in tree, history
```

The residue is the allowlist file's own text, the scanner's own tests, two home
paths quoted as evidence in `docs/Team/Decisions.md`, and the two causes above.

The gap between the runs is the allowlist, and the allowlist is
readable: `.github/privacy-allow.txt` carries one anchored, fully escaped literal
per exempted value family, each with the reason it cannot be fixed at source. No
entry exempts a credential - a token, key or password on the same line is still
reported, and `tests/unit/test_privacy_scan.py` proves both the narrowness of each
entry and that a neighbouring value is still caught.

### 7.4 Code-scanning: `py/clear-text-logging-sensitive-data` (alerts #1, #2, #3)

**Current state, re-measured at this revision.** All three alerts of this rule
are closed on the forge and the closure is a **fix**, not a dismissal:

```
$ gh api "repos/<owner>/<repo>/code-scanning/alerts?state=closed"
  #1  py/clear-text-logging-sensitive-data  state=fixed  dismissed_reason=null
  #2  py/clear-text-logging-sensitive-data  state=fixed  dismissed_reason=null
  #3  py/clear-text-logging-sensitive-data  state=fixed  dismissed_reason=null
```

A previous revision of this section triaged alerts #2 and #3 as **false
positives** and recorded the reasoning in D-20261020-SEC-1 (in
`docs/Team/Decisions.md`). That record is kept as written - it is the decision as
it was taken - but the **mechanism it described no longer exists**, and the alert
was closed by changing the code rather than by dismissing it. The reason is the
same finding the decision reached, reached the other way round: a sink that cannot
reach the value is better than a sink that is defended by a comment.

**What the scanner does now.** The raw matched value is not in the report at
all - not masked, not popped, not held in a key:

```python
class Finding(dict):
    """One report row, with the raw matched value held outside the mapping.

    Every reporting sink serialises *items*: ``json.dumps(report)`` walks the
    dict, the text report reads ``evidence``, and both end up in a CI log. A
    value kept as an attribute therefore cannot be published by any of them, so
    "the log never carries a secret" is a property of the shape rather than a
    promise held by one ``pop`` before one ``print``.
    """

    __slots__ = ("raw",)
```

The report row carries `"evidence": f"<redacted-{rule_id}>"` - the **rule name**,
not a partly masked preview of the value - and the raw value lives in
`Finding.raw`, an attribute outside the mapping, which every reporting sink
cannot reach. The only code that reads `.raw` is `--reveal` (which adds
`_fingerprint`, an unsalted truncated SHA-256) and `--reveal-to PATH` (which
writes to a `0600` file the operator names). There is **no** flag that prints the
value.

**Measured proof, re-run at this revision.** In a scratch extraction of `HEAD`
(`git archive HEAD | tar -x -C <scratch>`, re-initialised as a git repo so
`git ls-files` works) a synthetic credential was planted at runtime from parts
and committed:

```
$ python scripts/privacy_scan.py 2>&1 | grep leak_probe
leak_probe.txt:1: [critical/api-token] <redacted-api-token>
leak_probe.txt:1: [critical/env-secret] <redacted-env-secret>

$ python scripts/privacy_scan.py --reveal 2>&1 | grep leak_probe
leak_probe.txt:1: [critical/api-token] <redacted-api-token> (sha256:7873664f1ddd)
leak_probe.txt:1: [critical/env-secret] <redacted-env-secret> (sha256:7873664f1ddd)

$ python scripts/privacy_scan.py 2>&1            | grep -c '<planted value>'   -> 0
$ python scripts/privacy_scan.py --reveal 2>&1   | grep -c '<planted value>'   -> 0
$ python scripts/privacy_scan.py --json --reveal | grep -c '<planted value>'   -> 0

$ python scripts/privacy_scan.py --reveal-to .pi_reveal.txt
  stdout raw hits -> 0, stderr raw hits -> 0, file mode -> 600, file raw hits -> 2
  stderr: privacy_scan: WARNING - <n> unmasked value(s) written to .pi_reveal.txt
          (mode 0600). Delete it after remediation; never commit, copy into a
          ticket, or paste it into a chat.
```

Not one character of the planted value reaches stdout, stderr or the `--json`
output in any of the three modes, including `--reveal`; the only place it lands
is the `0600` file the operator named, with a warning on stderr. The report
names the rule instead of previewing the value, so the log cannot hand over a
prefix and a suffix of a credential either.

**Why the code-scanning rule stays armed.** The alert is closed by the fix, not
by an exclusion, so a genuine re-inroduction on this path alerts again. The
sink is also pinned by the team's own test, independently of the scanner's
opinion: `tests/unit/test_privacy_scan.py::test_reveal_never_prints_the_unmasked_secret`.

## 8. Sources

- [git-filter-repo](https://github.com/newren/git-filter-repo) - accessed 2026-10-17
- [GitHub: removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) - accessed 2026-10-17
- [GitHub: security hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions) - accessed 2026-10-17
- [GitHub REST API - commits](https://docs.github.com/en/rest/commits/commits) - accessed 2026-10-21
- Teamwork risk register R-2/R-3 (internal, `docs/Team/Risks.md`) - accessed 2026-10-17
