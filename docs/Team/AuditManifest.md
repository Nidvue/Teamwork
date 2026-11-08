# Audit report

- generated: 2026-11-08T16:14:55
- team: Teamwork
- ledger: 739 records, chain verified: False
- checkpoint: record #739 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `c7e78eb95cfc48c4b6f7efeb63304f52`
- git: 60ae154356d8 on ceo/t-0017-m21-records-parallel-asynchronous-lanes, dirty: True
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
| docs/Team/Plan.md | 93157 | `2006e672a5b3cf9d…` |
| docs/Team/Project.md | 58262 | `ff8e1e0c1994a058…` |

## PROBLEMS

- record 106 (task.add): digest mismatch (record altered)
