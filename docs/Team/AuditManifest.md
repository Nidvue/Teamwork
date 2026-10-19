# Audit report

- generated: 2026-10-19T20:02:53
- team: Teamwork
- ledger: 584 records, chain verified: True
- head hash: `ccd1b24f1d60024bcca0655a46924778`
- git: 74f8965db599 on ceo/t-0027-m7-records-final, dirty: False
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
| docs/Team/Decisions.md | 37521 | `2f6089e832a107a5…` |
| docs/Team/Plan.md | 6591 | `8f78306ad14b1d8b…` |
| docs/Team/Project.md | 10766 | `9bc02eff318d0959…` |
