# Audit report

- generated: 2026-11-11T09:32:06
- team: Teamwork
- ledger: 4551 records, chain verified: True
- checkpoint: record #4551 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `b5ac18faed148b4d358449f3bc1aa28c`
- git: e30b956e29ed on main, dirty: True
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
| docs/Team/Architecture.md | 181574 | `a1ca750a66f168ce…` |
| docs/Team/Decisions.md | 383381 | `32bffc0a4dc9ef98…` |
| docs/Team/Plan.md | 98011 | `d06860bc1cb0ff83…` |
| docs/Team/Project.md | 62432 | `6ccd52cea7d5ebf9…` |
