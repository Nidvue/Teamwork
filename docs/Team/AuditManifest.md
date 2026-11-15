# Audit report

- generated: 2026-11-15T01:46:26
- team: Teamwork
- ledger: 304 records, chain verified: True
- checkpoint: record #304 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `2d19911b118f47dfaddd50390010a397`
- git: 86b48469c75c on ceo/t-0034-close-out-records-export-the-audit-manif, dirty: False
- externally verifiable artifacts: 4
- local-only state files: 30

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 181406 | `8c29d7d1be17e6d1…` |
| docs/Team/Decisions.md | 366313 | `6b854711536b25d1…` |
| docs/Team/Plan.md | 95292 | `f2b41f46c8923d09…` |
| docs/Team/Project.md | 60271 | `e467b8c2052deb4b…` |
