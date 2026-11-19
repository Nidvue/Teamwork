# Audit report

- generated: 2026-11-19T19:32:10
- team: Teamwork
- ledger: 308 records, chain verified: True
- checkpoint: record #308 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `ebbeb16adbd7b94a89d778198d078ae1`
- git: 66d49d9a13f1 on main, dirty: False
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
| docs/Team/Architecture.md | 208381 | `1d06f8146987564c…` |
| docs/Team/Decisions.md | 447275 | `64cd8519c858c51e…` |
| docs/Team/Plan.md | 101665 | `452c4e541e134486…` |
| docs/Team/Project.md | 66079 | `842d24445c6fce5c…` |
