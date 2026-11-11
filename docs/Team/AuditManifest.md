# Audit report

- generated: 2026-11-11T11:30:03
- team: Teamwork
- ledger: 4633 records, chain verified: True
- checkpoint: record #4633 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `1fa0c2c64a7ee39dcebc340e7d5a69be`
- git: 60af2d906ac1 on main, dirty: False
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
| docs/Team/Decisions.md | 383381 | `32bffc0a4dc9ef98…` |
| docs/Team/Plan.md | 98011 | `d06860bc1cb0ff83…` |
| docs/Team/Project.md | 62432 | `6ccd52cea7d5ebf9…` |
