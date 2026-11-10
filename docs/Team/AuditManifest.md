# Audit report

- generated: 2026-10-20T08:34:27
- team: Teamwork
- ledger: 1587 records, chain verified: True
- checkpoint: record #1587 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `af80a524e943b500ad3e1cf523eb8949`
- git: 23ad80a68d88 on main, dirty: False
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
| docs/Team/Architecture.md | 13059 | `6faa17a14a59b9d5…` |
| docs/Team/Decisions.md | 76178 | `d924ceb202f4d289…` |
| docs/Team/Plan.md | 8461 | `ee75a63948ecc2a7…` |
| docs/Team/Project.md | 24045 | `54201cb1d3f8de57…` |
