# Archive merge revisions - the eight rows recorded after the reconciliation

Owner: CEO.

Related: [Archive](../Archive.md) · [T-0084 archive remap](T-0084-archive-remap.md)

## 1. Why this exists

[T-0084](T-0084-archive-remap.md) re-pointed 586 rows of `docs/Team/Archive.md` onto
`main`'s line after the 2026-11-18 reconciliation of the published line. Eight rows
were written *after* that repair - `P-0242` to `P-0249`, the widget layers, the remap
itself and the five identity tasks - and each recorded a merge revision that no longer
exists in the repository: `git cat-file -t` answers `fatal: Not a valid object name`
for all eight. The work is in the tree (the boundary constant, `outside_project_domain`,
the widget layers, this report's sibling are all present), so the records were naming a
revision of a line that is gone, not work that never landed.

`tests/unit/test_archive_merge_revisions.py` was red on `main` and on `origin/main` for
those eight rows and for nothing else. The guard was not touched: a record is repaired,
never a gate.

## 2. The rule, and why it is evidence rather than a guess

Each `chore(records): record the merge revision of P-024x` commit sits exactly two
commits above the revision that landed the branch:

```text
<landing commit>          the change-set on main
chore(records): re-render docs/Team/Board.md at the merge
chore(records): record the merge revision of P-024x in Archive.md
```

So the landing revision is the parent of the board-render commit, which is a fact read
from the graph, not an inference from a date or an order. Every one of the eight is
independently confirmed as the single commit on `main` that introduced that deliverable,
by `git log -S <token>` or `git log --diff-filter=A -- <path>` - one hit each, no
ambiguity to resolve.

## 3. The eight rows

| Row | Recorded (gone) | Landing on `main` | Independent confirmation |
|---|---|---|---|
| T-0018 `tester/t-0018-widget-crash-record-the-integration-laye` | `764e20a1` | `2e68df38` | `--diff-filter=A -- tests/integration/test_widget_survives.py` -> one hit |
| T-0008 `reviewer-3/t-0008-widget-crash-record-the-acceptance-layer` | `e6c09c25` | `e60e0e40` | `--diff-filter=A -- tests/acceptance/test_widget_survives_session_replacement.py` -> one hit |
| T-0084 `ceo/t-0084-repair-every-archive-merge-revision-so-i` | `3bd000e8` | `226b2e3b` | `--diff-filter=A -- docs/Team/reports/T-0084-archive-remap.md` -> one hit |
| T-0145 `dev-1/t-0145-the-identity-boundary-cannot-cover-a-two` | `2cb1ed12` | `51624168` | `-S 34384c63c1d817719aa3b15a62b6a0c269c71bb2 -- src/teamwork/engine.py` -> one hit |
| T-0146 `dev-1/t-0146-commit-identity-must-never-author-as-the` | `d0090de4` | `54fc2a04` | `-S outside_project_domain -- src/teamwork` -> one hit |
| T-0147 `dev-1/t-0147-the-merge-s-rebase-leaves-the-operator-a` | `ffa7ff92` | `5d98dedc` | the parent of its board-render commit; `git log --grep 'run_git takes an env'` -> one hit |
| T-0148 `dev-1/t-0148-align-the-identity-policy-s-other-pins-t` | `43bdf955` | `c380c5fa` | the parent of its board-render commit; the `test_names.py` pin, one hit |
| T-0149 `dev-1/t-0149-the-last-pin-of-the-superseded-identity` | `d6276c7c` | `d8f72ec3` | the parent of its board-render commit; the `test_integrity_fixes.py` pin, one hit |

Only the revision token on each `- branch / merge:` line changed. The branch, every
other field and the entry order are byte-identical.

## 4. Measured

- `pytest -q tests/unit/test_archive_merge_revisions.py` -> 6 passed (2 failed before).
- `git merge-base --is-ancestor <landing> main` for all eight -> exit 0.
- `teamwork.py links` -> `# issues: 0`.
- The guard file is unmodified: `git diff --stat -- tests/` is empty for this change.

## 5. What this does not fix

The eight rows now name a revision a reader can check out, which is what the field is
for. They still cannot name the branch's own commits (`09008e62`, `6f0e4f4a`, ...):
those objects are gone, and the entry's `author evidence` line still quotes them as the
author's measurement, which is honest - the measurement happened there - while the
`branch / merge` field now points at what landed. A future rewrite of the published line
must repeat this repair, which is why the guard measures reachability against the default
branch rather than trusting the record.
