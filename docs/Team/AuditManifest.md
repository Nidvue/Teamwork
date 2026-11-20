# Audit report

- generated: 2026-11-20T01:46:45
- team: Teamwork
- ledger: 392 records, chain verified: True
- checkpoint: record #392 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `fcea10a506d2a57b49e380a5f2fb361e`
- git: a5c680cbfdf0 on main, dirty: True
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
