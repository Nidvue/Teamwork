# Audit report

- generated: 2026-11-24T02:50:33
- team: Teamwork
- ledger: 868 records, chain verified: True
- checkpoint: record #868 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `2d4ddd048195d928e4a1c8c187153a26`
- git: e7903ead88ff on main, dirty: True
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
| docs/Team/Architecture.md | 211917 | `2a6c8beafff39f46…` |
| docs/Team/Decisions.md | 472008 | `c9c431933020a87e…` |
| docs/Team/Plan.md | 101665 | `452c4e541e134486…` |
| docs/Team/Project.md | 68746 | `d5ad1a83b9dc1372…` |
