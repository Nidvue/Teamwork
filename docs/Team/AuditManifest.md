# Audit report

- generated: 2026-10-19T13:46:11
- team: Teamwork
- ledger: 313 records, chain verified: True
- head hash: `87fddb28ec6e753b59692b246daacad1`
- git: 9fd26c58f874 on ceo/t-0023-bind-the-d-20261019-ceo-3-evidence-to-th, dirty: False
- externally verifiable artifacts: 5
- local-only state files: 22

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 10157 | `30a601b72f8f76e2…` |
| docs/Team/Archive.md | 67543 | `d9d439d5ddad01c7…` |
| docs/Team/Decisions.md | 27141 | `837717daf73e6df2…` |
| docs/Team/Plan.md | 5460 | `a3cb14be9d950ab2…` |
| docs/Team/Project.md | 10766 | `9bc02eff318d0959…` |
