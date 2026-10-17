# Audit report

- generated: 2026-10-17T21:50:35
- team: Teamwork
- ledger: 241 records, chain verified: True
- head hash: `bf7f9462262ca698a543e98bae57b385`
- git: bbb9d299d877 on main, dirty: True
- externally verifiable artifacts: 5
- local-only state files: 58

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 8949 | `038a5a95dc43e874…` |
| docs/Team/Archive.md | 7737 | `e4cff8229e44ea20…` |
| docs/Team/Decisions.md | 14595 | `e407c198281db81c…` |
| docs/Team/Plan.md | 3198 | `c68e0be4589a4b2d…` |
| docs/Team/Project.md | 9559 | `9ef22481a92c9c5f…` |
