# RISKS - risk register

Owner: COO. Reviewed at every integration point. No entry without an owner and a
mitigation - otherwise escalate to the CEO instead of recording it.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Costs](Costs.md) · [Archive](Archive.md) · [AuditReport](AuditReport.md)

| id | risk | category | likelihood | impact | mitigation / trigger | owner | status |
|---|---|---|---|---|---|---|---|
| R-1 | The project does not reach a high star count: stars are earned by users, not by repository decoration | delivery | high | med | Optimise only conversion inputs (demo, README, topics, release, license); report the real number, never a promise; keep publishing to communities | ProductManager | open |
| R-2 | Personal data leaks into the published tree or git history | security | med | high | `scripts/privacy_scan.py --tree --history` in CI and before every push; neutral git identity; history rewritten before the first public release | SecurityAuditor | mitigating |
| R-3 | A secret from the environment is written into a tracked file during development | security | med | high | Scan for key-shaped strings; never read `.env`; CI privacy job blocks the merge | SecurityAuditor | mitigating |
| R-4 | Windows-specific breakage that Linux CI cannot see | tech | med | med | `ubuntu/macos/windows` matrix; `portable.pid_alive`; no POSIX-only imports (source-scan test) | Architect | mitigating |
| R-5 | The 7k-line engine regresses while being moved into a package | delivery | med | high | Behaviour-preserving move, `selftest`, and an integration test that exercises the CLI end to end | Developer | mitigating |
| R-6 | The wheel ships without the skill bundle (roles/templates) | delivery | low | high | `scripts/verify_release.py` asserts `teamwork/data/SKILL.md` and `teamwork/data/templates/AGENTS.md` inside the wheel | ReleaseEngineer | mitigating |
| R-7 | Concurrent agents overwrite each other in one working tree | process | med | med | One writer per file, frozen ownership table, disjoint lanes, CEO integrates | ProjectManager | mitigating |
| R-8 | The `teamwork` PyPI name is taken, so `pip install teamwork` gets the wrong project | delivery | high | low | Distribution name `teamwork-agents`; README states it explicitly | ReleaseEngineer | resolved |
| R-9 | Git LFS is required for binary assets and breaks `git clone` for some users | tech | low | med | Ship only SVG (text) assets; no raster images in the repository | Designer | resolved |
| R-10 | GitHub Actions is unavailable or the account cannot push workflow changes | delivery | low | high | Verified: CI run `39173857076` executed 16/16 jobs green, and Actions runs are visible to `gh`; pushes use SSH with the `repo` scope (the token has no `workflow` scope, which SSH pushes do not need); local fallback stays `make verify` | ReleaseEngineer | resolved |
| R-11 | AGPL-3.0 deters some corporate adopters | delivery | med | low | Stated up front in the README; the license is deliberate for a governance tool | CEO | accepted |
| R-12 | GitHub Actions are referenced by mutable tags, so an upstream tag move could run different code in a `contents: write` job | security | low | high | Every `uses:` in `ci.yml`, `docs.yml` and `release.yml` is pinned to a full commit SHA with the moving tag only in a comment (`grep -h 'uses:' .github/workflows/*.yml` -> 28 refs, all SHA-pinned, 0 tag refs); workflow-level permissions default to `contents: read` and each job widens only what it needs | SecurityAuditor | resolved |
| R-13 | The privacy scanner has documented blind spots (personal names, GPG signature key IDs, binary blobs, non-email PII, unscanned `.git/config`) | security | med | med | Blind spots are listed in [AuditReport](AuditReport.md); the name/key-ID cases are eliminated by the history rewrite, the rest are accepted for v1.0.0 with an issue to extend the rule set | SecurityAuditor | accepted |
| R-14 | The repository handle appears in every project URL, and it is derived from the owner's initials | security | low | low | The owner publishes under this account by choice; it is not a secret and no other personal datum accompanies it | CEO | accepted |
| R-15 | `docs/Team/Archive.md`, `Ledger.jsonl` and the team workspace carry provenance that could leak if archived manually | security | low | med | `.pi/` and `site/` are gitignored; `scripts/privacy_scan.py --tree` flags tracked local state, agent-host config and credential files, and the release archive contains only the sdist/wheel | ReleaseEngineer | mitigating |
| R-16 | The author identity of a retained forge commit is **disclosed at the object level** - the forge serves the object anonymously by SHA with the name and the address in the payload, and the disclosure cannot be un-disclosed; the commit is **not reachable from any published ref**, and the published history is clean | security | med | high | The published side is clean and the object is **retained** by the forge rather than published by a ref (see "The privacy red is local" below), but the forge serves it to anyone who asks for that SHA, so the identity is already disclosed and no history rewrite can undo that. The rewrite is still required - it stops the published history from carrying the identity forward - and it needs the user's authorisation through the CEO | CEO | open |

