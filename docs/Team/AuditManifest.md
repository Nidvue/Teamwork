# Audit report

- generated: 2026-11-07T20:27:57
- team: Teamwork
- ledger: 478 records, chain verified: False
- checkpoint: record #478 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `5e3fde578bd97e55544284095d6acbfa`
- git: 7ee1691ace71 on main, dirty: True
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
| docs/Team/Architecture.md | 180162 | `a9576147d4876772…` |
| docs/Team/Decisions.md | 349069 | `01490d7fac678ece…` |
| docs/Team/Plan.md | 91248 | `aab6f909b0b5f4a9…` |
| docs/Team/Project.md | 56228 | `008c406824295f32…` |

## PROBLEMS

- record 106 (task.add): digest mismatch (record altered)
