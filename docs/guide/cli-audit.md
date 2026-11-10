# CLI: audit and control - Nidvue Teamwork

Owner: Technical Writer.

Related: [Home](../index.md) · [CLI reference](cli.md)

The audit trail and the controls that read it: ledger, trace, coordination,
throughput, loop, refresh, model routing and the auxiliary scripts.

This page is one part of the [CLI reference](cli.md) set; the overview lists every group.

## Audit and control

### `ledger`

```text
teamwork ledger {show,verify,repair,export} ...
```

The append-only, hash-chained audit trail.

#### `ledger show`

```text
teamwork ledger show [--tail TAIL] [--action ACTION] [--actor ACTOR] [--target TARGET]
```

Inspect the trail.

#### `ledger verify`

```text
teamwork ledger verify [--reconcile]
```

Recompute the hash chain. `--reconcile` repairs a head cache left by a crash.

#### `ledger repair`

```text
teamwork ledger repair --by BY --reason REASON [--force REASON]
```

Drop a torn tail and record the repair.

#### `ledger export`

```text
teamwork ledger export [--dry-run] [--by BY]
```

Write an externally verifiable audit manifest (`docs/Team/AuditManifest.json`).

### `trace`

```text
teamwork trace HANDLE [--full]
```

Follow one task, criterion, test or PR through every record. Free-text evidence
(evidence, findings, review notes, dispute rounds, rulings) is clipped at 600
characters with an `... (+N chars: --full)` marker; `--full` prints it whole.

### `coordination`

```text
teamwork coordination [--strict] [--json] [--commit]
```

Coordination health from the records the team already writes: duplicate
branches/tasks/shared references, verification lanes on one model, review
evidence copied from the author, reviewer monoculture, abandoned PRs, merge
fraction, and slot starvation. Stale open PRs remain `audit`'s check. The default
report is diagnostic; `--strict` exits `1` while a high-severity finding is open
and is the milestone gate; `--commit` appends the result to the ledger; `--json`
is machine-readable. Mechanisms and the failure each check addresses:
`references/Coordination.md`.

### `throughput`

```text
teamwork throughput [--json]
```

Read-only measured report from the ledger and the tree: top actions; review
claim -> verdict count, p50/p90/max; pass/fail verdicts; targets with more than
one verdict; queue depth per role; instance count; and surface bytes (AGENTS,
SKILL, startup range, Archive, Decisions, Plan, docs/Team, largest TaskQueue)
with a `//4` token estimate. `--json` prints one object with the same fields. It
writes no file and no ledger record; re-run it at the revision you quote.

### `links`

```text
teamwork links [--no-reciprocity]
```

Check markdown cross-links, external URLs and back-links. `--no-reciprocity`
skips the bidirectional back-link requirement. Exit code `1` when issues exist.

### `audit`

```text
teamwork audit [--stale-days STALE_DAYS]
```

Find fabricated completions, stale work, duplicates, LFS problems and link
health.

### `code-scanning`

```text
teamwork code-scanning [--commit] [--limit N] [--full]
```

Read the forge's open code-scanning alerts and route each one to the role that
owns the file. The Release Engineer owns this gate: an `error`, `critical` or
`high` alert on the default branch is a known defect in the revision that ships.
Without `--commit` it only prints the plan
(`<number> [<severity>] <rule> <path>:<line> -> <role>`); with it, one `P0` task
per (owner, rule, file) is filed in that role's queue, carrying the alert
numbers and the `gh api` command as evidence. Re-running is safe: a title
already in the queue is not duplicated.

Exit codes:

| Code | Meaning |
|---|---|
| `0` | the alerts were read and none blocks the release |
| `1` | a blocking alert is open - with or without `--commit`, filing a fix does not close the gate |
| `2` | the alerts could not be read: no origin, no `gh`, no auth, no scanner, non-JSON output |

