# Layered testing - every agent tests its own work

Reference for the /teamwork skill. Loaded on demand.

Related: [Roles](Roles.md) | [Engineering](Engineering.md) | [Evidence](Evidence.md) | [State](State.md) | [Docs](Docs.md) | [Concurrency](Concurrency.md) | [Audit](Audit.md)

## One layer per role

Every agent designs, develops **and executes** its own independent tests, and
evidences the run. No layer is delegated, and nobody substitutes for another
role's layer.

| Layer | Owner | What it must verify |
|---|---|---|
| `goal` | CEO | black-box: the delivered result actually meets the user's objective |
| `requirements` | Product Manager | every requirement maps to a passing check; traceability is complete |
| `plan` | Project Manager | plan integrity: dependency graph, duplicate work, milestone exit criteria |
| `tech` | CTO | toolchain and dependency upgrades, feasibility spikes, version drills |
| `release` | Release Engineer | reproducible build, CI gates, packaging, upgrade and rollback |
| `data` | Data Engineer | schema and migrations, backfill, backup and restore drills |
| `process` | COO | the documented workflow and tooling actually run end to end |
| `cost` | CFO | metering, cap enforcement, unit-economics assertions |
| `system` | Architect | architecture conformance: boundaries, dependency direction, contracts, ADRs |
| `ui` | Designer | UI use cases: flows, component states, accessibility |
| `docs` | Technical Writer | every documented command and claim executed as written |
| `unit` | Developer | unit tests for the code the Developer wrote |
| `integration` | Tester | integration / system / end-to-end behaviour |
| `acceptance` | Reviewer | acceptance tests over **every** role's output |
| `security` | Security Auditor | auth, input handling, secrets, red-line behaviour |

Ownership is enforced: `tests add --layer integration --owner developer-1` is
refused, and `tests run` only accepts instances of the owning role.

Several **Reviewers** may run at once (`reviewer-1`, `reviewer-2`, ...). One may
pass the verdict and that same lane merges it - an author never reviews or merges
its own work, which is where independence lives.

## Comprehensive and systematic

Each layer is designed the same way, so coverage is comparable across roles:

1. **Enumerate** the claims the role is accountable for (its own deliverables and
   decisions) and the ways they can fail: normal path, boundaries, error paths,
   concurrency, degraded inputs, and the regression case for each fixed defect.
2. **Design before implementing**: write down the cases and the expected result,
   then implement them. Tests are written from the frozen interface
   (`Architecture.md`) and the role's own specification - not from the finished
   code, so lanes stay independent.
3. **Execute and evidence**: actually run them and record command + revision +
   observed result. Reading a diff is not a test.
4. **Keep them deterministic**: no network, no sleeps, no ordering assumptions;
   quarantine flaky tests explicitly with an owner instead of ignoring them.
5. **Keep them alive**: re-run after every change that touches the layer's subject;
   a stale pass is not a pass.

Coverage is measured against the role's own claims, not line coverage. A layer
that cannot fail does not count as a test.

## Records

One record per **(layer, area)** pair - that is the anti-duplication rule: the
same thing is not tested twice by accident.

```sh
# each role declares its own layer for an area it is accountable for
teamwork.py tests add --layer unit --area auth --command "go test ./internal/auth"
teamwork.py tests add --layer system --area auth --command "check-boundaries ./..."
# the owning role runs it and records evidence
teamwork.py tests run TS-0002 --by tester-1 --result pass \
    --evidence "go test ./test/integration -run Auth @a1b2c3d -> ok 4 tests" \
    --baseline "empty auth table" --artifact Reports/auth-run.log --replay "go test ./test/integration -run Auth"

# a defect fix proves the failure first; the proof is stored on the defect task
# (task added with --bug), not on a layer record
teamwork.py tests repro T-0007 --by tester-1 \
    --pre-rev a1b2c3d --pre-evidence "go test ./test/integration -run Auth @a1b2c3d -> FAIL, 2 tests" \
    --post-rev d4e5f6a --post-evidence "go test ./test/integration -run Auth @d4e5f6a -> ok 4 tests"

teamwork.py tests list [--layer unit]
teamwork.py tests plan        # matrix, role coverage, gaps

Exit codes: `0` every required layer passes, `1` gaps remain, `3` no area is
declared yet (nothing to check).
```

`tests add` refuses a duplicate `(layer, area)` and warns when the same command
would run in two layers.

## Required coverage

Default: **every staffed role's layer** must cover every area in use. Narrow it
deliberately, per area, and record why:

```sh
teamwork.py tests require --area auth --layers unit,integration,system,ui,acceptance,security
```

Default required coverage per area is the proportionate core set (`unit`,
`integration`, `acceptance`) restricted to staffed roles; widen or narrow it per
area with `tests require --area <a> --layers ... --by <architect|ceo> --reason <why>`,
which is recorded and audited. Every staffed role must still design and run at
least one test of its own layer.

`loop` will not report STOP while a required layer is missing, pending or failing,
nor (with four or more staffed layers) while a staffed role has designed no tests
at all. `audit` lists the same gaps, failing layers, duplicate commands and roles
with no tests.

## Local and CI are one certification

The Tester owns both signals and must show they agree:

1. **Local** - run the layers on the working revision; this is the fast signal.
2. **CI** - confirm the Release Engineer's pushed SHA produced the same result,
   job by job across the OS/Python matrix; this is the authoritative signal.
   A green local run with a red CI run is a failure, and so is the reverse.
3. **Divergence is a defect.** Route it to the owner and re-verify after the fix:
   code -> Developer; test -> Tester; contract/interface -> Architect; workflow,
   packaging, runner or flake -> Release Engineer; scope -> CEO. File the exact
   command, expected vs actual, log excerpt, SHA, run id and a one-line repro.
4. **Never report a suite as passing while the matching CI run is red** (or the
   reverse), and never let a red run go unowned.

A `tests run` evidence string therefore names both:

```
<local command> @<rev> -> <result>; CI <run-id> @<rev> -> <conclusion>
```

## How it fits the flow

```text
interfaces frozen
      |
      +-- every role designs and runs its own layer, in parallel:
          goal · requirements · plan · tech · release · data · process · cost
          system · ui · docs · unit · integration · acceptance · security
      |
      v
  PR -> Reviewer acceptance tests + independent review -> merge (same lane)
```

Test layers are lanes like any other: they claim provider slots, run in parallel
with implementation, and are never deferred to the end of a milestone.
