# Audit report

- generated: 2026-11-24T15:33:08
- team: Teamwork
- ledger: 691 records, chain verified: True
- checkpoint: record #691 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `394742db7da5f6abe90bb8d25fc5d925`
- git: cc593024a40f on main, dirty: False
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
| docs/Team/Architecture.md | 211988 | `944a5e982cbda045…` |
| docs/Team/Decisions.md | 478370 | `9f8c7b7a78d02cca…` |
| docs/Team/Plan.md | 101984 | `d0a810d1ab23976d…` |
| docs/Team/Project.md | 75510 | `f850be3ab29ab5bf…` |