| R-17 | Asset changes review as binary: `.gitattributes` marks `docs/assets/*` `-diff`, so a reviewer sees "binary files differ" instead of the change | process | med | med | Read the blob with `git diff --text` or re-measure the file until the attribute is narrowed | Architect / CEO | open |
| R-18 | A README `<img>` carries no intrinsic `height`, so the hero shifts layout while it loads | tech | low | low | The asset declares its own size; the `<img>` attributes are a follow-up on the same file | Designer | open |
| R-19 | The OG card's pitch punctuation differs from the README and no generator is committed, so a rebuild cannot be replayed | process | low | low | Rebuild only with a committed generator; record the deviation until then | Designer | accepted |
| R-20 | A lane that writes into the base checkout has its uncommitted edit swept into another lane's records commit (`D-20261030-Developer-3` landed this way) | process | med | med | Lanes write only in their own worktree; the records pass commits what it finds, so an uncommitted file in the base tree is never safe | CEO | open |
| R-21 | `clean --all` was team-wide, so one lane's cleanup emptied every peer's `Scratch/` irreversibly - the CEO's own draft was one of the casualties | process | high | med | Fixed in `P-0010` (`6111b1a`): agent-scoped by default, `--team-wide` explicit and announced before the first unlink, pinned by six effect assertions | Developer | resolved |
| R-22 | A relative `--artifact` path resolves against the base checkout, so a lane can bind the main tree's copy into its record | process | med | med | Write artifacts under `Agents/<lane>/Artifacts` and name them absolutely; a worktree-validated path is a follow-up | CEO / Release Engineer | open |
| R-23 | No gate reads the licence/copyright fields across surfaces, so `CITATION.cff` could claim `AGPL-3.0-only` while `NOTICE`, `pyproject.toml` and the published npm metadata say "or-later" | delivery | med | high | Aligned by the technical-writer lane at the verifier's finding; add a licence-consistency rule to `check_release_consistency.py` (one SPDX id across the six surfaces) | Release Engineer | open |

## The privacy red is local - the published history is clean

Measured by the Security Auditor and re-read here. This section exists so the
next agent reads the answer instead of re-measuring it. **No finding count and no
revision is pinned**: the commit that documents a count raises it
([D-20261019-CEO-15](Decisions.md)); read the numbers from the commands.

**State.**

| Surface | Result | How to read it |
|---|---|---|
| Published history (every forge ref) | **clean** - every author and committer is a role mailbox or an allowlisted service mailbox (`noreply@github.com`, a dependabot service mailbox) | `git log --all --remotes --format='%ae\|%ce' \| sort -u` in a clone of the forge |
| Published objects | **no leak** - a blob sweep over every object reachable from every published ref finds no operator address, no private domain and no operator name | `git rev-list --objects --all` + `git cat-file --batch` over each blob |
| Published tree + history, shipped gate | **PASS** | `python3 scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` |
| Published `main` in CI | **green**, including the `privacy scan (tree + history)` job | `gh run list --repo Nidvue/Teamwork --branch main` |
| Local tree, shipped gate | **PASS** - the archive mask now covers every rule the gate reports, so an archive entry can no longer re-publish a quoted address | `python3 scripts/privacy_scan.py --tree --allow .github/privacy-allow.txt` |
| Local **history** | **red** - this is the only red left | `python3 scripts/privacy_scan.py --tree --history --allow .github/privacy-allow.txt` -> read the `privacy_scan:` line |

**Causes of the local-history red** (the tree is clean; only history is red):

