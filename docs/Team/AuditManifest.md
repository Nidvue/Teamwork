# Audit report

- generated: 2026-10-19T00:21:04
- team: Teamwork
- ledger: 94 records, chain verified: True
- head hash: `c706cffd1a0dbd12616c2e3991fe562d`
- git: a531fb8cd70f on ceo/t-0010-export-the-current-audit-manifest-with-a, dirty: False
- externally verifiable artifacts: 5
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
| docs/Team/Architecture.md | 9243 | `01f5bf176144f60c…` |
| docs/Team/Archive.md | 12923 | `a5adb4d785508b9c…` |
| docs/Team/Decisions.md | 18528 | `78b1fdcff2e379bb…` |
| docs/Team/Plan.md | 4100 | `b93c47d166d45ea0…` |
| docs/Team/Project.md | 10766 | `9bc02eff318d0959…` |
