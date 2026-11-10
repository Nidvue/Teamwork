# Audit report

- generated: 2026-11-10T11:09:11
- team: Teamwork
- ledger: 4403 records, chain verified: True
- checkpoint: record #4403 (the ledger.export event behind this manifest; later records are work that happened after it)
- head hash: `c24a6de44852c8fdeb16fa2b17f7ea72`
- git: b63e05a71cd1 on main, dirty: True
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
| docs/Team/Decisions.md | 375924 | `5bc66707205e0943…` |
| docs/Team/Plan.md | 98011 | `e11a5e3b4bff4186…` |
| docs/Team/Project.md | 62432 | `b7c10fda3b79c301…` |
