# Audit report

- generated: 2026-11-12T15:09:21
- team: Teamwork
- ledger: 6791 records, chain verified: True
- checkpoint: record #6791 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `12be1591243c3d400feb8ff6b19b18fb`
- git: bfed0a38491e705610877662d98b8156995a698e on main, dirty: False
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
| docs/Team/Architecture.md | 188305 | `6959ce458e27bfa0…` |
| docs/Team/Decisions.md | 409819 | `56ee9a8389ef24f5…` |
| docs/Team/Plan.md | 101872 | `f177d756731ecba2…` |
| docs/Team/Project.md | 62531 | `6364baa525482e4f…` |
