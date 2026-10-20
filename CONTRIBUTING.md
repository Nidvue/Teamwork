# Contributing to Teamwork

Owner: Technical Writer.

Related: [Architecture](docs/Team/Architecture.md) · [CI pipeline](docs/guide/ci.md) · [Security policy](SECURITY.md) · [Code of conduct](CODE_OF_CONDUCT.md)

Thanks for helping. Nidvue Teamwork is a standard-library-only Python package that also
ships as a Pi skill. Two rules matter more than any other: **every claim carries
evidence**, and **no secrets or personal data ever enter the repository**.

## Development setup

```console
$ git clone https://github.com/Nidvue/Teamwork.git
$ cd Teamwork
$ python -m venv .venv
$ . .venv/bin/activate            # Windows: .venv\Scripts\activate
$ python -m pip install -e ".[dev]"
$ python -m pip install -r docs/requirements.txt
```

Requirements: Python 3.9 or newer. The runtime has no third-party dependencies.

## Make targets

| Target | Command | Purpose |
|---|---|---|
| `make lint` | `ruff check .` + `ruff format --check .` | Style, imports and formatting. |
| `make typecheck` | `mypy src/teamwork` | Type report. |
| `make test` | `pytest -q` | Unit, integration and acceptance tests. |
| `make build` | `python -m build` | Build sdist and wheel. |
| `make verify` | `python scripts/verify_release.py` | Install and smoke-test the wheel. |
| `make privacy` | `python scripts/privacy_scan.py --tree --history` | Privacy gate. |
| `make docs` | `python -m mkdocs build --strict` | Docs site. |
| `make links` | `python scripts/teamwork.py links` | Link health. |
| `make identity` | `python scripts/teamwork.py identity --audit` | Team commit identity. |
| `make ci` | all of the above | Full local pipeline. |

The full pipeline is documented in [docs/guide/ci.md](docs/guide/ci.md).

## Pull request process

1. **Branch.** Never commit on `main`. Create a branch named after the work.
2. **Commit** with the repository's fixed message shape:

   ```text
   <type>(<area>): <summary>

   Task: <id>
   Role: <role>
   Producers: <agents>
   Goal: <what was asked>
   Deliverable: <what you produced>
   Why: <why this change>
   Status: <actual state>
   Result: <command @rev -> observed result>
   ```

   Commit as a role mailbox, for example
   `git -c user.name=Developer -c user.email=developer@agents.nidvue.com commit`.
3. **Self-check.** Re-read your diff and run a real command, then record the
   result.
4. **Open a pull request** describing the artifact, the evidence and the
   revision.
5. **Independent review.** A different maintainer reviews and merges; you never
   merge your own change. The preferred path is a local merge as the reviewing
   role, then a push. **Squash merging is disabled on the remote**: a forge squash
   stamps the *signed-in account's* mailbox on the resulting commit, and the
   privacy gate scans history - it fails on the personal address, and because that
   gate is also an acceptance proof, the traceability guard fails with it. That
   cost two rewrites of `main` (see the 2026-10-20 entries in
   [Decisions](docs/Team/Decisions.md)).

   **Rebase merging is the one forge action that is safe**, and it is the only one
   enabled: it replays the commits unchanged, so the author stays the role that did
   the work, and it rewrites only the committer to the host's `noreply@github.com`
   account. The identity audit accepts that stamp for a role-authored commit
   (`_RE_FORGE_COMMITTER_EMAIL`) and the privacy gate already treats it as a
   service address; a committer that is *not* the host's is still a defect.

   If a rewrite is forced on you anyway, amend the tip to a role mailbox, verify
   its tree is byte-identical to the commit it replaces, push it with
   `--force-with-lease`, and restore the branch protection you relaxed to do it.

## Evidence rule

Every claim about code, tests or CI cites the command, the revision and the
observed result:

```text
pytest -q @abc1234 -> 64 passed
mkdocs build --strict @abc1234 -> 0 warnings
```

A claim without evidence is `UNVERIFIED`. Do not invent test results, CI status
or benchmarks. Re-run after the tree changes; evidence goes stale with the
revision.

## No-secrets rule

- Never commit credentials, tokens, keys or `.env` contents.
- Never print or log secrets, and never read them to debug.
- Do not publish a personal email address or a personal filesystem path.
- Run `python scripts/privacy_scan.py --tree --history` before opening a PR. Git history
  is scanned too; a secret that was committed once is still exposed.

If you find a secret in the tree or history, stop and report it privately — see
[SECURITY.md](SECURITY.md).

## Developer Certificate of Origin (DCO)

Every commit must be signed off under the
[Developer Certificate of Origin 1.1](https://developercertificate.org/): add a
`Signed-off-by` line with `git commit -s`.

```text
Signed-off-by: Your Name <you@example.com>
```

Signing off certifies that you wrote the contribution, or have the right to
submit it under the project license (AGPL-3.0). By contributing you agree to
release your work under that license.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