Routing follows file ownership (`SCAN_ROUTE` in `src/teamwork/config.py`):
`scripts/privacy_scan.py` and `docs/Team/AuditReport.md` to the Security
Auditor, `src/**`, `scripts/**` and `tests/**` to the Developer, `.github/**`
and `docs/Team/Release.md` to the Release Engineer, `docs/Team/Architecture.md`
to the Architect, `docs/**` to the Technical Writer, `roles/**`,
`references/**` and `templates/**` to the CEO, `README.md` and `assets/**` to the
Designer. An alert with no file, or a file no pattern covers, goes to the
Release Engineer.

Exit `2` is the honest degraded mode: a host that is not a forge, has no `gh`,
is unauthenticated, or has code scanning disabled prints
`- cannot verify: unreadable: ...` and never `no open alert`, because nothing was
verified. Fixing the code is the normal close; dismissing an alert is a Security
Auditor triage with a recorded reason, never a silent one.

### `loop`

```text
teamwork loop [--full]
```

Stop-condition check: may the team stop? Prints `STOP` or `CONTINUE` with
reasons. Detail past 220 characters is clipped by default; `--full` prints every
line whole.

### `refresh`

```text
teamwork refresh [--dest DIR] [--host HOST] [--source DIR] [--repo URL]
                 [--remote origin] [--branch main] [--mirror]
                 [--no-fetch] [--check] [--dry-run] [--quiet]
```

Keep the **installed** skill equal to the remote. The host loads the copy in its
skills directory, not the checkout, so updating one without the other leaves the
agent reading stale text - measured once on this machine as an old `SKILL.md`
plus 8 engine modules that were simply missing.

1. Resolve the source: `--source`, else `$TEAMWORK_SOURCE`, else the bundle in
   use when it is a git checkout, else the tool-managed mirror checkout
   `.teamwork-source` (`--mirror` forces that case). The mirror sits beside the
   skills directory, one level higher when that directory is literally named
   `skills`. The destination is resolved from the host's skills directory -
   `--dest` names one directly, `--host` selects a host's default - so
   `~/.pi/agent/skills/teamwork` mirrors through
   `~/.pi/agent/.teamwork-source`, and `--host agents` uses
   `~/.agents/.teamwork-source`.
2. In a checkout: fetch `--remote/--branch` and fast-forward. A dirty tree is
   never clobbered - the checkout is mirrored as it stands and the command says
   "fast-forward skipped".
