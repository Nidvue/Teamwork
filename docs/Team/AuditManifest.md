# Audit report

- generated: 2026-11-16T19:42:39
- team: Teamwork
- ledger: 1875 records, chain verified: True
- checkpoint: record #1875 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `51d2ed111bd5800bca21b1101097c6c5`
- git: 7bb7ba6daa27 on main, dirty: True
- externally verifiable artifacts: 4
- local-only state files: 46

## Verification (external, no trust required)

```sh
teamwork.py ledger verify    # recompute sha256 chain over Ledger.jsonl
sha256sum -c <(jq -r '.artifacts[] | "\(.sha256)  \(.path)"' docs/Team/AuditManifest.json)
teamwork.py trace <T-id>     # follow any claim end to end
```

## Artifacts

| path | bytes | sha256 |
|---|---|---|
| docs/Team/Architecture.md | 191302 | `1fc3ade79e3059b6…` |
| docs/Team/Decisions.md | 439674 | `b1c15142f23c7350…` |
| docs/Team/Plan.md | 101509 | `f808906c4f25fca0…` |
| docs/Team/Project.md | 64083 | `47d2fc66e247dce1…` |
