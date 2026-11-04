# Audit report

- generated: 2026-11-04T22:35:21
- team: Teamwork
- ledger: 114 records, chain verified: True
- checkpoint: record #114 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `669b2df9b577c8dc5c1bf31acb91c86e`
- git: a8cb4aefc968 on main, dirty: False
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
| docs/Team/Architecture.md | 178297 | `8581ac82795ef502…` |
| docs/Team/Decisions.md | 344521 | `87803391c3712dd4…` |
| docs/Team/Plan.md | 90078 | `5a1187b1b0e41537…` |
| docs/Team/Project.md | 54414 | `f4e5b50f440bb34b…` |
