# Audit report

- generated: 2026-11-09T20:36:17
- team: Teamwork
- ledger: 3975 records, chain verified: True
- checkpoint: record #3975 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `1fdafc311bd1fbc80adce782262712db`
- git: 76e736d7dee3 on main, dirty: False
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
| docs/Team/Architecture.md | 181477 | `0a5dafb143fa8894…` |
| docs/Team/Decisions.md | 370693 | `a892a7c3bf53caeb…` |
| docs/Team/Plan.md | 98011 | `e11a5e3b4bff4186…` |
| docs/Team/Project.md | 63041 | `2f22fa611cf1c82f…` |
