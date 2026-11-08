# Audit report

- generated: 2026-11-08T17:21:11
- team: Teamwork
- ledger: 969 records, chain verified: False
- checkpoint: record #969 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `55fb5aad355d986e6c3de4fb7dbb3135`
- git: aa80a59ad4af on main, dirty: True
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
| docs/Team/Architecture.md | 180454 | `7921dfeaeefac1c1…` |
| docs/Team/Decisions.md | 352127 | `128322eaac180af8…` |
| docs/Team/Plan.md | 94053 | `f78dddce9ff14834…` |
| docs/Team/Project.md | 58516 | `59e078842ed8f127…` |

## PROBLEMS

- record 106 (task.add): digest mismatch (record altered)
