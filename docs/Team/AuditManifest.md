# Audit report

- generated: 2026-11-10T21:55:09
- team: Teamwork
- ledger: 4458 records, chain verified: True
- checkpoint: record #4458 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `c9fabaf1ba57387f226a5241d08e54e0`
- git: 5b2ea4c1947f on main, dirty: True
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
| docs/Team/Architecture.md | 181574 | `a1ca750a66f168ce…` |
| docs/Team/Decisions.md | 382208 | `2d5af480ce95f614…` |
| docs/Team/Plan.md | 98011 | `d06860bc1cb0ff83…` |
| docs/Team/Project.md | 62432 | `6ccd52cea7d5ebf9…` |
