# Audit report

- generated: 2026-10-22T01:35:59
- team: Teamwork
- ledger: 2490 records, chain verified: True
- checkpoint: record #2490 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `e73352c781e676938fbf58a8f954c79a`
- git: fcadbb09d0a6 on main, dirty: False
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
| docs/Team/Architecture.md | 84747 | `dc16bfb955bc1c96…` |
| docs/Team/Decisions.md | 211638 | `9014a1fa8f0cc463…` |
| docs/Team/Plan.md | 28017 | `8b486f12fe4e36c8…` |
| docs/Team/Project.md | 26182 | `3162142de84f2b3a…` |
