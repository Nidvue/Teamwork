# Audit report

- generated: 2026-11-08T21:53:10
- team: Teamwork
- ledger: 1230 records, chain verified: False
- checkpoint: record #1230 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `12c4cc7fa0e78153e80c3d2234621213`
- git: 5913171a44bb on main, dirty: False
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
| docs/Team/Architecture.md | 180681 | `9c747f1734833871…` |
| docs/Team/Decisions.md | 362724 | `278d1b9b94b494aa…` |
| docs/Team/Plan.md | 94557 | `d62a40b698f19f30…` |
| docs/Team/Project.md | 58516 | `59e078842ed8f127…` |

## PROBLEMS

- record 106 (task.add): digest mismatch (record altered)
