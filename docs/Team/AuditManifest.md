# Audit report

- generated: 2026-10-19T13:54:02
- team: Teamwork
- ledger: 336 records, chain verified: True
- head hash: `f21a6c664fa417e7b86be5a31cf729b3`
- git: 1609fe4545d9 on ceo/t-0026-close-the-m6-records-mark-t-0023-done-an, dirty: False
- externally verifiable artifacts: 4
- local-only state files: 22

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 10157 | `30a601b72f8f76e2…` |
| docs/Team/Decisions.md | 27266 | `09635cc8d1578a35…` |
| docs/Team/Plan.md | 5495 | `e8e5b651357b6722…` |
| docs/Team/Project.md | 10766 | `9bc02eff318d0959…` |
