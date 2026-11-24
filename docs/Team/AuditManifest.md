# Audit report

- generated: 2026-11-24T14:02:20
- team: Teamwork
- ledger: 528 records, chain verified: True
- checkpoint: record #528 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `b4f521234244e40f43a20d570435b2e0`
- git: 8e5d36df52b7 on main, dirty: False
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
| docs/Team/Architecture.md | 212001 | `44c0a0c7b9e2fc3b…` |
| docs/Team/Decisions.md | 477125 | `e930bfceade99949…` |
| docs/Team/Plan.md | 101984 | `d0a810d1ab23976d…` |
| docs/Team/Project.md | 73279 | `81fc19ff1d4a8a69…` |
