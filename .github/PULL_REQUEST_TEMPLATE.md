# Pull Request

<!--
Thanks for contributing to Teamwork. Fill every section; delete lines that do
not apply. A PR that cannot be traced to a task, an acceptance criterion and a
test will be sent back.
-->

## Summary

<!-- One paragraph: what changes and why. -->

## Task and acceptance

- Task id: `T-____`
- Addresses: <!-- e.g. AC-4 -->
- Related issue: <!-- #123 or "none" -->

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation only
- [ ] CI / build / release
- [ ] Refactor (no behaviour change)

## What was tested

<!-- Paste the exact command(s) and the observed result. Claims without a
command and a result are treated as unverified. -->

```text
$ <command>
<result>
```

- [ ] `python -m pytest -q` passes locally
- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] Docs build with `mkdocs build --strict` (if docs changed)
- [ ] Privacy scan: `python scripts/privacy_scan.py --tree` exits 0

## Checklist

- [ ] One logical change; no unrelated commits or mixed owners
- [ ] Interfaces in `docs/Team/Architecture.md` unchanged, or the change is
      recorded as a decision in `docs/Team/Decisions.md`
- [ ] No secrets, tokens, personal paths, personal emails or private domains
- [ ] No tests weakened or deleted to make the change pass
- [ ] Evidence (command @ revision -> result) is recorded on the task
- [ ] Runtime stays standard-library only and Python 3.9-3.13 compatible

## Reviewer notes

<!-- Anything the Reviewer must know: risky areas, follow-ups, open questions. -->
