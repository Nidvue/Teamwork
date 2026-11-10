# Audit report

- generated: 2026-11-10T00:13:30
- team: Teamwork
- ledger: 4242 records, chain verified: True
- checkpoint: record #4242 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `68c6c75ef125b52bf0b0868efa3cbc34`
- git: df8dae5bad59 on main, dirty: False
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
| docs/Team/Architecture.md | 181574 | `130f62e32145f831…` |
| docs/Team/Decisions.md | 373010 | `82cfc9f1b2db66dd…` |
| docs/Team/Plan.md | 98011 | `e11a5e3b4bff4186…` |
| docs/Team/Project.md | 63188 | `5f6b0f944fa7e7ee…` |