1. **The offending commit is local-only, and the forge still serves it.** It is
   the forge's squash merge of a published pull request, authored with the
   operator's personal identity because the forge stamps the signed-in account.
   It is **not reachable from any published ref** - it is an ancestor of no
   published ref and no tag, `git ls-remote origin` advertises no ref that
   carries it, and a plain anonymous clone does not contain it. **The forge
   nevertheless serves the object anonymously**: its API returns it with HTTP
   200 and the author name **and email** in the payload, its commit page returns
   HTTP 200 and renders the author name, and the PR #23 record names it as
   `merge_commit_sha` (also served by the ordinary enumerable `GET /pulls` list).
   So the identity is **disclosed to anyone who asks for that SHA** and cannot be
   un-disclosed - discoverability was measured absent (the forge's commit search
   returns it by neither author nor SHA, a truncated-SHA fetch is refused), so
   this is not a publicly discoverable disclosure but it is a real one. Its
   **tree is identical** to the published commit that carries the same content
   under the role mailbox, so the content is already public in a safe form and
   the disclosure is of the **identity**. Verify with
   `git rev-parse <sha>^{tree} <published-sha>^{tree}`.
   A note on the measure: `git cat-file -e <sha>` in a clone of the advertised
   refs answers **reachability**, not existence on the forge - such a clone never
   fetches an object no ref advertises. An earlier revision of this register
   read that as the object not being on the forge at all, which is false; ask
   the forge for the object by SHA to measure existence.
2. **Archived reviewer findings in old blob revisions.** The archive copies a
   reviewer's findings verbatim, so older revisions of `docs/Team/Archive.md`
   still quote the address inside a quoted-evidence field. The live tree is
   clean; the history is not. The archive mask was widened to cover every rule
   the gate reports, so a *new* entry cannot re-publish it; the *old* blob
   revisions are what remain, and only a history rewrite removes them.

**The remediation and who must authorise it.** The fix is a rewrite of the
local commits: rebase the local branches onto the published tip,
rewrite the leaking archive blob revisions so the address is redacted, and
re-point the commit SHAs that `docs/Team/Archive.md`, `docs/Team/Decisions.md`
and the ledger cite. No published ref, tag or release changes, and no push is
involved. **It still needs the user's authorisation**, because `AGENTS.md`'s
red-line list names "history rewrite" without the *published* qualifier, and
the conservative reading applies. The Security Auditor measured the whole
remediation end to end in a throwaway clone and reported the gate going from
red to clean; that figure is the Auditor's measurement on a throwaway copy, not
a property of this tree - re-measure it on the real branch after the rewrite.
**What the rewrite does not do:** it does not undo the disclosure. The identity
is already disclosed at the object level; the rewrite protects the published
history from carrying the identity forward.

**One item belongs to the operator, not to the team.** The forge creates a
`refs/pull/<n>/merge` preview ref for every open pull request, authored with
the account that opened it, and that ref is publicly readable. While a pull
request opened from the operator's personal account is open, its merge preview
carries the operator's personal identity. The shipped gate deliberately does
not report it - a forge merge preview is a server-side artifact, not a commit
the team made, and failing the gate on it would make every open pull request
red. The remedy is the account the pull requests are opened from, not the
gate. Read the live state with
`gh pr list --repo Nidvue/Teamwork --state open --json number,author`.

**Do not** exempt the operator's address in `.github/privacy-allow.txt`: the
allowlist is a tracked, published file, so an entry for a real personal address
would publish the value the gate protects. The exemption rule and its
falsifier are in [D-20261019-CEO-15](Decisions.md).

The blind spots of the scanner itself, and the residual risks of the tree, are
in [AuditReport](AuditReport.md); the criterion this state answers is AC-5 in
[Project](Project.md).

## Process health

- Cycle time: lanes started in parallel at the interface freeze; no lane waits on
  another except the review gate (M3).
- Blocked hotspots: GitHub publishing needs the CEO's credentials only.
- Duplicate work seen: none - the ownership table assigns one writer per file.
- Tooling gaps: no local Windows runner, so the Windows job is proved by CI.

## Sources

- [GitHub Blog - promoting an open source project](https://github.blog/open-source/maintainers/5-tips-for-promoting-your-open-source-project/) - accessed 2026-10-17
- [PyPI - project name availability for `teamwork`](https://pypi.org/project/teamwork/) - accessed 2026-10-17
