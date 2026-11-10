# Audit report

- generated: 2026-11-10T08:41:18
- team: Teamwork
- ledger: 4375 records, chain verified: True
- checkpoint: record #4375 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `c7c196f3afdbf01d3d7741e711bba9da`
- git: 3abc40251ec8 on main, dirty: False
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
| docs/Team/Architecture.md | 181574 | `130f62e32145f831…` |
| docs/Team/Decisions.md | 374929 | `6443c20940a2a4a0…` |
| docs/Team/Plan.md | 98011 | `e11a5e3b4bff4186…` |
| docs/Team/Project.md | 62621 | `d0ec58f319822844…` |
