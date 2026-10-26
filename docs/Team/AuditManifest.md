# Audit report

- generated: 2026-10-26T03:10:43
- team: Teamwork
- ledger: 678 records, chain verified: True
- checkpoint: record #678 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `add61ce99d677ef672c142ab46c447b7`
- git: a0d9ce6eb754 on main, dirty: False
- externally verifiable artifacts: 4
- local-only state files: 46

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 86817 | `08a67a3dec2646bb…` |
| docs/Team/Decisions.md | 224415 | `5f42de399f57a329…` |
| docs/Team/Plan.md | 67107 | `0259f404b6cf7e9a…` |
| docs/Team/Project.md | 38502 | `eebca9d9a9cb70a9…` |
