# Audit report

- generated: 2026-11-11T13:45:18
- team: Teamwork
- ledger: 4960 records, chain verified: True
- checkpoint: record #4960 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `2adcf45ff0413506fd73142bd22609cd`
- git: c94a4baa77f6 on main, dirty: False
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
| docs/Team/Architecture.md | 182291 | `0af58b750955fc06…` |
| docs/Team/Decisions.md | 390712 | `2e32fe1ceaf1aea6…` |
| docs/Team/Plan.md | 98011 | `d06860bc1cb0ff83…` |
| docs/Team/Project.md | 62432 | `6ccd52cea7d5ebf9…` |
