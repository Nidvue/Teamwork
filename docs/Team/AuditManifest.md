# Audit report

- generated: 2026-11-18T15:44:41
- team: Teamwork
- ledger: 9107 records, chain verified: True
- checkpoint: record #9107 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `4d6bb8ade8db3bd4e51ec2d728c57b9a`
- git: c66573271de7 on main, dirty: True
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
| docs/Team/Architecture.md | 208381 | `1d06f8146987564c…` |
| docs/Team/Decisions.md | 445697 | `590d5e1c3056ffc5…` |
| docs/Team/Plan.md | 101665 | `452c4e541e134486…` |
| docs/Team/Project.md | 66079 | `842d24445c6fce5c…` |
