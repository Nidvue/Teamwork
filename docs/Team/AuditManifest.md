# Audit report

- generated: 2026-11-10T21:49:11
- team: Teamwork
- ledger: 4456 records, chain verified: True
- checkpoint: record #4456 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `17122ce04b63193316ef1ee94442fdbf`
- git: c55404459bd2 on main, dirty: False
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
| docs/Team/Architecture.md | 181574 | `a1ca750a66f168ce…` |
| docs/Team/Decisions.md | 380172 | `af5e59c60cde6124…` |
| docs/Team/Plan.md | 98011 | `d06860bc1cb0ff83…` |
| docs/Team/Project.md | 62432 | `6ccd52cea7d5ebf9…` |
