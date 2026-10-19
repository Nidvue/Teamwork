# Audit report

- generated: 2026-10-19T13:50:28
- team: Teamwork
- ledger: 324 records, chain verified: True
- head hash: `00f8834f4654df2c9149299abc7aaf03`
- git: ab26dc24b88e on ceo/t-0023-bind-the-d-20261019-ceo-3-evidence-to-th, dirty: False
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
| docs/Team/Plan.md | 5459 | `aaf46096b13182b1…` |
| docs/Team/Project.md | 10766 | `9bc02eff318d0959…` |
