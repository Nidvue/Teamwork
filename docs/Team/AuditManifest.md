# Audit report

- generated: 2026-10-25T19:24:01
- team: Teamwork
- ledger: 531 records, chain verified: True
- checkpoint: record #531 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `a37724864840054ca23cb9406374c3ba`
- git: 17a67bd9bdd4 on main, dirty: False
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
| docs/Team/Architecture.md | 85754 | `f454bc68c68c6bee…` |
| docs/Team/Decisions.md | 223916 | `bedee7da43ad6548…` |
| docs/Team/Plan.md | 67107 | `0259f404b6cf7e9a…` |
| docs/Team/Project.md | 38502 | `eebca9d9a9cb70a9…` |
