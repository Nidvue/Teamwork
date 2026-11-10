# RISKS - risk register

Owner: COO. Reviewed at every integration point. No entry without an owner and a
mitigation - otherwise escalate to the CEO instead of recording it.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Costs](Costs.md) · [Archive](Archive.md)

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
| R-10 | GitHub Actions is unavailable or the account lacks the `workflow` scope | delivery | low | high | Verify `gh auth status` scopes before pushing; fall back to a local, reproducible pipeline via `make verify` | ReleaseEngineer | open |
| R-11 | AGPL-3.0 deters some corporate adopters | delivery | med | low | Stated up front in the README; the license is deliberate for a governance tool | CEO | accepted |
| R-12 | GitHub Actions are referenced by mutable tags (`@v4`), so an upstream tag move could run different code in a `contents: write` job | security | low | high | Workflow-level permissions reduced to `contents: read`; each job widens only what it needs. Pinning every action to a commit SHA is the follow-up for v1.1 | SecurityAuditor | mitigating |
| R-13 | The privacy scanner has documented blind spots (personal names, GPG signature key IDs, binary blobs, non-email PII, unscanned `.git/config`) | security | med | med | Blind spots are listed in [AuditReport](AuditReport.md); the name/key-ID cases are eliminated by the history rewrite, the rest are accepted for v1.0.0 with an issue to extend the rule set | SecurityAuditor | accepted |
| R-14 | The repository handle appears in every project URL, and it is derived from the owner's initials | security | low | low | The owner publishes under this account by choice; it is not a secret and no other personal datum accompanies it | CEO | accepted |
| R-15 | `docs/Team/Archive.md`, `Ledger.jsonl` and the team workspace carry provenance that could leak if archived manually | security | low | med | `.pi/` and `site/` are gitignored; `scripts/privacy_scan.py --tree` flags tracked local state, agent-host config and credential files, and the release archive contains only the sdist/wheel | ReleaseEngineer | mitigating |

## Process health

- Cycle time: lanes started in parallel at the interface freeze; no lane waits on
  another except the review gate (M3).
- Blocked hotspots: GitHub publishing needs the CEO's credentials only.
- Duplicate work seen: none - the ownership table assigns one writer per file.
- Tooling gaps: no local Windows runner, so the Windows job is proved by CI.

## Sources

- [GitHub Blog - promoting an open source project](https://github.blog/open-source/maintainers/5-tips-for-promoting-your-open-source-project/) - accessed 2026-10-17
- [PyPI - project name availability for `teamwork`](https://pypi.org/project/teamwork/) - accessed 2026-10-17
