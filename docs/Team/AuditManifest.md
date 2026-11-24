# Audit report

- generated: 2026-11-24T10:42:56
- team: Teamwork
- ledger: 410 records, chain verified: True
- checkpoint: record #410 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `f890f1a886d502cc3139791b404d4693`
- git: 744836cb2559 on main, dirty: False
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
| docs/Team/Architecture.md | 212392 | `0a5b757dfca5a884…` |
| docs/Team/Decisions.md | 475816 | `9d16d991c1c4aa1c…` |
| docs/Team/Plan.md | 101665 | `452c4e541e134486…` |
| docs/Team/Project.md | 70812 | `deda5955d8fa6995…` |
