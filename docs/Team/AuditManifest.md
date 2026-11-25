# Audit report

- generated: 2026-11-25T14:37:50
- team: Teamwork
- ledger: 1077 records, chain verified: True
- checkpoint: record #1077 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `8c86dd02aaf0ecbb5f35d19faf377015`
- git: a4e89b06d24f on main, dirty: False
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
| docs/Team/Architecture.md | 212788 | `09551ce668d48419…` |
| docs/Team/Decisions.md | 485922 | `ed3093f663b2e96a…` |
| docs/Team/Plan.md | 101984 | `d0a810d1ab23976d…` |
| docs/Team/Project.md | 79801 | `4eacee66b119fc93…` |
