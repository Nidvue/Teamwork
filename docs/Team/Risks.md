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

## Process health

- Cycle time: lanes started in parallel at the interface freeze; no lane waits on
  another except the review gate (M3).
- Blocked hotspots: GitHub publishing needs the CEO's credentials only.
- Duplicate work seen: none - the ownership table assigns one writer per file.
- Tooling gaps: no local Windows runner, so the Windows job is proved by CI.

## Sources

- [GitHub Blog - promoting an open source project](https://github.blog/open-source/maintainers/5-tips-for-promoting-your-open-source-project/) - accessed 2026-10-17
- [PyPI - project name availability for `teamwork`](https://pypi.org/project/teamwork/) - accessed 2026-10-17
