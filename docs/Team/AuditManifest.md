# Audit report

- generated: 2026-11-09T20:05:10
- team: Teamwork
- ledger: 3947 records, chain verified: True
- checkpoint: record #3947 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `37cb2b3b9ea4447855092ee2b01dfb85`
- git: b1e547fd1e95 on main, dirty: False
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
| docs/Team/Architecture.md | 181387 | `05da19a9a8b53f51…` |
| docs/Team/Decisions.md | 370693 | `a892a7c3bf53caeb…` |
| docs/Team/Plan.md | 98011 | `e11a5e3b4bff4186…` |
| docs/Team/Project.md | 63041 | `2f22fa611cf1c82f…` |
