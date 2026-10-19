# Audit report

- generated: 2026-10-19T19:41:32
- team: Teamwork
- ledger: 569 records, chain verified: True
- head hash: `8ae1ab5a1d3b603bf6bc9db31d8a2323`
- git: 84bdfab12ca1 on ceo/t-0027-m7-records-final, dirty: True
- externally verifiable artifacts: 4
- local-only state files: 42

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 10222 | `450c1d546c9e6b21…` |
| docs/Team/Decisions.md | 37214 | `55e7a58e3d004690…` |
| docs/Team/Plan.md | 5495 | `0996f5acdbb3d941…` |
| docs/Team/Project.md | 10766 | `9bc02eff318d0959…` |
