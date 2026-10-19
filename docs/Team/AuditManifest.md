# Audit report

- generated: 2026-10-19T20:11:37
- team: Teamwork
- ledger: 592 records, chain verified: True
- head hash: `6b1f259914eaa56cf898750f290ac682`
- git: 89b7874eb782 on ceo/t-0027-m7-records-final, dirty: False
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
| docs/Team/Plan.md | 6591 | `8f78306ad14b1d8b…` |
| docs/Team/Project.md | 10766 | `9bc02eff318d0959…` |
