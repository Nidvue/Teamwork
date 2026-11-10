# PLAN - milestones and task graph

Owner: Project Manager. One row per task; `deps` must be `done` before it runs.
Priority: P0 code, P1 tests, P2 docs.

Related: [Project](Project.md) · [Board](Board.md) · [Architecture](Architecture.md) · [Decisions](Decisions.md) · [Research](Research.md) · [Design](Design.md) · [Risks](Risks.md) · [Costs](Costs.md) · [Release](Release.md) · [Archive](Archive.md)

## M1 - <name>

Exit: <verifiable statement>

| id | task | role | prio | deps | artifact | status |
|---|---|---|---|---|---|---|
| T-0001 | Freeze interfaces | architect | P0 | - | Architecture.md | todo |
| T-0002 | Implement + unit tests | developer | P0 | architect:T-0001 | src/... | todo |
| T-0003 | Integration/E2E tests | tester | P1 | architect:T-0001 | tests/... | todo |
| T-0004 | UX spec | designer | P1 | architect:T-0001 | Design.md | todo |
| T-0005 | Docs | product-manager | P2 | developer:T-0002 | docs/... | todo |

## Parallel rules

- Freeze interfaces first, then run dev / test / design lanes concurrently.
- Tests are written from the frozen contract, in parallel with implementation.
- Docs never block code or tests.
