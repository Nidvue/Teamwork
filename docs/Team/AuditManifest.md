# Audit report

- generated: 2026-11-20T01:47:31
- team: Teamwork
- ledger: 396 records, chain verified: True
- checkpoint: record #396 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `563becbccdffe4506d5e2e4469aeec05`
- git: d9fc02d87f75 on main, dirty: False
- externally verifiable artifacts: 4
- local-only state files: 30

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 208703 | `a6f2844314e51a8e…` |
| docs/Team/Decisions.md | 452089 | `3ee84ac5dc502b25…` |
| docs/Team/Plan.md | 101665 | `452c4e541e134486…` |
| docs/Team/Project.md | 66079 | `842d24445c6fce5c…` |
