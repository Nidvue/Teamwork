# Audit report

- generated: 2026-11-16T20:28:08
- team: Teamwork
- ledger: 1928 records, chain verified: True
- checkpoint: record #1928 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `835f4fed611abefae6fab01f06d93a96`
- git: 0cf0c488b01d on main, dirty: True
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
| docs/Team/Decisions.md | 441163 | `b216705b6f12126b…` |
| docs/Team/Plan.md | 101509 | `f808906c4f25fca0…` |
| docs/Team/Project.md | 64083 | `47d2fc66e247dce1…` |
