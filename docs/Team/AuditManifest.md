# Audit report

- generated: 2026-10-21T06:42:22
- team: Teamwork
- ledger: 666 records, chain verified: True
- checkpoint: record #666 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `2870ee98a255f156a006c4058da96db6`
- git: 7f6071484b9d on ceo/t-0012-re-export-the-audit-manifest-at-the-fina, dirty: False
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
| docs/Team/Decisions.md | 145134 | `dd3e9bfbe337c30d…` |
| docs/Team/Plan.md | 17872 | `1d9ac8251b288968…` |
| docs/Team/Project.md | 26056 | `f328e490fc3c9391…` |
