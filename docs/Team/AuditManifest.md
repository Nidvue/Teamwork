# Audit report

- generated: 2026-11-25T11:51:43
- team: Teamwork
- ledger: 976 records, chain verified: True
- checkpoint: record #976 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `766d3e9b4138d82ee3f964ddb7f0d888`
- git: ee058107d5b8 on main, dirty: False
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
| docs/Team/Decisions.md | 484423 | `6f3a2bc6874e974d…` |
| docs/Team/Plan.md | 101984 | `d0a810d1ab23976d…` |
| docs/Team/Project.md | 79801 | `4eacee66b119fc93…` |
