# Audit report

- generated: 2026-11-20T17:25:47
- team: Teamwork
- ledger: 49 records, chain verified: True
- checkpoint: record #49 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `b8b5cfff480102eec6dc613f4cce0dbe`
- git: 1bc0db626969 on main, dirty: True
- externally verifiable artifacts: 4
- local-only state files: 26

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
| docs/Team/Decisions.md | 454810 | `22afacba02c2a199…` |
| docs/Team/Plan.md | 101665 | `452c4e541e134486…` |
| docs/Team/Project.md | 66079 | `842d24445c6fce5c…` |