3. Mirror into `--dest` (default the host's skills directory). Files the source
   no longer ships are deleted, files outside the bundle trees are never touched,
   and a stale `__pycache__` is removed.
4. Print the reminder to reload the host when anything was written.

`--check` reports drift and exits `1` without writing; `--dry-run` prints the
file plan; `--no-fetch` mirrors the local checkout only (`--repo` is required
just once, to create the mirror). `scripts/sync_skill.py` and `make sync-skill` /
`make sync-check` are the same mirror for a checkout that has no `teamwork` on
`PATH`.

### `version`

```text
teamwork version
```

Print the version and exit (same as `--version`).

### `selftest`

```text
teamwork selftest
```

Offline smoke test of the install; no network, no workspace required.

### `model` - per-agent configuration and automatic routing

```text
teamwork model set <role|instance> --provider P --model M
teamwork model get <role|instance>
teamwork model list
teamwork model auto [--apply] [--json]
```

The skill ships no model and calls no LLM API: every agent runs through the host's
own API, so the model is a property of the **agent**, not of the project.

- `set` writes a role default, or an instance override when the name carries an
  instance suffix (`developer-1`). The instance wins over the role.
- `get` prints the effective model and where it came from (`agent`, `role` or
  `unset`); `list` prints the whole roster.
- `auto` reads the **runtime environment** - the running agent host and the model
  it exposes - and routes the strongest available model to the decision lanes
  (Reviewer, Architect,
  Security Auditor, CEO, CTO) and the economy model to the mechanical lanes
  (developers, testers, writers, formatting, link checks). It is a dry run by
  default; `--apply` writes it and records `model.auto` in the ledger. It never
  invents a model id: a lane with nothing available is reported `unset` together
  with the variable to set (`TEAMWORK_MODEL_STRONG`, `TEAMWORK_MODEL_ECONOMY`).
  `TEAMWORK_AGENT_HOST` pins host detection when the markers are ambiguous.

Automatic routing policy: [references/Concurrency.md](https://github.com/Nidvue/Teamwork/blob/main/references/Concurrency.md).

### `imaging probe`

```text
teamwork imaging probe [--json]
```

The Designer's capability probe for **generated raster assets**. It is offline by
design: it reads environment variables and `PATH` only, never the network, so it
cannot leak a prompt or hang.

Resolution order: `TEAMWORK_IMAGE_MODEL` (explicit override) ->
`TEAMWORK_IMAGE_PROVIDER` -> the first ambient provider with a ranked image
model, in the order openai, google, black-forest-labs, stability, replicate,
local, ollama-cloud. "Best quality" is the first generally available model of the
detected provider, ranked in `teamwork.engine.IMAGE_MODEL_RANKING`.

When no model is detected it prints the fallback ladder instead of failing:
local model, then a hand-authored SVG. The full process - plan one prompt per
asset in `docs/Team/Design.md`, generate at least four candidates off one seed
base, review every candidate visually, improve the winner until it passes,
integrate, record evidence - plus the privacy and licence red lines, is the
Designer's own policy in
[`roles/designer.md`](https://github.com/Nidvue/Teamwork/blob/main/roles/designer.md).

## Auxiliary scripts

### `scripts/privacy_scan.py`

```text
python3 scripts/privacy_scan.py [--tree] [--staged] [--history] [--all]
                                [--allow FILE] [--root DIR] [--json]
                                [--reveal] [--reveal-to PATH] [--quiet]
```

The privacy gate. It fails (exit `1`) on personal data, credentials, private
domains, absolute home paths and agent-host configuration in the tracked tree,
the index and the full git history. `--tree`, `--staged` and `--history` combine;
`--all` sets all three; the default is `--tree`. Exit `2` is a usage or git
error. CI runs `--tree --history --allow .github/privacy-allow.txt`.

**No character of a matched value reaches stdout or stderr.** There is
deliberately no flag that sends a secret to a log: a log line survives the session
(CI logs are retained and world-readable, terminals are recorded, `tee` output
outlives the shell), and a partly masked preview such as `ev***et` already hands
the first and last characters of a credential to every reader of that log.

Plain output therefore names the rule, not the value -
`src/mod.py:12: [critical/api-token] <redacted-api-token>` - which says what fired
and where. The value itself is held outside the report record, so no reporting
sink (the text line, `--json`, a CI annotation) can serialise it by accident.

| Option | Meaning |
|---|---|
| `--reveal` | append a stable fingerprint to each finding line - `sha256:` plus 12 hex characters of the unsalted SHA-256 of the full value. Use it to tell two findings apart or to confirm that a rotated secret really is gone. It is not usable as the credential and does not embed any prefix of it |
| `--reveal-to PATH` | write the raw matched values to a file you name, for local remediation only. The file is created `0600` and **refuses to overwrite** an existing path (exit `2`); each line is `location<TAB>rule<TAB>fingerprint<TAB>value`; a `WARNING` naming the file is printed to stderr; a partial file is deleted on error |
| `--json` | machine-readable report. It carries the same rule-named evidence; the raw value is not an item of any finding, so it is not in the JSON either |
| `--quiet` | only the one-line `PASS`/`FAIL` summary |
| `--allow FILE` | allowlist, one regular expression per line with an optional `# reason` |

Remediation workflow: run with `--reveal` to locate and identify, then
`--reveal-to /a/path/only/you/can/read` to recover the exact strings, rotate the
credential, delete the file, and rewrite history if it was committed. Never pass
`--reveal-to` in CI, never commit the output, and never paste it into a ticket or
a chat - the file is plaintext by construction.

## The rest of the reference

- [CLI reference](cli.md) - every command, grouped by job.
- [CLI: records and knowledge](cli-records.md) - learning, context, criteria and tests.
- [CLI: review and governance](cli-review.md) - review, archive, decisions, disputes, red lines, skills.
- [CLI: feature teams and git workflow](cli-workflow.md) - features, branches, PRs, commits, hooks.
- [CLI: audit and control (this page)](cli-audit.md) - ledger, trace, coordination, loop, model, scripts.
