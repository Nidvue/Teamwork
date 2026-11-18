# Audit report

- generated: 2026-11-18T14:50:31
- team: Teamwork
- ledger: 9075 records, chain verified: True
- checkpoint: record #9075 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `f946c6abbb880b30a57006b364b6ac4a`
- git: 6feae5447d5e on main, dirty: False
- externally verifiable artifacts: 4
- local-only state files: 38

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
| docs/Team/Decisions.md | 441163 | `b216705b6f12126b…` |
| docs/Team/Plan.md | 101665 | `452c4e541e134486…` |
| docs/Team/Project.md | 66079 | `842d24445c6fce5c…` |
