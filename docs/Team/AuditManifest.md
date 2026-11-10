# Audit report

- generated: 2026-10-20T21:30:34
- team: Teamwork
- ledger: 509 records, chain verified: True
- checkpoint: record #509 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `edf19e8d8aaf30a66dca62eb367b955f`
- git: 160c6daf671f on ceo/t-0009-export-the-audit-manifest-for-the-m9-mil, dirty: False
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
| docs/Team/Architecture.md | 31647 | `35d72df8f505b0d1…` |
| docs/Team/Decisions.md | 130096 | `1dd6716794d3e815…` |
| docs/Team/Plan.md | 13417 | `e4253bcecbaa0e16…` |
| docs/Team/Project.md | 26056 | `f328e490fc3c9391…` |
