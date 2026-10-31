# Audit report

- generated: 2026-10-31T12:12:55
- team: Teamwork
- ledger: 402 records, chain verified: True
- checkpoint: record #402 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `ba7bce8b126438e919b86f5e9c94dfc5`
- git: 966d0c9ecea2 on main, dirty: False
- externally verifiable artifacts: 4
- local-only state files: 34

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 102748 | `91129fc78fa67bea…` |
| docs/Team/Decisions.md | 277094 | `1b89b7c3608b8be4…` |
| docs/Team/Plan.md | 80579 | `1f4052c2639e7af7…` |
| docs/Team/Project.md | 45378 | `747db04077a8a0fd…` |
