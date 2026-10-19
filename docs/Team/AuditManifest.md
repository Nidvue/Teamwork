# Audit report

- generated: 2026-10-19T20:36:23
- team: Teamwork
- ledger: 621 records, chain verified: True
- head hash: `e0af74bb195270e5c0a4c85269e07e3c`
- git: b372290bc723 on ceo/t-0028-m8-records-hygiene-repair-the-archive-me, dirty: False
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
| docs/Team/Decisions.md | 37453 | `870154ac865912c0…` |
| docs/Team/Plan.md | 6500 | `91178b66af795265…` |
| docs/Team/Project.md | 10766 | `9bc02eff318d0959…` |
