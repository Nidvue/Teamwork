# COSTS - budget, unit economics, ROI

Owner: CFO. Every number states its assumption and check date. Escalate early if a
cap is projected to be hit.

Related: [Project](Project.md) · [Plan](Plan.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Archive](Archive.md)

## Cost model

| driver | unit | rate | volume | monthly | note |
|---|---|---|---|---|---|
| Model tokens (team run) | per agent-turn | metered by the provider | one delivery | not budgeted by the project | the team is run by the owner's coding agent, not by the shipped product |
| CI minutes (public repo) | per minute | free for public repositories | ~9 matrix jobs x ~2 min per push | 0 | within the free tier for public repos |
| GitHub Releases storage | per GB | free | < 5 MB per release | 0 | wheel + sdist + checksums + SBOM |
| PyPI hosting | per project | free | 0 (publishing prepared, not executed) | 0 | needs an owner token to enable |
| Domain / hosting for docs | - | GitHub Pages, free | - | 0 | `docs.yml` deploys to Pages |

## Budget

- Approved: no monetary budget. The deliverable is a public repository.
- Hard caps and behaviour at cap: if a GitHub Actions cap were hit, CI would fall
  back to `make verify` locally (`scripts/verify_release.py` + `pytest`), which is
  the same pipeline.
- Current burn: zero cash. Compute is metered by the owner's coding agent.

## Unit economics

- Cost per user: **0**. The package has zero runtime dependencies and no service
  to run; the user pays only for the model tokens their own agents consume.
- Cost per task/run: determined entirely by the user's provider, not by Teamwork.
- Break-even assumption: none - there is no revenue and no cost to recover. The
  return is adoption: stars, forks and issues that improve the project.

## Build vs buy

| need | build | buy | recommendation | reason |
|---|---|---|---|---|
| Workspace/state engine | `src/teamwork/engine.py` (stdlib) | a database/service | build | zero deps, markdown-and-git is auditable by a human |
| CI | GitHub Actions | paid runners | buy (free tier) | public-repo minutes are free |
| Docs hosting | mkdocs-material + GitHub Pages | Read the Docs / Netlify | buy (free) | one less account, one less secret |
| Package registry | GitHub Releases | PyPI (also prepared) | both, PyPI optional | releases work without a token |

## Sources

- [GitHub Actions billing for public repositories](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions) - accessed 2026-10-17
- [GitHub Pages](https://docs.github.com/en/pages) - accessed 2026-10-17
